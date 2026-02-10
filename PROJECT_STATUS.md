# Project Status - StoryForge 2.0

**Last Updated:** 2026-02-07
**Current Phase:** Phase 1 - MVP Foundation COMPLETE
**Current Stage:** All 6 stages complete

---

## Completed Tasks

### Stage 1.1: Project Structure
- [x] Created full directory structure (backend/app/{api,core,models,services}, static/*, exports/, workflows/)
- [x] Initialized Python 3.13 virtual environment at backend/.venv
- [x] Created requirements.txt with Python 3.13-compatible dependency versions
- [x] Created .env with all configuration defaults per TECH_STACK.md
- [x] Implemented app/core/config.py (Pydantic Settings loading from .env)
- [x] Created app/main.py (FastAPI entrypoint with /health endpoint)
- [x] Verified all imports and FastAPI app loads correctly

### Stage 1.2: Database Setup
- [x] Created `storyforge` database in PostgreSQL (owner: vince)
- [x] Installed pgvector and uuid-ossp extensions
- [x] Created app/core/database.py (async engine, session factory, Base declarative class)
- [x] Initialized Alembic for async migrations (alembic init + async env.py)
- [x] Added greenlet dependency (required by SQLAlchemy async)
- [x] Verified async database connection (PostgreSQL 17.6, extensions confirmed)
- [x] Verified Alembic autogenerate + upgrade workflow end-to-end

### Stage 2.1–2.3: Core Models & Migration
- [x] Created Story model (app/models/story.py) — UUID PK, title, genre, timestamps, current_leaf_id FK, JSONB metadata
- [x] Created Node model (app/models/node.py) — UUID PK, self-referential parent_id, story_id FK, content, summary, Vector(768) embedding, node_type, HNSW index
- [x] Created WorldBibleEntity model (app/models/world_bible.py) — UUID PK, story_id FK, entity_type, name, description, base_prompt, image fields, Vector(768) embedding, HNSW index, versioning
- [x] All relationships configured (Story ↔ Node, Story ↔ WorldBibleEntity, Node ↔ parent/children)
- [x] Alembic migration generated and applied (a1178161be24)
- [x] Indexes verified: HNSW on embeddings, B-tree on parent_id and story_id
- [x] ORM CRUD round-trip tested (create story → root node → child node → entity → update leaf)

### Stage 3.1: Ollama Service
- [x] Created OllamaService (app/services/ollama_service.py) with three methods:
  - `generate(prompt, system, model)` — full text generation via chat API
  - `generate_stream(prompt, system, model)` — async iterator yielding text chunks
  - `create_embedding(text)` — 768-dim vector via nomic-embed-text
- [x] Uses ollama.AsyncClient, configurable host/model from .env
- [x] Tested all three methods against live Ollama instance

### Stage 3.2: ComfyUI Service
- [x] Created ComfyUIService (app/services/comfyui_service.py) with:
  - `generate_image(prompt, negative_prompt, seed, width, height, steps, cfg, checkpoint)` — full txt2img pipeline
  - `queue_workflow(workflow)` — submit arbitrary workflow JSON to queue
  - `get_image(filename)` — retrieve image bytes from ComfyUI
  - Automatic polling of /history for completion, configurable timeout
- [x] Default workflow: SDXL Lightning (realvisxlV40) with euler sampler, 6 steps, cfg 1.8
- [x] Images saved to static/images/ with prompt_id prefix for uniqueness
- [x] Tested live: generated 1024x1024 RGB PNG (1.6MB) in seconds

### Stage 3.3: Story Generation Service
- [x] Created StoryGenerationService (app/services/story_service.py) with three methods:
  - `get_story_context(session, node_id, depth)` — walks ancestor chain, returns chronological context
  - `generate_scene(session, story_id, parent_node_id, user_prompt)` — builds context, generates via Ollama (dolphin-mistral), embeds with nomic-embed-text, saves Node, updates story leaf
  - `create_branch(session, node_id, user_prompt)` — creates alternative sibling from same parent
- [x] System prompt tuned for interactive fiction (2-4 paragraphs, reader-driven)
- [x] Tested live: generated 3,027-char scene + 2,419-char branch, 768-dim embeddings, correct leaf tracking

### Stage 3.4: Asset Management Service
- [x] Created AssetService (app/services/asset_service.py) with four methods:
  - `detect_entities(text)` — uses phi4 (logical planner) to extract characters, locations, props as structured JSON
  - `create_entity(session, story_id, entity_data)` — creates WorldBibleEntity with nomic-embed-text embedding
  - `get_entity_references(session, story_id, entity_names)` — case-insensitive name lookup
  - `generate_entity_image(session, entity, seed)` — generates image via ComfyUI, saves path and seed to entity
- [x] Tested live: detected 5 entities from sample scene, created all in DB with embeddings, looked up by name, generated Elara character image via ComfyUI with seed=42
- [x] Note: phi4 may produce duplicate entities (e.g., "Aetheria" as docks and city) — dedup is a Phase 2 refinement

### Stage 4: REST API Layer
- [x] Created Pydantic schemas (app/api/schemas.py) — request/response models for stories, nodes, entities
- [x] Created Story router (app/api/stories.py) — 5 endpoints:
  - `POST /api/stories` — create story with auto-generated root node
  - `GET /api/stories` — list all stories
  - `GET /api/stories/{id}` — get story by ID
  - `GET /api/stories/{id}/tree` — get full narrative DAG
  - `DELETE /api/stories/{id}` — delete story (cascades)
- [x] Created Node router (app/api/nodes.py) — 5 endpoints:
  - `POST /api/stories/{id}/nodes` — generate next scene (calls Ollama)
  - `POST /api/nodes/{id}/branch` — create alternative branch
  - `GET /api/nodes/{id}` — get single node
  - `GET /api/nodes/{id}/path` — get root-to-node path
  - `PATCH /api/nodes/{id}` — manually edit content
- [x] Created Entity router (app/api/entities.py) — 6 endpoints:
  - `POST /api/stories/{id}/entities` — manually add entity (with embedding)
  - `GET /api/stories/{id}/entities` — list all entities
  - `POST /api/stories/{id}/entities/detect` — auto-detect from text (phi4), deduplicate, create
  - `GET /api/entities/{id}` — get entity details
  - `POST /api/entities/{id}/image` — generate/regenerate image (ComfyUI)
  - `PATCH /api/entities/{id}` — update entity (bumps version)
- [x] Wired all routers into app/main.py, added static file serving for images
- [x] Smoke tested all 16 API endpoints: CRUD, 404s, cascade delete all correct
- [x] OpenAPI docs auto-generated at /docs

### Stage 5: CLI Interface
- [x] Added `generate_scene_stream` to StoryGenerationService — yields text chunks then final Node
- [x] Created interactive CLI (backend/cli.py) with full feature set:
  - `/new` — create story with title, genre, opening direction; streams first scene
  - `/load` — list and select existing stories; shows current scene
  - `/status` — story info (title, genre, node count, entity count)
  - `/tree` — visual narrative tree with current-node marker
  - `/goto <n>` — jump to any node in the tree
  - `/branch [direction]` — create alternative scene from current branch point
  - `/entities` — list world bible with image indicators
  - `/detect` — auto-detect entities in current scene (phi4 + dedup)
  - `/image <n>` — generate reference image for entity (ComfyUI)
  - `/export` — markdown export with entity images, root-to-leaf path
  - `/help`, `/quit`
- [x] Streaming output: scenes stream token-by-token to terminal
- [x] Color-coded terminal UI (ANSI: cyan commands, green info, yellow warnings, magenta entity types)
- [x] Tested: streaming generation (2,153 chars), export to markdown
- [x] Run with: `cd backend && .venv/bin/python cli.py`

### Stage 6: Web Frontend
- [x] Created WebSocket endpoint (backend/app/api/websocket.py) — WS /ws/generate
  - Handles `generate` and `branch` actions
  - Streams tokens as `{ type: "token", content: "..." }`
  - Sends `{ type: "complete", node: {...} }` on finish
  - Each request gets its own async session (no Depends())
  - Supports optional `parent_node_id` for tree navigation
- [x] Added export endpoint — `GET /api/stories/{id}/export/markdown`
  - Returns markdown file as download with Content-Disposition header
  - Includes world bible entities with image references and root-to-leaf scenes
- [x] Updated config — added `frontend_dir` setting
- [x] Updated main.py — registered WS router, mounted frontend at /app, root route serves index.html
- [x] Created vanilla HTML/CSS/JS frontend (no build tools, ES modules):
  - `frontend/index.html` — SPA shell with lobby + writing views
  - `frontend/css/style.css` — Dark theme, CSS Grid layout
  - `frontend/js/app.js` — Entry point, view switching, toast notifications
  - `frontend/js/api.js` — fetch() wrappers for all 16+ REST endpoints
  - `frontend/js/ws.js` — WebSocket client with auto-reconnect
  - `frontend/js/story-list.js` — Lobby: list/create/delete stories
  - `frontend/js/story-writer.js` — Scene display, streaming with blinking cursor, prompt input
  - `frontend/js/entity-panel.js` — Entity list, detect entities, generate images with thumbnails
  - `frontend/js/tree-view.js` — Narrative tree display, click-to-navigate
- [x] Verified: server starts, serves frontend, REST API works, export downloads markdown

### Task 10: End-to-End Browser Test
- [x] API flow verified: create story → generate 2 scenes → branch → detect entities → tree → export
- [x] All 16 REST endpoints return correct data, branching creates correct sibling nodes
- [x] Entity detection (phi4) extracts characters/locations/props with dedup
- [x] Export follows current_leaf_id path correctly (root → branch or root → scene chain)
- [x] Narrative tree correctly shows DAG: root → scene1 → scene2, root → branch
- [x] Frontend bugs found and fixed:
  - **tree-view.js**: Race condition — `setTimeout(render, 100)` replaced with `await navigateToNode()` + synchronous `render()`
  - **ws.js**: `connect()` now returns a Promise, resolving on open; handles CLOSING/CLOSED socket cleanup; prevents duplicate CONNECTING sockets
  - **story-writer.js**: `loadStory()` now awaits socket connection before sending; `unload()` cleans up cursor and partial scenes on navigation away
- [x] ComfyUI down (no CUDA GPU available in LXC) — image generation untestable; covered by error handling task
- [x] Server starts and serves frontend at / with all JS modules loading correctly

### Task 11: Error Handling & Graceful Degradation
- [x] Created custom exception hierarchy (app/core/exceptions.py):
  - `StoryForgeError` base, `ServiceUnavailableError` (→ 503), `ServiceTimeoutError` (→ 504), `GenerationError` (→ 502)
- [x] **OllamaService** — catches `ConnectError`, `TimeoutException`, `ResponseError`; wraps in custom exceptions; mid-stream errors handled; added `check_health()`
- [x] **ComfyUIService** — catches connection/timeout/HTTP errors in all methods; `_wait_for_completion` propagates custom exceptions properly; added `check_health()`
- [x] **Global exception handlers** in main.py — maps exceptions to structured JSON responses with `detail`, `service`, and `error_type` fields
- [x] **Health endpoint enhanced** — `/health` now checks Ollama and ComfyUI concurrently, returns `"ok"` or `"degraded"` status with per-service breakdown
- [x] **WebSocket handler** — structured error messages with `error_type` and `service` fields; specific handling for each exception type
- [x] **Entity detection** — `GenerationError` returns empty list (graceful), `ServiceUnavailable`/`Timeout` propagate to client
- [x] **Frontend error handling**:
  - `api.js` — `ApiError` class with `isServiceUnavailable` / `isTimeout` helpers; network errors caught
  - `ws.js` — passes `error_type` and `service` to error callback
  - `story-writer.js` — user-friendly messages per error type ("Ollama is not available", "took too long", etc.)
  - `entity-panel.js` — specific messages for detection and image generation failures
- [x] Verified: server starts, health endpoint works, all imports clean, exception handlers registered

### Task 12: Documentation
- [x] Created `docs/USER_GUIDE.md` — covers web UI, CLI, REST API, WebSocket protocol, error states, concepts (narrative DAG, world bible, AI models)
- [x] Created `docs/DEPLOYMENT.md` — system requirements, installation steps, configuration, running (dev/production/systemd), database management, ComfyUI setup, troubleshooting
- [x] API documentation auto-generated at /docs (Swagger UI) — no manual work needed
- [x] Updated PROJECT_STATUS.md with final MVP status

---

## Phase 1 MVP — Complete

All 6 stages of Phase 1 are done:
- Stage 1: Project structure and database setup
- Stage 2: Data layer (narrative DAG with pgvector)
- Stage 3: Services layer (Ollama, ComfyUI, story generation, asset management)
- Stage 4: REST API (16 endpoints + WebSocket)
- Stage 5: CLI interface
- Stage 6: Web frontend, E2E testing, error handling, documentation

### What Works
- Create stories with AI-generated scenes (streaming)
- Branch narratives into alternate timelines
- Navigate the full narrative DAG
- Detect and track characters, locations, props
- Generate reference images via ComfyUI
- Export to Markdown
- Graceful degradation when services are down
- Both CLI and web interfaces

### Ready for Phase 2
Potential next steps (not currently planned):
- Multi-agent MoA (Planner/Writer split)
- RAG for long-form memory
- Advanced image consistency (IP-Adapter, LoRA)
- Rich web UI with visual DAG editor
- Audio narration

---

### Git Repository Initialization
- [x] Created `.gitignore` (excludes .venv, .env, __pycache__, generated images, exports, .claude/)
- [x] Created `backend/.env.example` (credential-free template)
- [x] Added `.gitkeep` files for empty directories (static/images, exports, workflows)
- [x] Initialized git repo on `main` branch
- [x] Initial commit: 59 files, 10,962 lines — full Phase 1 MVP

---

## Next Session

- [ ] Consider Phase 2 planning

## Blockers

None.

---

## Architecture Notes

- Python 3.13.5 on server (newer than TECH_STACK.md assumed)
- All deps bumped to compatible versions; documented in requirements.txt
- FastAPI app runs at http://192.168.1.71:8000
- Swagger docs at /docs, health check at /health
- PostgreSQL 17.6 running on port 5432
- Alembic configured for async (asyncpg + greenlet)
- Migrations: 67150de53c78 (initial empty) → a1178161be24 (core tables)
- HNSW indexes use vector_cosine_ops with m=16, ef_construction=64
- Embedding dimension: 768 (matches nomic-embed-text model)
- Ollama models: dolphin-mistral:7b (creative writer), phi4:latest (planner), gemma2:9b (visualizer), nomic-embed-text (embeddings)
- ComfyUI 0.7.0 with RTX 3090 (24GB VRAM), PyTorch 2.6.0+cu124
- Available checkpoints: CyberRealisticPony, blendermix, flux1-kontext, mistoonAnime, realism-sdxl, realvisxlV40 (default), sd3.5_large
- Default pipeline: SDXL Lightning — euler/sgm_uniform, 6 steps, cfg 1.8 (fast generation)
