# Claude Code Instructions for StoryForge 2.0

## Project Overview
You are working on **StoryForge 2.0**, an AI-powered interactive storytelling application with dynamic illustration generation. This is a greenfield implementation running on a Debian LXC container with GPU access.

## Infrastructure Context

**Server Environment:**
- Host: debian-storybook-lxc (192.168.1.71)
- Project Path: `/home/vince/storyforge/`
- OS: Debian 12 (LXC container on Proxmox)
- GPU: Dual NVIDIA GPUs (passthrough configured)

**Available Services:**
- **Ollama** (LLM inference): http://localhost:11434
- **ComfyUI** (Image generation): http://localhost:8188
- **PostgreSQL** (Database): localhost:5432

**Available Models:**
- `phi4:latest` (9.1 GB) - Logical Planner
- `dolphin-mistral:7b` (4.1 GB) - Creative Writer
- `gemma2:9b` (5.4 GB) - Visualizer with vision
- `nomic-embed-text:latest` (274 MB) - Embeddings for RAG

**Storage:**
- Project files: `/home/vince/storyforge/`
- Model storage: `/mnt/` (bind-mounted from host)

## Development Philosophy

This project uses a **subagent system** where specialized agents handle domain-specific work, while the main Claude instance focuses on implementation and coordination.

### Subagents (Separate Context Windows)

These are Claude Code subagents created via `/agents`. Each has its own context window, system prompt, and tool access. Delegate to them for specialized work:

1. **Architect** — System design and technical decisions
   - Design reviews, component planning, API contracts
   - Documents decisions in ARCHITECTURE_DECISIONS.md
   - Read-only tools (analyzes, doesn't implement)
   - Reference: ROLE_ARCHITECT.md for detailed guidelines

2. **Database Specialist** — Data layer expert
   - Schema design, migration review, query optimization
   - pgvector embedding strategy, recursive CTE queries
   - Full tool access (runs migrations, tests queries)
   - Reference: ROLE_DATABASE.md for detailed guidelines

3. **Integration Specialist** — Service connections
   - Ollama and ComfyUI client code, error handling
   - Multi-service orchestration, VRAM management
   - Full tool access (tests against live services)
   - Reference: ROLE_INTEGRATION.md for detailed guidelines

4. **Code Reviewer** — Quality gate before commits
   - Code quality, security, pattern consistency
   - Read-only tools (reviews, doesn't modify)
   - Runs on sonnet for speed

### Main Instance Responsibilities

The main Claude instance handles directly (no subagent needed):

- **Implementation** — Writing backend/frontend code (this is the primary job)
- **Project Management** — Updating PROJECT_STATUS.md after tasks
- **Session Management** — Handoff documentation at end of sessions

Reference ROLE_IMPLEMENTATION.md for coding standards and patterns.

### When to Delegate vs. Handle Directly

**Delegate to a subagent when:**
- Designing a new feature or making architectural decisions (Architect)
- Creating or reviewing database migrations (Database Specialist)
- Building or debugging service integrations (Integration Specialist)
- Reviewing code before a commit (Code Reviewer)

**Handle directly when:**
- Writing implementation code (models, services, API endpoints)
- Updating PROJECT_STATUS.md
- Simple bug fixes or small changes
- Running tests

## How to Work

**Before starting ANY task:**
1. Read PROJECT_STATUS.md to understand current state
2. Identify if specialized subagent work is needed
3. Reference TECH_STACK.md for technical constraints
4. Check PHASE_1_ROADMAP.md for priorities

**After completing ANY task:**
1. Update PROJECT_STATUS.md with:
   - What was completed
   - Any issues encountered
   - Next recommended steps
2. Update relevant documentation

## Key Project Documents

- **PROJECT_CHARTER.md** - Vision and goals (read first)
- **PHASE_1_ROADMAP.md** - Current implementation plan
- **PROJECT_STATUS.md** - Living status document (update frequently)
- **TECH_STACK.md** - Locked technical decisions
- **ARCHITECTURE_DECISIONS.md** - Why we chose what we chose
- **SETUP_INSTRUCTIONS.md** - Initial setup steps
- **ROLE_*.md** - Detailed guidelines for each specialization

## Communication Protocol

When Vince provides a task:
1. Assess whether subagent delegation is needed
2. State what documents you're referencing
3. Outline your approach before implementing
4. Execute the work (delegating specialized analysis as needed)
5. Update PROJECT_STATUS.md
6. Summarize what was done and suggest next steps

Example (direct implementation):
```
Referencing: TECH_STACK.md, PHASE_1_ROADMAP.md

Approach:
- Implement StoryGenerationService per roadmap Stage 3.3
- Uses OllamaService for text generation
- Add context retrieval from narrative DAG

[... implementation happens ...]

Updated: PROJECT_STATUS.md
Completed: Story generation service with context retrieval
Next: REST API endpoints for story and node CRUD
```

Example (with subagent delegation):
```
This requires schema changes — delegating to Database Specialist
for migration review before applying.

[... Database Specialist reviews in its own context ...]

Migration approved. Applying and continuing with implementation.
```

## Important Constraints

- **No Windows Claude dependency** - All decisions and implementation happen here
- **Use existing infrastructure** - Ollama and ComfyUI are already running
- **Start simple, iterate** - MVP first, sophistication later
- **Document everything** - Future you will thank present you
- **Test as you go** - Don't build huge features without validation

## Success Criteria

You're doing well when:
- PROJECT_STATUS.md is always current
- Each commit moves toward Phase 1 goals
- Code is clean and documented
- Services integrate cleanly
- The system works end-to-end (even if simple)
- Subagents are used for specialized analysis, not routine work

You need to course-correct when:
- Status docs are stale
- You're blocked for >1 hour without documenting it
- You're building features not in current phase
- Tests are failing
- Services can't communicate

## Getting Started

If this is your first session, start with:
1. Read PROJECT_STATUS.md for current state
2. Read PHASE_1_ROADMAP.md for what's next
3. Check that services are running (Ollama, ComfyUI, PostgreSQL)
4. Pick up where the last session left off
