# Phase 2 Roadmap - Intelligence & Consistency

## Goal
Make StoryForge smarter, more visually consistent, and content-aware. The AI should remember the full story, plan before writing, maintain character appearances across illustrations, and respect user content preferences.

## Success Criteria
- [ ] AI recalls characters/events from 20+ scenes ago (RAG)
- [ ] Story scenes have logical structure from planner before creative writing
- [ ] Character illustrations are visually consistent across 5+ images (IP-Adapter)
- [ ] Safe mode toggle switches between censored and uncensored generation
- [ ] Automated test suite covers core services and API endpoints

---

## Stage 1: Content Mode & Story Settings

**Why first:** This is a quick, high-value feature that affects how all subsequent AI work behaves. Building it first means MoA and RAG respect the content mode from day one.

### 1.1 Content Mode Toggle

Add a per-story `content_mode` setting that controls which LLM is used for text generation and what system prompts are applied.

**Modes:**
| Mode | Writer Model | Persona | Behavior |
|------|-------------|---------|----------|
| `unrestricted` | Dark Champion 8X4B V2 (~13GB) | "Grindhouse Director" | Native uncensored (abliterated). No content guardrails. Mature themes (violence, sexual content) permitted. 128k context window for long-form consistency. MoE architecture for fast inference. |
| `safe` | Gemma 3 27B QAT (~14GB) | "International Poet" | Heavily aligned with built-in safety guardrails. High literary quality. Excellent multilingual support (French, Japanese, Russian). Will refuse mature themes. |

**Fallback models** (lighter, for when VRAM is constrained):
| Mode | Fallback Model | Notes |
|------|---------------|-------|
| `unrestricted` | `dolphin-mistral:7b` (4GB) | Current Phase 1 writer. Uncensored but smaller/less capable. |
| `safe` | Hermes 3 8B (~5GB) | Nous Research. Balanced, steerable, no heavy moralizing. |

**Model selection reference** (from brainstorming report Section 3.1.2):
- Dark Champion is an "abliterated" MoE model — refusal vectors mathematically removed. 128k context makes it the only small model viable for full-length novellas.
- Gemma 3 27B QAT uses Google's quantization-aware training (trained knowing it would be int4, so minimal quality loss). Its heavy alignment makes it prone to "moralizing" on mature themes — a feature, not a bug, for safe mode.
- Midnight Miqu 70B ("Gold Standard" novelist) was considered but requires ~42GB for weights alone — impractical on dual 3090s with any meaningful context window.

**Implementation:**
- [ ] Add `content_mode` column to `stories` table (VARCHAR, default `'unrestricted'`)
- [ ] Add `content_mode` to Story Pydantic schemas (request/response)
- [ ] Alembic migration for new column
- [ ] Add writer model config to Settings: `writer_model_unrestricted`, `writer_model_safe` (configurable in .env)
- [ ] Update `StoryGenerationService` to select model based on `story.content_mode`
- [ ] Update system prompts: unrestricted mode gets creative-freedom prompt, safe mode gets appropriate-content prompt
- [ ] API: `PATCH /api/stories/{id}` already supports updates — add `content_mode` field
- [ ] Frontend: toggle switch in story settings
- [ ] CLI: `/mode` command to switch
- [ ] Pull new models via Ollama (see New Model Requirements section)

### 1.2 Story Settings Expansion

While touching the story model, add settings that Phase 2 features will need:

- [ ] `auto_illustrate` (BOOLEAN, default FALSE) — auto-generate scene images (AD-011)
- [ ] `context_depth` (INTEGER, default 5) — how many ancestor nodes to include in context (overridden by RAG in Stage 2)
- [ ] `metadata` JSONB field already exists — use for additional per-story preferences

**Deliverable:** Content mode toggle working end-to-end, model selected per story.

---

## Stage 2: RAG for Long-Form Memory

**Why:** Currently `get_story_context()` walks the ancestor chain (last N nodes). In a long story, the AI forgets characters, plot points, and world details introduced early on. RAG fixes this by searching all past content semantically.

### 2.1 Context Retrieval Service

Build a `ContextService` that assembles rich context for scene generation:

```
ContextService.build_context(session, story_id, parent_node_id, user_prompt) -> str
```

**Context assembly strategy:**
1. **Ancestor chain** (always included) — last 3 direct ancestors for narrative flow
2. **Semantic search** — embed the user's prompt, query pgvector for relevant past nodes (top 5 by cosine similarity, excluding ancestors already included)
3. **World bible lookup** — embed prompt, find relevant entities (characters, locations, props) by vector similarity
4. **Entity name matching** — scan prompt for known entity names, include their full descriptions

**Implementation:**
- [ ] Create `app/services/context_service.py`
- [ ] Implement ancestor chain retrieval (extract from existing `story_service.py`)
- [ ] Implement semantic node search (pgvector cosine similarity query)
- [ ] Implement world bible entity retrieval (vector + name matching)
- [ ] Assemble structured context block with sections: `[RECENT SCENES]`, `[RELEVANT HISTORY]`, `[WORLD BIBLE]`
- [ ] Update `StoryGenerationService.generate_scene()` to use `ContextService` instead of `get_story_context()`
- [ ] Add context window budget (count tokens approximately, prioritize recent > entities > history)

### 2.2 Embedding Maintenance

Ensure all content has embeddings for RAG to work:

- [ ] Verify all nodes get embeddings on creation (already done in `generate_scene`)
- [ ] Add embedding to manually edited nodes (`PATCH /api/nodes/{id}` should re-embed on content change)
- [ ] Add embedding to world bible entities on update (already done on create, add on `PATCH`)
- [ ] Background re-embedding endpoint for existing content without embeddings

### 2.3 Summary Generation

For long stories, full node content is too large for context. Add summaries:

- [ ] After scene generation, generate a 1-2 sentence summary via Ollama (phi4 for conciseness)
- [ ] Store in existing `summary` column on nodes table
- [ ] RAG uses summaries for semantic search results (full content only for direct ancestors)
- [ ] Batch summarize existing nodes that lack summaries

**Deliverable:** AI remembers the full story. Generating scene 25 correctly references a character introduced in scene 3.

---

## Stage 3: Multi-Agent MoA (Planner/Writer Split)

**Why:** Single-model generation produces creative prose but can lose plot coherence. Splitting planning from writing produces structurally better stories.

### 3.1 Agent Architecture

Implement a two-pass generation pipeline:

```
User prompt
    → Planner (phi4, 9GB, GPU 0) — generates story beat, checks consistency
    → Writer (Dark Champion or Gemma 3, ~13-14GB, GPU 1) — writes prose from beat + context
    → Embedder (nomic-embed-text, 274MB) — embeds final content
```

**Dual-GPU advantage:** phi4 (9GB) fits on GPU 0 while the writer model (~13-14GB) runs on GPU 1. This eliminates the model-swapping bottleneck for the planner/writer pipeline — both can stay loaded simultaneously. The embedder is tiny and fits alongside either.

**Implementation:**
- [ ] Create `app/services/planner_service.py`:
  - `plan_beat(context, user_prompt, world_bible) -> StoryBeat`
  - StoryBeat: structured output with `setting`, `characters_present`, `key_events`, `emotional_tone`, `continuity_notes`
  - Uses phi4 model with structured JSON output prompt
  - Validates character names against world bible (flags unknown characters)
- [ ] Create `app/services/writer_service.py`:
  - `write_scene(beat, context, content_mode) -> str`
  - `write_scene_stream(beat, context, content_mode) -> AsyncIterator[str]`
  - Selects model based on content_mode (Dark Champion vs Gemma 3 27B)
  - Incorporates beat structure into system prompt
- [ ] Update `StoryGenerationService` as orchestrator:
  - Calls ContextService → PlannerService → WriterService → Embedder
  - Stores beat in node metadata JSONB
  - Streaming still works (writer streams, planner is non-streaming)

### 3.2 VRAM Management & GPU Assignment

With dual RTX 3090s (24GB each), models can be pinned to specific GPUs to avoid swapping:

**Optimal GPU layout:**
| GPU | Model | VRAM Used | VRAM Free |
|-----|-------|-----------|-----------|
| GPU 0 | phi4 (planner) | ~9GB | ~15GB |
| GPU 1 | Dark Champion 8X4B V2 or Gemma 3 27B QAT (writer) | ~13-14GB | ~10GB |
| Either | nomic-embed-text (embedder) | ~0.3GB | — |

**Note:** When ComfyUI is generating images, it needs GPU VRAM too. The model manager should unload writer models before illustration generation, or pin ComfyUI to a specific GPU.

**Implementation:**
- [ ] Create `app/services/model_manager.py`:
  - Configure GPU assignment per model via Ollama's `CUDA_VISIBLE_DEVICES` or model-level GPU pinning
  - `ensure_loaded(model_name)` — verify model is loaded, load if not
  - `unload(model_name)` — set `keep_alive=0` to free VRAM
  - Track which models are loaded and on which GPU
- [ ] Add asyncio.Semaphore to prevent concurrent generation requests from colliding
- [ ] Config option to disable MoA and use single-model mode (fallback to Phase 1 behavior)
- [ ] Config option for single-GPU mode (sequential model swapping for users without dual GPUs)
- [ ] Health check: verify both GPUs are available, report VRAM status

### 3.3 Consistency Checking

The planner can also check for continuity errors:

- [ ] Planner receives world bible entities in context
- [ ] Planner output includes `continuity_warnings` (e.g., "Character X was established as left-handed but prompt implies right-handed")
- [ ] Warnings stored in node metadata, surfaced in UI/CLI
- [ ] Optional: planner can reject/modify prompts that contradict established facts

**Deliverable:** Two-pass generation produces more coherent, structurally sound stories. Planning visible in node metadata.

---

## Stage 4: Image Consistency (IP-Adapter)

**Why:** Currently, entity reference images exist but aren't used when generating scene illustrations. Characters look different every time. IP-Adapter lets ComfyUI use reference images as style/identity guides.

### 4.1 IP-Adapter Workflow

Build a ComfyUI workflow that takes a text prompt + reference image(s) and generates a consistent illustration:

- [ ] Install IP-Adapter ComfyUI custom nodes (if not already installed)
- [ ] Create `workflows/scene_ipadapter.json` — txt2img with IP-Adapter node:
  - Input: scene description prompt, character reference image(s)
  - IP-Adapter weight: ~0.6-0.8 (balance identity vs. scene freedom)
  - Same base checkpoint (realvisxlV40 SDXL Lightning)
- [ ] Create `workflows/entity_reference.json` — dedicated entity portrait workflow (no IP-Adapter, just prompt-to-image for initial reference)

### 4.2 Scene Illustration Service

Build automatic scene illustration that uses entity references:

- [ ] Create `app/services/illustration_service.py`:
  - `illustrate_scene(session, node, story) -> str` (returns image path)
  - Extracts character/location names from scene text (reuse entity detection from AssetService or use planner beat's `characters_present`)
  - Looks up reference images for detected entities
  - Builds ComfyUI prompt: scene description + IP-Adapter reference images
  - Falls back to basic txt2img if no references available
- [ ] Integrate with `auto_illustrate` story setting (Stage 1.2)
- [ ] Add scene illustration endpoint: `POST /api/nodes/{id}/illustrate`
- [ ] Store illustration path on node (add `illustration_path` column or use metadata JSONB)

### 4.3 Frontend Integration

- [ ] Display scene illustrations inline with story text
- [ ] "Illustrate" button on each scene (manual trigger)
- [ ] Auto-illustrate indicator in story settings
- [ ] CLI: `/illustrate` command for current scene

**Deliverable:** Characters maintain visual identity across scene illustrations. Auto-illustrate option generates images as you write.

---

## Stage 5: Test Suite & Polish

### 5.1 Automated Tests

- [ ] Set up pytest + pytest-asyncio in `backend/tests/`
- [ ] Add test dependencies to requirements.txt (pytest, pytest-asyncio, httpx)
- [ ] Unit tests for ContextService (mock database, verify context assembly)
- [ ] Unit tests for PlannerService (mock Ollama, verify beat structure)
- [ ] Unit tests for WriterService (mock Ollama, verify model selection by content_mode)
- [ ] Integration tests for API endpoints (TestClient, in-memory or test database)
- [ ] Test content mode switching (verify correct model is called)
- [ ] Test RAG context retrieval (verify semantic search returns relevant nodes)

### 5.2 Incremental UI Improvements

No React rewrite — improve the existing vanilla JS frontend:

- [ ] Story settings panel (content mode toggle, auto-illustrate toggle, context depth)
- [ ] Inline scene illustrations (display below scene text)
- [ ] Planner beat display (expandable section showing story beat before scene)
- [ ] Continuity warnings display
- [ ] Better error messages for model-not-found (e.g., mistral:7b not pulled)
- [ ] Loading states for multi-step generation (planning... → writing... → illustrating...)

### 5.3 CLI Improvements

- [ ] `/mode [safe|unrestricted]` — toggle content mode
- [ ] `/illustrate` — generate illustration for current scene
- [ ] `/beat` — show planner beat for current scene
- [ ] `/context` — show what context was assembled for current scene (debug)
- [ ] Update `/status` to show content mode and auto-illustrate setting

**Deliverable:** Test coverage for new services, polished UI for Phase 2 features.

---

## Development Order

**Stage 1** (Content Mode) — foundation for all subsequent work, small scope
**Stage 2** (RAG) — backend-only, high impact, independent of other stages
**Stage 3** (MoA) — builds on RAG context, adds planner/writer split
**Stage 4** (IP-Adapter) — builds on entity system, benefits from MoA beats for character detection
**Stage 5** (Tests & Polish) — covers all new services, UI catches up

Stages 1-2 can proceed without ComfyUI. Stages 3-4 benefit from each other but are independently valuable.

---

## New Model Requirements

### Already Available
| Model | Size | Role |
|-------|------|------|
| `dolphin-mistral:7b` | 4.1GB (Q4_0) | Fallback unrestricted writer |
| `phi4:latest` | 9.1GB (Q4_K_M) | Planner agent |
| `nomic-embed-text:latest` | 274MB (F16) | Embeddings |
| `gemma2:9b` | 5.4GB (Q4_0) | Visualizer scene descriptions |

### Needs Pull (Stage 1)
| Model | Ollama Name | Size (est.) | Role |
|-------|-------------|-------------|------|
| Dark Champion 8X4B V2 | `dfebrero/DavidAU-Llama-3.2-8X4B-MOE-V2-Dark-Champion-Instruct-uncensored-abliterated` | ~13GB (Q4) | Primary unrestricted writer |
| Gemma 3 27B QAT | `gemma3:27b-it-qat` | ~14GB (int4) | Primary safe mode writer |
| Hermes 3 8B | `hermes3:8b` | ~5GB (Q4) | Fallback safe mode writer |

```bash
# Primary writer models
ollama pull gemma3:27b-it-qat
ollama pull hermes3:8b

# Dark Champion (community model — verify exact tag before pulling)
ollama pull dfebrero/DavidAU-Llama-3.2-8X4B-MOE-V2-Dark-Champion-Instruct-uncensored-abliterated
```

### Model Selection Reference (Brainstorming Report 3.1.2)

**Unrestricted / Creative Mode:**
- **Midnight Miqu 70B** ("Gold Standard Novelist") — captures "Sophosympatheia" (believable emotional resonance), understands subtext and sarcasm, native unrestricted. **Skipped: ~42GB weights, impractical on dual 3090s.**
- **Dark Champion 8X4B V2** ("Grindhouse Director") — abliterated (refusal vectors mathematically removed), 128k context window, MoE for fast inference. **Selected: fits on single GPU.**

**Safe / Balanced Mode:**
- **Hermes 3 8B** ("Balanced") — high steerability, coherent prose without heavy moralizing. Good general fiction. **Selected as fallback.**
- **Gemma 3 27B QAT** ("International Poet") — literary flair, excellent multilingual, heavily aligned (will refuse mature themes). **Selected as primary safe writer.**

---

## Database Changes Summary

New/modified columns (single migration):
- `stories.content_mode` — VARCHAR, default `'unrestricted'`
- `stories.auto_illustrate` — BOOLEAN, default FALSE
- `stories.context_depth` — INTEGER, default 5

Optional (Stage 4):
- `nodes.illustration_path` — VARCHAR, nullable

---

## Phase 2 Non-Goals (Deferred to Phase 3)

- ❌ React/TypeScript frontend rewrite
- ❌ PuLID advanced face consistency
- ❌ LoRA training pipeline for characters
- ❌ Audio narration / TTS
- ❌ EPUB export
- ❌ Multi-user support
- ❌ Visual DAG editor (React Flow)

---

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| VRAM exhaustion (writer + ComfyUI) | OOM crash | Model manager unloads writer before image gen; semaphore prevents concurrent use |
| Dark Champion community model unavailable/broken | No unrestricted writer | Fall back to dolphin-mistral:7b (already pulled, proven) |
| Gemma 3 27B moralizes too aggressively | Safe mode too restrictive | Fall back to Hermes 3 8B; tune system prompts |
| RAG returns irrelevant context | Confused AI output | Tune similarity threshold, limit to top-K results |
| IP-Adapter not installed in ComfyUI | Stage 4 blocked | Check early, install custom nodes before Stage 4 |
| New models not pulled | Content mode broken | Pull during Stage 1 setup, add model health check to /health endpoint |
| Planner produces bad JSON | Writer gets garbage | Validate planner output, fallback to single-model if parse fails |
| Dual-GPU Ollama layer splitting issues | Model won't load | Pin models to specific GPUs; test layer distribution |
