# StoryForge 2.0 - Project Charter

## Vision Statement

Create a local-first, AI-powered interactive storytelling application that enables open-ended creative writing with dynamic, visually consistent illustrations. The system maintains an "Asset Catalog" ensuring characters, locations, and props remain consistent across the narrative, and supports branching storylines through a version-controlled narrative structure.

## Core Principles

1. **Privacy First** - All AI processing happens locally on self-hosted infrastructure
2. **Unrestricted Creativity** - No API censorship; users control content boundaries
3. **Visual Consistency** - Characters look the same across all generated illustrations
4. **Non-Destructive Editing** - Explore alternative story paths without losing work
5. **Export Ready** - Generate complete documents with embedded images

## User Experience Goals

### The Writing Loop
1. User types narrative prompt or action (open-ended, not multiple choice)
2. AI generates the next scene/paragraph
3. If enabled, system automatically generates illustration
4. Continue writing or branch to explore alternatives
5. Export complete story as document with embedded images

### The Asset System
- System automatically detects new characters, locations, and props
- Generates reference images for each entity
- Reuses these references to maintain visual consistency
- Users can manually update/evolve entity appearances (versioning)

## Technical Goals

### Phase 1: Foundation (MVP)
- [ ] Database with DAG structure for branching narratives
- [ ] Single LLM integration (dolphin-mistral) for creative writing
- [ ] Asset catalog (Characters, Locations, Props)
- [ ] Basic illustration generation (FLUX + reference matching)
- [ ] Simple API + minimal interface
- [ ] Export to Markdown with images

### Phase 2: Intelligence (MoA)
- [ ] Multi-agent orchestration (Planner, Writer, Visualizer)
- [ ] Dynamic model swapping based on task
- [ ] Enhanced visual consistency (PuLID + Redux)
- [ ] RAG for long-form narrative memory
- [ ] World Bible with semantic search

### Phase 3: Polish
- [ ] Rich web UI with branching visualization
- [ ] LoRA training pipeline for recurring characters
- [ ] Audio narration generation
- [ ] Advanced export formats (EPUB, interactive HTML)

## Success Metrics

**MVP is successful when:**
- User can write a multi-chapter story with AI assistance
- Story branches can be created and navigated
- Characters maintain visual consistency across 5+ illustrations
- Complete story exports as readable document with embedded images

**System is production-ready when:**
- Handles stories with 50+ nodes (chapters/scenes)
- Generates consistent illustrations in <30 seconds
- Supports simultaneous planning and writing (model swapping)
- Exports professional-quality formatted output

## Non-Goals (Out of Scope)

- Multi-user/collaborative editing
- Cloud deployment or SaaS offering
- Mobile applications
- Real-time multiplayer
- Blockchain/NFT integration
- Video generation (images only)

## Architecture Philosophy

**Practical over Perfect:**
We favor working code over architectural purity. Start simple, add complexity only when needed.

**Modular Monolith:**
Single deployable backend, but organized into clear service boundaries (database, inference, orchestration).

**Async-First:**
Long-running AI generation requires async patterns (WebSockets, background tasks).

**Hardware-Aware:**
Respect VRAM constraints. Load/unload models strategically.

## Key Stakeholder

**Primary User:** Vince
- Senior Systems Architect & DevOps Engineer
- Runs Proxmox infrastructure with GPU passthrough
- Values systematic approaches and comprehensive documentation
- Prefers self-hosted solutions
- Experienced with AI/ML deployment

## Project Constraints

**Hardware:**
- Debian LXC on Proxmox (debian-storybook-lxc)
- Dual NVIDIA GPUs (passthrough enabled)
- Models stored on bind-mounted HDD (/mnt/)
- PostgreSQL database (local)

**Software:**
- Python backend (FastAPI)
- Ollama for LLM inference (already running)
- ComfyUI for image generation (already running on :8188)
- PostgreSQL + pgvector for data and embeddings

**Operational:**
- Single developer (Vince)
- Development happens via Claude Code on server
- Must maintain clear documentation for future reference
- Iterative development with frequent validation

## Risk Mitigation

| Risk | Impact | Mitigation |
|------|--------|-----------|
| VRAM exhaustion | System crash | Implement model leasing semaphore |
| Inconsistent characters | Poor user experience | Use IP-Adapter/PuLID from start |
| Complex UI scope creep | Delayed MVP | Start with CLI/minimal UI |
| Database schema changes | Data migration pain | Use Alembic from day 1 |
| Lost context in long stories | Narrative drift | Implement RAG early in Phase 2 |

## Timeline Philosophy

We don't commit to dates. We commit to:
1. **Always having a working system** (even if minimal)
2. **Completing phases before moving forward**
3. **Documenting blockers immediately**
4. **Celebrating small wins**

Progress is tracked in PROJECT_STATUS.md, updated after every significant change.

## Definition of Done

A feature is "done" when:
- [ ] Code is written and tested
- [ ] Services integrate successfully
- [ ] Documentation is updated
- [ ] PROJECT_STATUS.md reflects completion
- [ ] Next steps are identified

## Communication

All technical decisions are documented in ARCHITECTURE_DECISIONS.md with rationale. If a choice is made, explain why.

---

**Let's build a tool that makes storytelling magical.** ✨
