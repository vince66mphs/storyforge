# Tech Stack - Locked Decisions

## Overview
This document defines the technology choices for StoryForge 2.0. These decisions are locked for Phase 1 to avoid analysis paralysis.

---

## Backend Stack

### Framework: FastAPI (Python 3.11+)
**Why:** 
- Native async support for streaming responses
- Automatic OpenAPI documentation
- Excellent WebSocket support
- Strong integration with Python AI/ML ecosystem

**Key Libraries:**
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
websockets==12.0
```

### Database: PostgreSQL 15+ with pgvector

**Why:**
- Mature ACID-compliant relational database
- pgvector extension for semantic search
- Excellent support for recursive CTEs (tree traversal)
- Built-in JSONB for flexible metadata

**Connection:**
```
asyncpg==0.29.0          # Async PostgreSQL driver
sqlalchemy==2.0.23       # ORM
alembic==1.12.1          # Migrations
```

**Extensions Required:**
```sql
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pgvector";
```

### ORM: SQLAlchemy 2.0

**Why:**
- Industry standard Python ORM
- Excellent async support
- Strong relationship modeling
- Supports complex queries (CTEs)

**Pattern:** Async Session with declarative models

---

## AI/ML Infrastructure

### LLM Inference: Ollama (Local)

**Host:** http://localhost:11434

**API Client:**
```
ollama-python==0.1.6
```

**Available Models:**

| Model | Size | Role | Use Case |
|-------|------|------|----------|
| `phi4:latest` | 9.1 GB | Planner | Logical analysis (Phase 2) |
| `dolphin-mistral:7b` | 4.1 GB | Writer | Creative prose (Phase 1) |
| `gemma2:9b` | 5.4 GB | Visualizer | Scene description + vision |
| `nomic-embed-text:latest` | 274 MB | Embeddings | RAG/semantic search |

**Phase 1 Usage:**
- Single model: `dolphin-mistral:7b` for all text generation
- Embeddings: `nomic-embed-text:latest` for vector search

**Phase 2 Upgrade:**
- Implement MoA with model swapping
- Use phi4 for planning, dolphin-mistral for writing

### Image Generation: ComfyUI

**Host:** http://localhost:8188

**API Client:**
```python
# Custom implementation using requests + websockets
import requests
import websockets
import json
```

**Workflow Templates:**
- `flux_basic.json` - Standard FLUX text-to-image
- `flux_ipadapter.json` - Character-consistent generation (Phase 1)
- `flux_pulid.json` - Advanced face consistency (Phase 2)

**Models Path:** `/mnt/` (bind-mounted from host)

**Phase 1 Workflow:**
- FLUX.1 [dev] FP8 (~17GB VRAM)
- IP-Adapter for character references
- Basic prompt engineering

---

## Data & Storage

### Vector Embeddings

**Dimension:** 768 (nomic-embed-text output size)

**Indexing:** HNSW (Hierarchical Navigable Small World)
```sql
CREATE INDEX idx_nodes_embedding ON nodes 
USING hnsw (embedding vector_cosine_ops);
```

**Distance Metric:** Cosine similarity

### File Storage

**Structure:**
```
/home/vince/storyforge/
├── static/
│   ├── characters/      # Character reference images
│   ├── locations/       # Location reference images
│   ├── scenes/          # Generated scene illustrations
│   └── props/           # Prop reference images
├── exports/             # Story exports
└── workflows/           # ComfyUI workflow JSON templates
```

**Image Format:** PNG (lossless)
**Naming Convention:** `{entity_type}_{entity_id}_{timestamp}.png`

---

## Frontend Stack (Phase 1: Minimal)

### Option A: CLI (Recommended for MVP)
```python
# Using standard library
import readline  # For input history
import sys
```

### Option B: Minimal Web UI (Phase 1.5)
```
react==18.2.0
vite==5.0.0
axios==1.6.2
```

**Phase 2 Upgrade:**
- Add React Flow for DAG visualization
- Add ProseMirror for rich text editing
- Add WebSocket client for streaming

---

## Development Tools

### Environment Management
```bash
python3 -m venv .venv
source .venv/bin/activate
```

### Code Quality
```
black==23.11.0           # Code formatting
ruff==0.1.6              # Fast linter
pytest==7.4.3            # Testing
pytest-asyncio==0.21.1   # Async test support
```

### API Testing
```
httpx==0.25.2            # Async HTTP client for tests
```

---

## Configuration Management

### Environment Variables (.env)
```bash
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

# Paths
STATIC_DIR=/home/vince/storyforge/static
EXPORT_DIR=/home/vince/storyforge/exports
WORKFLOW_DIR=/home/vince/storyforge/workflows
```

### Config Module (app/core/config.py)
```python
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    database_url: str
    ollama_host: str
    ollama_model: str
    comfyui_host: str
    # ... etc
    
    class Config:
        env_file = ".env"
```

---

## API Design

### REST Conventions
- Base URL: `http://192.168.1.71:8000/api`
- JSON request/response bodies
- UUID primary keys (not integers)
- ISO 8601 timestamps
- HTTP status codes:
  - 200 OK - Success
  - 201 Created - Resource created
  - 400 Bad Request - Validation error
  - 404 Not Found - Resource not found
  - 500 Internal Server Error - Server error

### WebSocket Protocol
- Path: `/ws/generate`
- JSON messages:
```json
// Client -> Server
{
  "action": "generate",
  "story_id": "uuid",
  "parent_node_id": "uuid",
  "prompt": "user input"
}

// Server -> Client (streaming)
{
  "type": "token",
  "content": "text chunk"
}

// Server -> Client (complete)
{
  "type": "complete",
  "node_id": "uuid",
  "image_path": "path/to/image.png"
}
```

---

## Deployment

### Development Server
```bash
cd /home/vince/storyforge/backend
source .venv/bin/activate
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production (Systemd Service)
```ini
[Unit]
Description=StoryForge Backend
After=network.target postgresql.service

[Service]
User=vince
WorkingDirectory=/home/vince/storyforge/backend
Environment="PATH=/home/vince/storyforge/backend/.venv/bin"
ExecStart=/home/vince/storyforge/backend/.venv/bin/uvicorn app.main:app --host 0.0.0.0 --port 8000

[Install]
WantedBy=multi-user.target
```

---

## Dependencies Summary

### Core Python Requirements
```txt
# Web Framework
fastapi==0.104.1
uvicorn[standard]==0.24.0
python-multipart==0.0.6
websockets==12.0
pydantic==2.5.0
pydantic-settings==2.1.0

# Database
sqlalchemy==2.0.23
asyncpg==0.29.0
alembic==1.12.1
psycopg2-binary==2.9.9

# AI/ML
ollama-python==0.1.6

# Utilities
python-dotenv==1.0.0
aiofiles==23.2.1

# Development
black==23.11.0
ruff==0.1.6
pytest==7.4.3
pytest-asyncio==0.21.1
httpx==0.25.2
```

---

## Version Lock Rationale

**Why lock versions?**
- Reproducible builds
- Avoid breaking changes mid-project
- Simplify debugging

**When to upgrade?**
- Security vulnerabilities
- Critical bug fixes
- Phase transitions (Phase 1 → Phase 2)

**How to upgrade?**
1. Document reason in ARCHITECTURE_DECISIONS.md
2. Test thoroughly
3. Update PROJECT_STATUS.md

---

## Prohibited Dependencies

Do NOT add these (at least in Phase 1):
- ❌ LangChain - Too heavyweight, prefer direct Ollama integration
- ❌ CrewAI - Phase 2 feature, not needed for single-agent MVP
- ❌ Transformers - Use Ollama instead
- ❌ PyTorch - ComfyUI handles this
- ❌ Redis - Unnecessary complexity for single-user local app

---

## Model-to-Agent Mapping (Phase 2)

Reserved for future reference:

| Agent | Model | Context Length | VRAM |
|-------|-------|----------------|------|
| Planner | phi4:latest | 16k | ~9GB |
| Writer | dolphin-mistral:7b | 32k | ~4GB |
| Visualizer | gemma2:9b | 8k | ~5GB |
| Embedder | nomic-embed-text:latest | 8k | <1GB |

**Phase 1:** Only Writer (dolphin-mistral) is active

---

## Notes

- This stack is optimized for **local development** on Debian LXC
- GPU passthrough is configured and available
- All services (Ollama, ComfyUI, PostgreSQL) already running
- No external API dependencies (fully air-gapped capable)
