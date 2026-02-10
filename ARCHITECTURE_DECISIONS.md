# Architecture Decisions

This document explains **why** we made specific technical choices for StoryForge 2.0. Each decision includes the context, options considered, and rationale.

---

## AD-001: Directed Acyclic Graph (DAG) for Story Structure

**Date:** 2026-02-05  
**Status:** Accepted  
**Context:**

Traditional word processors store stories as linear text. Users who want to explore alternative plot paths must manually duplicate content or lose their original work.

**Options Considered:**

1. **Linear Array** - Simple list of paragraphs
   - ✅ Simple to implement
   - ❌ No branching support
   - ❌ Destructive edits

2. **Full Version Control (Git-like)** - Complete diff-based history
   - ✅ Powerful versioning
   - ❌ Overly complex for storytelling
   - ❌ Hard to visualize branches

3. **Directed Acyclic Graph (DAG)** - Tree structure with parent pointers
   - ✅ Natural branching model
   - ✅ Non-destructive exploration
   - ✅ Efficient traversal with recursive CTEs
   - ✅ Clear visualization

**Decision:** Implement DAG using adjacency list (parent_id self-reference)

**Rationale:**
- Stories naturally branch (Chapter 3 could go two different ways)
- Users want to explore "What if?" without losing work
- PostgreSQL recursive CTEs make tree traversal efficient
- Adjacency list balances read/write performance

**Consequences:**
- Slightly more complex than linear storage
- UI must support branch navigation
- Export must choose which branch to follow

---

## AD-002: Adjacency List vs. Materialized Path (ltree)

**Date:** 2026-02-05  
**Status:** Accepted  
**Context:**

PostgreSQL supports multiple approaches to hierarchical data. We need efficient tree queries.

**Options Considered:**

1. **Adjacency List** - Each node has parent_id
   - ✅ Simple writes (just insert with parent_id)
   - ✅ Easy to move subtrees
   - ✅ Natural ORM support
   - ⚠️ Requires recursive CTE for full paths

2. **Materialized Path (ltree)** - Store full path as "1.2.3"
   - ✅ Very fast descendant queries
   - ❌ Complex updates when moving subtrees
   - ❌ Path length limits
   - ❌ Less intuitive for editing environment

3. **Closure Table** - Separate table for all ancestor/descendant pairs
   - ✅ Fast queries
   - ❌ Complex writes
   - ❌ More storage overhead

**Decision:** Use Adjacency List

**Rationale:**
- StoryForge is write-heavy (users constantly adding/editing nodes)
- Moving branches should be simple
- Recursive CTEs in PostgreSQL are fast enough for typical story depth (<100 nodes)
- We're not building a million-node knowledge graph

**Consequences:**
- Must use WITH RECURSIVE for path queries
- Index on parent_id is critical
- Tree depth should be monitored (but won't be a practical issue)

---

## AD-003: Single Model (Phase 1) vs. Multi-Agent MoA (Phase 2)

**Date:** 2026-02-05  
**Status:** Accepted  
**Context:**

The SDD proposes a sophisticated Mixture of Agents approach with specialized models for planning, writing, and visualization. However, this adds significant complexity.

**Options Considered:**

1. **Multi-Agent from Day 1**
   - ✅ Matches SDD vision
   - ❌ Complex orchestration
   - ❌ Model swapping logic required
   - ❌ VRAM management overhead
   - ❌ Delays MVP

2. **Single Model for MVP**
   - ✅ Simple to implement
   - ✅ Faster MVP delivery
   - ✅ dolphin-mistral is uncensored and creative
   - ⚠️ Less sophisticated output

3. **Hybrid: Single Writer + Separate Visualizer**
   - ⚠️ Middle complexity
   - ✅ Good text quality
   - ⚠️ Still need some orchestration

**Decision:** Use single model (dolphin-mistral:7b) for Phase 1, architect for MoA in Phase 2

**Rationale:**
- MVP should prove the concept: DAG + Asset Catalog + Illustrations
- dolphin-mistral is sufficient for creative writing
- Adding MoA before validating core mechanics is premature optimization
- Design the service layer to support MoA later (but don't implement yet)

**Implementation:**
- StoryGenerationService has single method in Phase 1
- Phase 2 will add PlannerAgent, WriterAgent classes
- Service interface remains the same (API doesn't change)

**Consequences:**
- Phase 1 stories won't have logical planning layer
- Users get faster response (no model swapping overhead)
- Easier debugging during MVP development

---

## AD-004: PostgreSQL + pgvector vs. Specialized Vector DB

**Date:** 2026-02-05  
**Status:** Accepted  
**Context:**

RAG requires vector similarity search. Several options exist for storing embeddings.

**Options Considered:**

1. **Separate Vector DB (Chroma, Qdrant, Weaviate)**
   - ✅ Optimized for vector search
   - ❌ Additional service to manage
   - ❌ Data synchronization complexity
   - ❌ Two databases to maintain

2. **PostgreSQL + pgvector Extension**
   - ✅ Single database for all data
   - ✅ Transactional consistency
   - ✅ No synchronization issues
   - ✅ HNSW index is fast enough for <10k documents
   - ⚠️ Slightly slower than specialized DBs at massive scale

**Decision:** Use PostgreSQL + pgvector

**Rationale:**
- StoryForge is not Google-scale (typical story = <1000 nodes)
- Keeping story content and embeddings in one database simplifies architecture
- ACID transactions ensure consistency
- One less service to deploy/monitor
- pgvector with HNSW is fast enough for our use case

**Consequences:**
- Must install pgvector extension
- Vector column adds storage overhead (~3KB per 768-dim embedding)
- If scaling to millions of stories, may need to revisit

---

## AD-005: FastAPI vs. Flask vs. Django

**Date:** 2026-02-05  
**Status:** Accepted  
**Context:**

We need a Python web framework for the backend API.

**Options Considered:**

1. **Flask**
   - ✅ Simple, minimal
   - ❌ No native async support
   - ❌ Manual OpenAPI docs
   - ❌ WebSocket support is awkward

2. **Django + Django REST Framework**
   - ✅ Batteries included (admin, ORM)
   - ❌ Heavyweight for API-only backend
   - ❌ Poor WebSocket story
   - ❌ Opinionated structure

3. **FastAPI**
   - ✅ Native async/await
   - ✅ Automatic OpenAPI/Swagger docs
   - ✅ Excellent WebSocket support
   - ✅ Pydantic validation
   - ✅ Modern Python 3.11+ features
   - ⚠️ Less mature than Flask/Django

**Decision:** FastAPI

**Rationale:**
- LLM generation is long-running (async is essential)
- WebSocket streaming provides better UX than polling
- Auto-generated API docs save time
- Pydantic models match SQLAlchemy well
- Strong Python AI/ML ecosystem integration

**Consequences:**
- Must use async/await throughout codebase
- Learning curve if unfamiliar with async Python
- No built-in admin interface (acceptable for single-user app)

---

## AD-006: Ollama vs. Direct Model Loading

**Date:** 2026-02-05  
**Status:** Accepted  
**Context:**

We need to run local LLMs. Options include loading models directly with transformers/llama.cpp or using an inference server.

**Options Considered:**

1. **Direct Loading (transformers / llama.cpp)**
   - ✅ Maximum control
   - ❌ Must manage model loading/unloading
   - ❌ No API abstraction
   - ❌ Complex CUDA memory management

2. **Ollama**
   - ✅ Simple API (OpenAI-compatible)
   - ✅ Automatic model management
   - ✅ GGUF quantization built-in
   - ✅ keep_alive parameter for VRAM control
   - ✅ Already running on server
   - ⚠️ Slightly higher memory overhead

3. **vLLM**
   - ✅ Excellent batching/throughput
   - ⚠️ More complex setup
   - ⚠️ Overkill for single-user app

**Decision:** Use Ollama

**Rationale:**
- Already installed and working on server
- Simple HTTP API reduces complexity
- Model management is handled (no manual CUDA code)
- keep_alive=0 allows model swapping in Phase 2
- Performance is sufficient for single user

**Consequences:**
- Dependent on Ollama service availability
- Must use GGUF model format
- Slightly higher latency than native transformers (acceptable tradeoff)

---

## AD-007: ComfyUI vs. Automatic1111 vs. InvokeAI

**Date:** 2026-02-05  
**Status:** Accepted  
**Context:**

We need image generation with control over workflows (for IP-Adapter, PuLID, etc.).

**Options Considered:**

1. **Automatic1111 (WebUI)**
   - ✅ Popular, mature
   - ❌ Less flexible workflow system
   - ❌ Harder to programmatically control
   - ❌ SDXL-focused (FLUX support is secondary)

2. **InvokeAI**
   - ✅ Node-based workflows
   - ⚠️ Smaller community
   - ⚠️ Less LoRA/extension support

3. **ComfyUI**
   - ✅ Extremely flexible node graph system
   - ✅ JSON workflow definitions (perfect for API)
   - ✅ Best FLUX support
   - ✅ Easy to add IP-Adapter/PuLID nodes
   - ✅ Already running on server on :8188
   - ⚠️ Steeper learning curve

**Decision:** Use ComfyUI

**Rationale:**
- Already installed and working
- JSON workflows can be version-controlled
- Easy to build character consistency pipeline
- FLUX.1 [dev] support is first-class
- Programmatic control via API is excellent

**Consequences:**
- Must learn ComfyUI workflow JSON structure
- Need to manage custom nodes for PuLID/Redux
- Workflow debugging requires understanding node graph

---

## AD-008: Streaming vs. Polling for LLM Responses

**Date:** 2026-02-05  
**Status:** Accepted  
**Context:**

LLM generation can take 30+ seconds. Users need feedback that something is happening.

**Options Considered:**

1. **Polling** - Client polls /api/status endpoint every second
   - ✅ Simple implementation
   - ❌ Wastes bandwidth
   - ❌ Higher latency (up to 1 second delay)
   - ❌ Server must store intermediate state

2. **WebSocket Streaming** - Stream tokens as generated
   - ✅ Real-time feedback
   - ✅ Efficient bandwidth usage
   - ✅ Better UX (tokens appear immediately)
   - ⚠️ More complex (requires WebSocket handling)

3. **Server-Sent Events (SSE)** - One-way streaming
   - ✅ Simpler than WebSocket
   - ✅ Real-time
   - ❌ HTTP/2 only
   - ❌ Less browser support for error handling

**Decision:** WebSocket streaming

**Rationale:**
- FastAPI has excellent WebSocket support
- Ollama supports streaming responses
- User sees tokens appear in real-time (feels faster)
- Can send control messages (pause, cancel generation)
- Modern browsers support WebSockets well

**Consequences:**
- Must implement WebSocket connection management
- Need to handle disconnections gracefully
- CLI interface will need WebSocket client

---

## AD-009: CLI vs. Web UI for Phase 1

**Date:** 2026-02-05  
**Status:** Accepted  
**Context:**

MVP needs some interface for user interaction. Full React UI is time-consuming.

**Options Considered:**

1. **Full React Web UI**
   - ✅ Professional appearance
   - ✅ Easy to add features later
   - ❌ Significant development time
   - ❌ Delays backend validation

2. **CLI (Command-Line Interface)**
   - ✅ Extremely fast to implement
   - ✅ Forces focus on backend logic
   - ✅ Easy to test API manually
   - ❌ Less user-friendly
   - ❌ No visual DAG representation

3. **Minimal Web UI (Single page, simple forms)**
   - ⚠️ Compromise
   - ✅ Better UX than CLI
   - ⚠️ Still takes development time

**Decision:** Start with CLI, add minimal web UI in Phase 1.5 if time allows

**Rationale:**
- Backend API is the critical path
- CLI proves the system works end-to-end
- Web UI can be added without changing backend
- Vince (primary user) is comfortable with CLI
- Focus on functionality over aesthetics for MVP

**Implementation:**
```python
# cli.py - Simple interactive loop
while True:
    user_input = input("> ")
    response = api_client.generate(user_input)
    print(response)
```

**Consequences:**
- Phase 1 demo is less visually impressive
- Export functionality is critical (markdown output)
- Web UI becomes Phase 1.5 or Phase 2 priority

---

## AD-010: Asset Detection Strategy

**Date:** 2026-02-05  
**Status:** Accepted  
**Context:**

The system must identify when characters/locations/props are introduced in the narrative.

**Options Considered:**

1. **Manual Tagging** - User explicitly creates entities
   - ✅ 100% accurate
   - ❌ Interrupts writing flow
   - ❌ User burden

2. **LLM Extraction** - Ask LLM "extract characters from this text"
   - ✅ Automatic
   - ✅ Understands context
   - ⚠️ Costs tokens
   - ⚠️ May miss entities

3. **NER (Named Entity Recognition)** - SpaCy/Stanza pipeline
   - ✅ Fast, local
   - ❌ Generic (misses fictional names)
   - ❌ Separate service to run

4. **Hybrid: Manual + LLM-Assisted** - LLM suggests, user confirms
   - ✅ Best accuracy
   - ✅ Low friction
   - ⚠️ Requires UI flow

**Decision:** Phase 1: Manual creation. Phase 2: Add LLM extraction with user confirmation

**Rationale:**
- MVP should focus on core mechanics (DAG + images)
- Manual entity creation validates the concept
- Users will know when they introduce important characters
- Automatic extraction can be added later without changing database

**Implementation:**
- API endpoint: POST /api/stories/{id}/entities
- User explicitly names character, provides description
- System generates reference image
- Phase 2: Add auto-detection endpoint that suggests entities

**Consequences:**
- Users must remember to create entities
- More friction than automatic detection
- Good enough for Phase 1 validation

---

## AD-011: Image Generation Trigger

**Date:** 2026-02-05  
**Status:** Accepted  
**Context:**

When should illustrations be generated? Every scene? On-demand?

**Options Considered:**

1. **Automatic for Every Scene**
   - ✅ Fully illustrated story
   - ❌ Slow (adds 20-30 seconds per scene)
   - ❌ VRAM contention if generating while writing

2. **On-Demand Button**
   - ✅ User control
   - ✅ Faster writing flow
   - ❌ User might forget to generate
   - ⚠️ Inconsistent illustrated stories

3. **Configurable Flag per Story** - "auto-illustrate" setting
   - ✅ User choice
   - ✅ Can be changed mid-story
   - ✅ Best of both worlds

**Decision:** Configurable "auto_illustrate" flag on story settings

**Rationale:**
- Some users want fully illustrated stories
- Others want to write fast, add images later
- Flag in database allows per-story configuration
- API supports both modes without code changes

**Implementation:**
```python
# stories table
auto_illustrate BOOLEAN DEFAULT FALSE

# In generation service
if story.auto_illustrate:
    await generate_illustration(node)
```

**Consequences:**
- Must add UI control for toggling flag
- Export should handle stories with/without images
- Users can experiment to find preferred workflow

---

## AD-012: Export Format

**Date:** 2026-02-05  
**Status:** Accepted  
**Context:**

Users want to save completed stories in readable format.

**Options Considered:**

1. **Plain Text (.txt)**
   - ✅ Universal compatibility
   - ❌ No images
   - ❌ No formatting

2. **HTML**
   - ✅ Images + formatting
   - ✅ Self-contained (base64 images)
   - ⚠️ Large file size

3. **Markdown + Image Files**
   - ✅ Human-readable
   - ✅ Images as references
   - ✅ Can be converted to other formats
   - ⚠️ Need to package images

4. **EPUB (eBook)**
   - ✅ Professional format
   - ✅ Images supported
   - ❌ More complex to generate
   - ❌ Phase 2 feature

**Decision:** Phase 1: Markdown with image references. Phase 2: Add EPUB

**Rationale:**
- Markdown is simple to generate
- Images copied to export directory alongside .md file
- Users can convert markdown to other formats if needed
- Proves export functionality works
- EPUB can be added later with libraries like ebooklib

**Implementation:**
```python
# Export creates:
exports/story_uuid/
  ├── story.md
  └── images/
      ├── character_001.png
      └── scene_001.png
```

**Consequences:**
- Export is a folder, not a single file
- Users can zip the folder for sharing
- Images are copied (not moved) from static/

---

## Patterns to Follow

As development continues, add new decisions to this document with:
- **Date** - When decided
- **Context** - What problem we're solving
- **Options** - What we considered (with pros/cons)
- **Decision** - What we chose
- **Rationale** - Why we chose it
- **Consequences** - What this means going forward

This creates a paper trail for future reference and onboarding.
