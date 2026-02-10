# Project Status - StoryForge 2.0

**Last Updated:** 2026-02-10
**Current Phase:** Phase 2 - Intelligence & Consistency
**Current Stage:** Stage 5.1 (Test Suite) — COMPLETE

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

### Phase 2, Stage 1: Content Mode & Story Settings
- [x] Added `content_mode` (VARCHAR, default 'unrestricted'), `auto_illustrate` (BOOLEAN), `context_depth` (INTEGER) to Story model
- [x] Alembic migration applied: 795905b88fe5
- [x] Added `writer_model_unrestricted` and `writer_model_safe` to Settings + .env
- [x] Created `StoryUpdate` Pydantic schema for PATCH operations
- [x] Added `PATCH /api/stories/{id}` endpoint for updating story settings
- [x] `StoryCreate` now accepts `content_mode` field
- [x] `StoryResponse` returns `content_mode`, `auto_illustrate`, `context_depth`
- [x] `StoryGenerationService` selects writer model and system prompt based on story's `content_mode`
- [x] Unrestricted mode: creative-freedom system prompt, uses `writer_model_unrestricted` from config
- [x] Safe mode: family-friendly system prompt, uses `writer_model_safe` from config
- [x] Frontend: content mode toggle in create-story form (Unrestricted/Safe buttons)
- [x] Frontend: content mode indicator in writing view header (click to toggle)
- [x] Frontend: story cards show content mode in metadata
- [x] CSS: toggle group, content mode indicator with color coding (red=unrestricted, green=safe)
- [x] Validation rejects invalid content_mode values (regex pattern)
- [x] All 17 API endpoints verified working
- [x] Both content modes default to dolphin-mistral:7b until new models are pulled

### Phase 2, Stage 2: RAG for Long-Form Memory — COMPLETE
- [x] Created `ContextService` (app/services/context_service.py) — full RAG context assembly:
  - `build_context()` — assembles from ancestors + semantic search + entity lookup
  - `_get_ancestors()` — walks parent chain (configurable depth via `story.context_depth`)
  - `_semantic_node_search()` — pgvector cosine distance query, excludes ancestor nodes
  - `_semantic_entity_search()` — vector search on world_bible entities
  - `_name_match_entities()` — scans user prompt for entity names (case-insensitive)
  - `_assemble()` — structured output with token budget (ancestors > entities > history)
- [x] Wired `ContextService` into `StoryGenerationService` (replaces old `get_story_context`)
  - Both `generate_scene` and `generate_scene_stream` use `context_svc.build_context()`
  - Uses `story_obj.context_depth` for ancestor depth
- [x] Added summary generation via phi4 after scene creation (`_generate_summary` method)
  - Generates 1-2 sentence summaries for efficient RAG retrieval
  - Non-blocking — failure logged but doesn't affect scene
- [x] Re-embedding on PATCH for nodes (app/api/nodes.py) — content edits re-embed via nomic-embed-text
- [x] Re-embedding on PATCH for entities (app/api/entities.py) — description edits re-embed
- [x] Bug fix: `current_leaf_id` not persisting after ContextService refactor
  - Root cause: `story_obj` loaded early, SQLAlchemy identity map stale after many queries
  - Fix: Re-fetch Story object right before setting `current_leaf_id` in both `generate_scene` and `generate_scene_stream`
- [x] Smoke tested: created story → generated 2 scenes → verified `current_leaf_id` persisted correctly in DB
- [x] Cleaned up all test data from database

### Phase 2, Stage 3: MoA Planner/Writer Split — COMPLETE (2074ec0)
- [x] Added MoA config settings: `planner_model`, `moa_enabled`, `planner_keep_alive`, `writer_keep_alive` to config + .env
- [x] Added `keep_alive` parameter to `OllamaService.generate()` and `generate_stream()`
- [x] Created `ModelManager` (app/services/model_manager.py):
  - `generation_lock` — asyncio.Semaphore(1) to serialize generation (prevents VRAM contention)
  - `ensure_loaded()` — zero-token preload request
  - `unload()` — keep_alive=0 to free VRAM
  - `list_loaded()` — query Ollama /api/ps
- [x] Created `PlannerService` (app/services/planner_service.py):
  - `plan_beat()` — uses phi4 to generate structured JSON beats
  - JSON parsing with markdown fence stripping and extraction fallback
  - Falls back to minimal beat on parse failure (never crashes pipeline)
  - Validates characters against world bible, flags unknowns in continuity_warnings
- [x] Created `WriterService` (app/services/writer_service.py):
  - `write_scene()` and `write_scene_stream()` — expands beats into prose
  - Formats beat as natural-language scene plan in prompt
  - Content-mode-aware system prompts (unrestricted vs safe)
- [x] Added `beat` and `continuity_warnings` properties to Node model (reads from metadata_ JSONB)
- [x] Added `beat` and `continuity_warnings` fields to NodeResponse schema
- [x] Refactored `StoryGenerationService`:
  - MoA path: planner → writer under generation_lock semaphore
  - Stores beat in node.metadata_ (zero migrations needed)
  - Stream yields phase signals: `{"phase": "planning"}`, `{"phase": "writing"}`
  - Single-model fallback when `MOA_ENABLED=false`
  - `_generate_summary()` uses configurable planner_model
  - `_get_world_bible_entities()` helper for planner input
- [x] WebSocket handler: dispatches `{"type": "phase", "phase": "..."}` messages on dict phase signals
- [x] `_node_to_dict()` includes `beat` and `continuity_warnings`
- [x] CLI: phase signals show "Planning scene..." / "Writing..." indicators
- [x] CLI: `/beat` command displays current scene's planner beat
- [x] CLI: continuity warnings shown after scene generation
- [x] Frontend ws.js: added `onPhase` callback
- [x] Frontend story-writer.js: phase indicator updates ("Planning scene..." → "Writing...")
- [x] Frontend story-writer.js: beat displayed as expandable `<details>` below each scene
- [x] Frontend story-writer.js: continuity warnings shown as toasts on completion
- [x] Frontend style.css: `.scene-beat` styles for expandable beat display
- [x] Health endpoint: includes `moa_enabled` in response
- [x] All imports verified clean, config loads correctly, Node properties tested

### Phase 2, Stage 4: Image Consistency (IP-Adapter) — COMPLETE
- [x] Created ComfyUI workflow templates:
  - `workflows/scene_ipadapter.json` — IP-Adapter workflow (11 nodes: checkpoint + IP-Adapter model + CLIP vision + LoadImage → IPAdapter apply → KSampler → VAEDecode → SaveImage)
  - `workflows/scene_basic.json` — Plain txt2img for scenes without references (7 nodes, landscape 1024x576)
- [x] Added illustration config settings to `config.py` + `.env` + `.env.example`:
  - `ipadapter_enabled` (bool, default true), `ipadapter_weight` (float, default 0.7)
  - `scene_image_width` (1024), `scene_image_height` (576)
- [x] Added `illustration_path` property to Node model (reads from `metadata_` JSONB — zero migrations)
- [x] Added `illustration_path` field to `NodeResponse` schema
- [x] Added `upload_image()` method to `ComfyUIService` — multipart POST to ComfyUI `/upload/image`
- [x] Created `IllustrationService` (`app/services/illustration_service.py`):
  - `illustrate_scene()` — generates scene illustration with IP-Adapter or plain txt2img fallback
  - `_build_image_prompt()` — extracts prompt from planner beat (setting, characters, events, tone) or falls back to scene content
  - `_find_reference_image()` — looks up character/location entities with reference images from the beat's `characters_present`
  - `_generate_ipadapter()` — loads IP-Adapter workflow, uploads ref image, configures and queues
  - `_generate_basic()` — loads basic workflow for scenes without entity references
  - `illustration_lock` — asyncio.Semaphore(1) prevents concurrent ComfyUI illustration requests
  - Stores `illustration_path` in `node.metadata_` with `flag_modified()` for JSONB mutation detection
- [x] Added REST endpoint: `POST /api/nodes/{node_id}/illustrate` — generates illustration, returns updated NodeResponse
- [x] Wired auto-illustrate into WebSocket handler:
  - `_node_to_dict()` includes `illustration_path`
  - `_handle_generate()` and `_handle_branch()` check `story.auto_illustrate` after completion
  - `asyncio.create_task(_auto_illustrate_and_notify())` — fire-and-forget background illustration
  - Sends `{"type": "illustration", "node_id": "...", "path": "/static/images/..."}` on WebSocket
  - Graceful failure — swallows exceptions if WebSocket is closed
- [x] Frontend changes:
  - `api.js`: added `illustrateNode(nodeId)` function
  - `ws.js`: added `onIllustration` callback, dispatches on `msg.type === 'illustration'`
  - `story-writer.js`: scene illustrations shown inline, "Illustrate"/"Re-illustrate" button (visible on hover), auto-illustrate toggle button, `handleIllustration()` for WebSocket notifications
  - `style.css`: `.scene-illustration` (rounded, full-width), `.scene-actions` (opacity transition on hover), `#auto-illustrate-btn.active` styling
  - `index.html`: auto-illustrate toggle button in writing view header
- [x] CLI: added `/illustrate` command — generates scene illustration for current node, displays saved path
- [x] All imports verified clean, FastAPI app loads successfully, all 18 REST endpoints + WebSocket registered

#### E2E Verification (all 13 areas passed)
- [x] Frontend serving (HTML/CSS with illustration classes)
- [x] Create story + generate scene 1 with beat
- [x] Entity detection (4 entities: 2 characters, 1 location, 1 prop)
- [x] Entity reference image generation (character portrait via ComfyUI)
- [x] Scene illustration via IP-Adapter (uses character ref for visual consistency)
- [x] Auto-illustrate toggle (on/off persists)
- [x] Scene 2 + branch generation
- [x] Scene illustration via basic txt2img fallback (no ref image)
- [x] Tree (4 nodes, 2 illustrated) + markdown export
- [x] Error cases (root node → 400, missing → 404)
- [x] Images on disk verified
- [x] WebSocket auto-illustrate (scene generated → illustration msg received on WS)
- [x] Cleanup (story deleted, 0 remaining)

### Phase 2, Stage 5.1: Automated Test Suite — COMPLETE
- [x] Created `storyforge_test` PostgreSQL database with pgvector + uuid-ossp extensions
- [x] Added `pytest-mock` to requirements.txt
- [x] Created `pyproject.toml` with pytest + asyncio config
- [x] Created test infrastructure:
  - `tests/conftest.py` — env override, sync DDL setup/teardown, per-test async engine + transactional rollback, ASGI test client with dependency override
  - `tests/factories.py` — `make_story`, `make_node`, `make_entity`, `make_beat`, `fake_embedding` helpers
  - `tests/unit/conftest.py` — `mock_session`, `mock_ollama_client` fixtures
  - `tests/integration/conftest.py` — `sample_story`, `sample_story_with_scene`, `sample_entity` fixtures
- [x] **117 unit tests** covering all services and models:
  - `test_schemas.py` (17) — Pydantic validation for all request/response schemas
  - `test_node_model.py` (9) — Node properties: beat, illustration_path, continuity_warnings
  - `test_ollama_service.py` (16) — generate, stream, embed, health, all error paths
  - `test_comfyui_service.py` (14) — queue, wait, save, upload, health, all error paths
  - `test_model_manager.py` (8) — lock, ensure_loaded, unload, list_loaded
  - `test_planner_service.py` (9) — plan_beat, _parse_beat (JSON, markdown fences, fallback), character warnings
  - `test_writer_service.py` (9) — model selection, system prompts, format_beat_prompt, write/stream
  - `test_context_service.py` (7) — _assemble budget logic, section priorities, truncation
  - `test_story_service.py` (8) — MoA pipeline, single-model fallback, branch, prompt building
  - `test_illustration_service.py` (8) — IP-Adapter vs basic workflow, prompt building, error handling
  - `test_asset_service.py` (9) — detect_entities, create_entity, generate_entity_image
- [x] **45 integration tests** with real PostgreSQL:
  - `test_story_api.py` (17) — CRUD, tree, export, validation, 404s
  - `test_node_api.py` (11) — generate (mocked), branch, get, path, update, illustrate
  - `test_entity_api.py` (9) — create, list, detect, get, image, update
  - `test_health_api.py` (3) — healthy, degraded (ollama down), both down
  - `test_websocket.py` (5) — invalid JSON, unknown action, streaming, story/node not found
- [x] **162 tests total, all passing in ~3 seconds**
- [x] No live Ollama/ComfyUI required — all external services mocked
- [x] Integration tests use real PostgreSQL with pgvector for accurate query testing

## Next Steps

1. Phase 2, Stage 5.2: Incremental UI improvements (story settings panel, inline illustrations, beat display, continuity warnings, loading states)
2. Phase 2, Stage 5.3: CLI improvements (/mode, /context commands, updated /status)
3. Pull new writer models (Dark Champion, Gemma 3 27B QAT, Hermes 3 8B) — see PHASE_2_ROADMAP.md "New Model Requirements"
4. Phase 3 planning (React frontend rewrite, audio narration, EPUB export, etc.)

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
- Migrations: 67150de53c78 (initial) → a1178161be24 (core tables) → 795905b88fe5 (content mode + story settings)
- Stage 2 RAG: ContextService provides structured context (ancestors + semantic nodes + world bible entities) with token budget
- Stage 3 MoA: Two-pass pipeline (PlannerService → WriterService) under ModelManager semaphore; beat stored in metadata_ JSONB
- HNSW indexes use vector_cosine_ops with m=16, ef_construction=64
- Embedding dimension: 768 (matches nomic-embed-text model)
- Ollama models: dolphin-mistral:7b (creative writer), phi4:latest (planner), gemma2:9b (visualizer), nomic-embed-text (embeddings)
- ComfyUI 0.7.0 with RTX 3090 (24GB VRAM), PyTorch 2.6.0+cu124
- Available checkpoints: CyberRealisticPony, blendermix, flux1-kontext, mistoonAnime, realism-sdxl, realvisxlV40 (default), sd3.5_large
- Default pipeline: SDXL Lightning — euler/sgm_uniform, 6 steps, cfg 1.8 (fast generation)
