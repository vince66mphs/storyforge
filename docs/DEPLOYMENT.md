# StoryForge 2.0 Deployment Guide

This guide covers setting up and running StoryForge on a fresh server or recovering the existing installation.

---

## System Requirements

- **OS:** Debian 12+ (tested on Debian 12 in LXC)
- **Python:** 3.13+
- **PostgreSQL:** 15+ with pgvector extension
- **Ollama:** Running on port 11434
- **ComfyUI:** Running on port 8188 (optional — story writing works without it)
- **GPU:** NVIDIA GPU with CUDA for image generation (ComfyUI)

---

## Directory Layout

```
/home/vince/storyforge/
  backend/
    app/
      api/           # FastAPI routers and schemas
      core/          # Config, database, exceptions
      models/        # SQLAlchemy ORM models
      services/      # Business logic (Ollama, ComfyUI, story, assets)
    alembic/         # Database migration scripts
    cli.py           # Interactive CLI
    requirements.txt
    .env             # Environment configuration
    .venv/           # Python virtual environment
  frontend/
    index.html       # SPA entry point
    css/style.css
    js/              # ES modules (app, api, ws, story-writer, etc.)
  static/images/     # Generated images (served at /static/images/)
  exports/           # Markdown exports
  docs/              # This guide, user guide
```

---

## Installation

### 1. Prerequisites

```bash
# PostgreSQL with pgvector
sudo apt install postgresql postgresql-contrib
sudo apt install postgresql-15-pgvector  # or matching version

# Python 3.13
# If not available via apt, use pyenv or deadsnakes PPA

# Ollama
curl -fsSL https://ollama.com/install.sh | sh
```

### 2. Database Setup

```bash
sudo -u postgres psql <<SQL
CREATE DATABASE storyforge OWNER vince;
\c storyforge
CREATE EXTENSION IF NOT EXISTS vector;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
SQL
```

### 3. Pull Ollama Models

```bash
ollama pull dolphin-mistral:7b
ollama pull phi4:latest
ollama pull nomic-embed-text:latest
```

### 4. Python Environment

```bash
cd /home/vince/storyforge/backend
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt
```

### 5. Configuration

Edit `backend/.env`:

```env
# Database
DATABASE_URL=postgresql+asyncpg://vince:password@localhost:5432/storyforge

# Ollama
OLLAMA_HOST=http://localhost:11434
OLLAMA_MODEL=dolphin-mistral:7b

# ComfyUI
COMFYUI_HOST=http://localhost:8188

# Application
APP_HOST=0.0.0.0
APP_PORT=8000
LOG_LEVEL=INFO

# Paths (adjust to your installation)
STATIC_DIR=/home/vince/storyforge/static
EXPORT_DIR=/home/vince/storyforge/exports
WORKFLOW_DIR=/home/vince/storyforge/workflows
```

All settings can be overridden via environment variables (uppercase, matching the field names).

### 6. Run Migrations

```bash
cd /home/vince/storyforge/backend
.venv/bin/alembic upgrade head
```

This creates the `stories`, `nodes`, and `world_bible_entities` tables with pgvector indexes.

---

## Running

### Development

```bash
cd /home/vince/storyforge/backend
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

`--reload` watches for file changes and restarts automatically.

### Production

```bash
cd /home/vince/storyforge/backend
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1
```

Note: Use `--workers 1` because the app holds in-memory state (service instances) and Ollama/ComfyUI are single-GPU resources. Multiple workers would compete for VRAM.

### systemd Service (optional)

Create `/etc/systemd/system/storyforge.service`:

```ini
[Unit]
Description=StoryForge 2.0
After=network.target postgresql.service ollama.service

[Service]
Type=simple
User=vince
WorkingDirectory=/home/vince/storyforge/backend
ExecStart=/home/vince/storyforge/backend/.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
Restart=on-failure
RestartSec=5

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable --now storyforge
```

### CLI Only (no web server needed)

```bash
cd /home/vince/storyforge/backend
.venv/bin/python cli.py
```

The CLI connects directly to the database and Ollama/ComfyUI — it doesn't use the FastAPI server.

---

## Service Dependencies

| Service | Port | Required For | Fallback |
|---------|------|-------------|----------|
| PostgreSQL | 5432 | All operations | None (required) |
| Ollama | 11434 | Scene generation, entity detection, embeddings | 503 error with helpful message |
| ComfyUI | 8188 | Image generation only | Story writing works without it |

### Health Check

```bash
curl http://localhost:8000/health
```

Returns:
```json
{
  "status": "ok",        // or "degraded" if a service is down
  "version": "0.1.0",
  "services": {
    "ollama": "ok",       // or "unavailable"
    "comfyui": "ok"       // or "unavailable"
  }
}
```

### Checking Individual Services

```bash
# PostgreSQL
sudo systemctl status postgresql

# Ollama
curl http://localhost:11434/api/tags

# ComfyUI
curl http://localhost:8188/system_stats
```

---

## Database

### Connection

Default: `postgresql+asyncpg://vince:password@localhost:5432/storyforge`

### Schema

Three main tables (managed by Alembic migrations):

- **stories** — `id` (UUID), `title`, `genre`, `current_leaf_id`, timestamps, JSONB metadata
- **nodes** — `id` (UUID), `story_id` FK, `parent_id` self-referential FK, `content`, `embedding` (vector(768)), `node_type`
- **world_bible_entities** — `id` (UUID), `story_id` FK, `entity_type`, `name`, `description`, `base_prompt`, `reference_image_path`, `embedding` (vector(768)), `version`

### Indexes

- HNSW indexes on embedding columns (vector_cosine_ops, m=16, ef_construction=64)
- B-tree indexes on `parent_id`, `story_id`

### Migrations

```bash
# Apply all pending migrations
cd /home/vince/storyforge/backend
.venv/bin/alembic upgrade head

# Check current revision
.venv/bin/alembic current

# Generate a new migration after model changes
.venv/bin/alembic revision --autogenerate -m "description"
```

### Backup

```bash
pg_dump storyforge > storyforge_backup.sql
```

### Restore

```bash
psql storyforge < storyforge_backup.sql
```

---

## ComfyUI Setup

ComfyUI is optional — StoryForge works for story writing without it. Image generation features return clear error messages when ComfyUI is unavailable.

### Required Checkpoint

The default workflow uses `realvisxlV40_v40LightningBakedvae.safetensors` (SDXL Lightning). Place it in ComfyUI's `models/checkpoints/` directory.

### Default Pipeline

- Sampler: euler / sgm_uniform
- Steps: 6
- CFG: 1.8
- Resolution: 1024x1024

This is optimized for speed (~2-4 seconds per image on RTX 3090).

---

## Troubleshooting

### "Ollama is unavailable"

```bash
# Check if Ollama is running
curl http://localhost:11434/api/tags

# Start it
sudo systemctl start ollama
# or
ollama serve
```

### "ComfyUI is unavailable"

```bash
# Check if ComfyUI is running
curl http://localhost:8188/system_stats

# Check GPU access
nvidia-smi
```

In LXC containers, GPU passthrough must be configured on the Proxmox host.

### Database connection refused

```bash
sudo systemctl status postgresql
sudo systemctl start postgresql

# Verify database exists
sudo -u postgres psql -l | grep storyforge
```

### "No module named 'app'"

Make sure you're running from the `backend/` directory:
```bash
cd /home/vince/storyforge/backend
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

### Migration errors

```bash
# Check current state
cd /home/vince/storyforge/backend
.venv/bin/alembic current

# If the database is out of sync, stamp it
.venv/bin/alembic stamp head

# Then re-run
.venv/bin/alembic upgrade head
```

### Port already in use

```bash
# Find what's using port 8000
ss -tlnp | grep 8000

# Kill the process
kill <pid>
```
