# StoryForge 2.0 User Guide

StoryForge is an AI-powered interactive storytelling application. You write story directions, the AI generates scenes, and you can branch the narrative into alternate timelines. A world bible tracks characters, locations, and props, with optional AI-generated reference images.

---

## Quick Start

### Start the Server

```bash
cd /home/vince/storyforge/backend
.venv/bin/python -m uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Then open your browser to `http://192.168.1.71:8000` for the web UI, or use the CLI:

```bash
cd /home/vince/storyforge/backend
.venv/bin/python cli.py
```

---

## Web Interface

### Lobby

When you open StoryForge in a browser, you'll see the lobby with your existing stories (if any) and a form to create a new one.

**Creating a story:**
1. Enter a title and optional genre
2. Write an opening direction (e.g., "A detective arrives at a foggy dockyard at midnight")
3. Click **Create**

The AI will generate the first scene based on your direction.

**Loading a story:**
Click any story in the list to continue where you left off.

### Writing View

The writing view has three panels:

**Main area (center):** Shows all scenes in order. New scenes appear at the bottom with a streaming animation as the AI writes.

**Prompt bar (bottom):** Type your direction for the next scene, then:
- Click **Continue** (or press Ctrl+Enter) to generate the next scene
- Click **Branch** to create an alternate version from the current point

**Entity panel (right sidebar):**
- Shows detected characters, locations, and props
- Click **Detect Entities** to scan the current scene with AI
- Click an entity's icon to generate a reference image via ComfyUI

**Tree view (right sidebar):** Shows the narrative DAG. Click any node to jump to that point in the story.

**Export:** Click the export button in the header to download a Markdown file of the current story path, including entity descriptions and images.

### Branching

Branching creates an alternate timeline from the same parent scene. The original and branch coexist in the narrative tree. Use the tree view to switch between branches.

### Error States

If Ollama or ComfyUI is down, the UI will show specific messages:
- **"Ollama is not available"** — The LLM server needs to be started
- **"ComfyUI is not available"** — Image generation is offline (story writing still works)
- **"took too long to respond"** — Service timed out; try again or use a shorter prompt

---

## CLI Interface

The CLI provides the same features in a terminal interface.

```bash
cd /home/vince/storyforge/backend
.venv/bin/python cli.py
```

### Commands

| Command | Description |
|---------|-------------|
| `/new` | Create a new story (prompts for title, genre, opening) |
| `/load` | List and select an existing story |
| `/status` | Show current story info (title, node count, entity count) |
| `/tree` | Display the narrative tree with numbered nodes |
| `/goto <n>` | Jump to node number `n` from the tree display |
| `/branch [direction]` | Create an alternate branch from current scene |
| `/entities` | List all world bible entities |
| `/detect` | Auto-detect entities in the current scene |
| `/image <n>` | Generate a reference image for entity number `n` |
| `/export` | Export story to Markdown file in `exports/` |
| `/help` | Show command help |
| `/quit` | Exit |

Anything that isn't a command is treated as a direction for the next scene. Scenes stream token-by-token to the terminal.

### Example Session

```
> /new
  Title: The Last Signal
  Genre (optional): sci-fi
  Opening scene direction: A lone radio operator picks up an impossible signal from a star that went supernova centuries ago

  Generating...
  [AI-generated scene streams here...]

> The operator tries to decode the signal, discovering it contains coordinates

  Generating...
  [Next scene streams...]

> /detect
  > Detected 3 entities, created 3 new
  [character] Dr. Elara Voss — A weary radio operator with silver-streaked hair...
  [location] Outpost Meridian — A remote listening station on a barren moon...
  [prop] Signal Decoder — An ancient piece of equipment...

> /tree
  1. [root] [Beginning of 'The Last Signal']
    2. [scene] A lone radio operator picks up...
      3. [scene] The operator tries to decode...

> /branch The operator ignores the signal and goes to sleep instead

  Branching...
  [Alternative scene streams...]

> /export
  > Exported to /home/vince/storyforge/exports/The Last Signal.md
```

---

## REST API

Full API documentation is auto-generated at `http://192.168.1.71:8000/docs` (Swagger UI).

### Key Endpoints

**Stories:**
- `POST /api/stories` — Create story `{"title": "...", "genre": "..."}`
- `GET /api/stories` — List all stories
- `GET /api/stories/{id}` — Get story details
- `GET /api/stories/{id}/tree` — Get full narrative DAG
- `DELETE /api/stories/{id}` — Delete story and all data

**Nodes (Scenes):**
- `POST /api/stories/{id}/nodes` — Generate next scene `{"user_prompt": "..."}`
- `POST /api/nodes/{id}/branch` — Branch from node `{"user_prompt": "..."}`
- `GET /api/nodes/{id}` — Get node details
- `GET /api/nodes/{id}/path` — Get root-to-node path
- `PATCH /api/nodes/{id}` — Edit node content `{"content": "..."}`

**Entities (World Bible):**
- `POST /api/stories/{id}/entities` — Add entity manually
- `GET /api/stories/{id}/entities` — List entities
- `POST /api/stories/{id}/entities/detect` — Auto-detect from text `{"text": "..."}`
- `GET /api/entities/{id}` — Entity details
- `POST /api/entities/{id}/image` — Generate reference image
- `PATCH /api/entities/{id}` — Update entity

**Streaming:**
- `WS /ws/generate` — WebSocket for streaming scene generation

**Utility:**
- `GET /health` — Service health with Ollama/ComfyUI status
- `GET /api/stories/{id}/export/markdown` — Download story as Markdown

### WebSocket Protocol

Connect to `ws://192.168.1.71:8000/ws/generate`, then send JSON messages:

**Generate a scene:**
```json
{"action": "generate", "story_id": "uuid", "prompt": "what happens next"}
```

**Create a branch:**
```json
{"action": "branch", "story_id": "uuid", "node_id": "uuid", "prompt": "alternative"}
```

**Responses stream as:**
```json
{"type": "token", "content": "The "}
{"type": "token", "content": "detective "}
{"type": "complete", "node": {"id": "...", "content": "...", ...}}
```

**Errors:**
```json
{"type": "error", "message": "...", "error_type": "service_unavailable", "service": "Ollama"}
```

### Error Responses

The API returns structured errors for service failures:

| HTTP Status | `error_type` | Meaning |
|-------------|-------------|---------|
| 502 | `generation_error` | AI generation failed |
| 503 | `service_unavailable` | Ollama or ComfyUI is down |
| 504 | `service_timeout` | Service request timed out |

All error responses include `detail`, `error_type`, and `service` fields.

---

## Concepts

### Narrative DAG

Stories are stored as a directed acyclic graph (DAG) of nodes. Each node contains one scene. The root node is created automatically. When you generate a scene, it becomes a child of the current node. When you branch, a sibling is created from the same parent.

The `current_leaf_id` on the story tracks which node you're currently at. The tree view shows all branches.

### World Bible

The world bible tracks entities discovered in your story:
- **Characters** — People, creatures, etc.
- **Locations** — Places, settings
- **Props** — Objects, artifacts

Entities are detected by the AI (using the phi4 model) or added manually. Each entity has a description and an image generation prompt. Reference images are generated via ComfyUI.

### AI Models

StoryForge uses different models for different tasks:
- **dolphin-mistral:7b** — Creative writing (scene generation)
- **phi4:latest** — Logical analysis (entity detection)
- **nomic-embed-text** — Embedding generation (for future semantic search)

Image generation uses SDXL Lightning via ComfyUI with the realvisxlV40 checkpoint.
