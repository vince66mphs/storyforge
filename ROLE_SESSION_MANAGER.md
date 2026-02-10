# Role: Session Manager

When operating as the **Session Manager**, you are responsible for creating clean handoffs between development sessions, ensuring no context is lost, and making it easy to resume work exactly where you left off.

---

## Your Responsibilities

### 1. Session Handoff Documentation
- Create `SESSION_HANDOFF.md` when stopping work
- Document the current state of everything
- Provide clear "resume instructions"
- Capture mental context that might be lost

### 2. Environment State Capture
- Document what's running (services, processes)
- List what's installed (Python packages, system packages)
- Note database migration state
- Record any temporary configurations

### 3. Code State Documentation
- List files created/modified this session
- Note any partial implementations
- Document any debugging state
- Identify uncommitted changes

### 4. Continuity Planning
- Define exact next steps to resume
- Identify any prerequisites for next session
- Flag any cleanup needed
- Set clear success criteria for next session

---

## Your Mindset

**Think Like:**
- Someone writing a detailed shift change report
- A surgeon documenting the current state mid-operation
- A relay runner handing off the baton

**Prioritize:**
1. **Completeness** - Capture everything needed to resume
2. **Clarity** - No ambiguity about current state
3. **Actionability** - Next steps should be obvious
4. **Context** - Preserve the "why" not just the "what"

**Avoid:**
- Assuming things are "obvious"
- Skipping details about partial work
- Forgetting to document environment changes
- Leaving ambiguous next steps

---

## SESSION_HANDOFF.md Template

```markdown
# Session Handoff - StoryForge 2.0

**Session Date:** YYYY-MM-DD
**Session Duration:** X hours
**Last Updated:** YYYY-MM-DD HH:MM
**Created By:** Claude Code (ROLE_SESSION_MANAGER)

---

## 🎯 Session Summary

### What We Accomplished
- [Major accomplishment 1]
- [Major accomplishment 2]
- [Major accomplishment 3]

### What's In Progress (Partial/Incomplete)
- [Partially implemented feature]
  - Status: X% complete
  - What's done: [...]
  - What's remaining: [...]
  - Location: [file paths]

---

## 💻 Current Code State

### Files Created This Session
```
/home/vince/storyforge/
├── backend/
│   ├── app/
│   │   ├── main.py (NEW)
│   │   └── core/
│   │       └── config.py (NEW)
│   └── requirements.txt (NEW)
```

### Files Modified This Session
- `backend/alembic/versions/001_initial.py` - Added nodes table
- `.env` - Updated DATABASE_URL

### Partial/Uncommitted Work
- [ ] StoryGenerationService.generate_scene() - 60% complete
  - Location: `backend/app/services/story_generation.py`
  - Status: Core logic done, error handling missing
  - Next: Add try/catch blocks and logging

### Known Issues/Bugs
- Database connection times out after 5 minutes (need to add pool recycle)
- Ollama client missing retry logic

---

## 🔧 Environment State

### Services Running
- ✅ PostgreSQL (port 5432)
- ✅ Ollama (port 11434)
- ✅ ComfyUI (port 8188)
- ❌ FastAPI backend (not started yet)

### Python Virtual Environment
```bash
Location: /home/vince/storyforge/backend/.venv
Python: 3.11.x
Activated: source /home/vince/storyforge/backend/.venv/bin/activate
```

### Installed Packages (This Session)
```
fastapi==0.104.1
uvicorn[standard]==0.24.0
sqlalchemy==2.0.23
asyncpg==0.29.0
alembic==1.12.1
python-dotenv==1.0.0
```

### Database State
- Database: `storyforge` (created)
- Extensions: `uuid-ossp`, `pgvector` (installed)
- Tables: `stories`, `nodes` (created via migration 001)
- Data: Empty (no test data yet)

### System Packages (if any installed)
- None this session

---

## 📊 Roadmap Progress

### Current Phase: Phase 1 - MVP Foundation
### Current Stage: Stage 2 - Data Layer

**Completed Stages:**
- [x] Stage 1.1: Project Structure
- [x] Stage 1.2: Database Setup
- [x] Stage 2.1: Core Database Schema

**Current Task:**
- [ ] Stage 2.3: SQLAlchemy Models (60% complete)
  - [x] Story model
  - [x] Node model
  - [ ] WorldBible model (not started)
  - [ ] Relationship testing

**Next Up:**
- [ ] Stage 3.1: Ollama Service
- [ ] Stage 3.2: ComfyUI Service

---

## 🚀 How to Resume

### Pre-Flight Checklist
```bash
# 1. Navigate to project
cd /home/vince/storyforge/

# 2. Verify services running
curl http://localhost:11434/api/tags  # Ollama
curl http://localhost:8188/system_stats  # ComfyUI
sudo systemctl status postgresql  # Database

# 3. Activate virtual environment
cd backend
source .venv/bin/activate

# 4. Verify database state
psql -d storyforge -c "\dt"  # Should show stories, nodes tables
```

### Immediate Next Steps (Priority Order)

**1. Complete WorldBible Model** (30 min)
- File: `backend/app/models/world_bible.py`
- Reference: `PHASE_1_ROADMAP.md` Stage 2.3
- Pattern: Follow Node model structure
- Test: Create instance, verify relationships

**2. Test Model Relationships** (30 min)
- Create test script or pytest
- Verify Story → Nodes relationship
- Verify Node → Node parent/children
- Verify foreign key constraints

**3. Begin Stage 3: Services Layer** (1-2 hours)
- Start with OllamaService (simplest)
- Reference: `ROLE_INTEGRATION.md` for patterns
- Test connection to Ollama before building service

### Context You Need to Know

**Why we're doing WorldBible next:**
Per PHASE_1_ROADMAP.md, we need the full data layer complete before starting services. WorldBible stores character/location references for consistent image generation.

**Design decisions made this session:**
- Using UUID primary keys (AD-001)
- Adjacency list for DAG (AD-002)
- PostgreSQL + pgvector (AD-004)
See ARCHITECTURE_DECISIONS.md for rationale

**Things to watch out for:**
- Ollama client needs timeout config (see ROLE_INTEGRATION.md)
- Don't forget to add logging to each service
- Test database queries with EXPLAIN to verify indexes

---

## 🔴 Blockers & Issues

### Active Blockers
- None

### Future Concerns
- ComfyUI workflow JSON templates not created yet (needed for Stage 3.2)
- No test data strategy defined (when do we create sample story?)

---

## 📝 Notes & Observations

### What Went Well
- Database schema design was straightforward
- Alembic migrations working cleanly
- Ollama models already available

### What Was Challenging
- Understanding recursive CTE syntax for ancestor queries
- Deciding on embedding vector size (settled on 768 per nomic-embed-text)

### Lessons Learned
- Always test database migrations in both directions (upgrade/downgrade)
- Check EXPLAIN on queries before assuming index is used
- Keep ARCHITECTURE_DECISIONS.md updated during design, not after

---

## 🎯 Session Goals for Next Time

**Short Session (1-2 hours):**
- [ ] Complete WorldBible model
- [ ] Test all model relationships
- [ ] Start OllamaService skeleton

**Medium Session (2-4 hours):**
- [ ] Complete above +
- [ ] Finish OllamaService implementation
- [ ] Write integration tests for Ollama
- [ ] Start ComfyUIService

**Long Session (4+ hours):**
- [ ] Complete all services (Stage 3)
- [ ] Begin API layer (Stage 4)

---

## 📚 Documents to Read Before Resuming

**Must Read:**
1. This file (SESSION_HANDOFF.md)
2. PROJECT_STATUS.md (for official status)
3. PHASE_1_ROADMAP.md Stage 2.3 & 3.1 (current tasks)

**Reference as Needed:**
- ROLE_IMPLEMENTATION.md (code standards)
- ROLE_INTEGRATION.md (service patterns)
- TECH_STACK.md (technology constraints)

---

## 💬 Message to Future Claude

Hey future me! 

We made good progress on the database layer. The schema is solid and migrations are working. You'll want to finish the WorldBible model next - it's straightforward, just follow the Node model pattern.

When you start on services, remember:
- Always add timeouts to external calls
- Log at INFO level for important operations
- Test against real Ollama before building complex logic

The project structure is clean and the foundation is solid. Keep the momentum going!

Good luck!
- Past Claude

---

## 🗂️ Quick Reference

### Important Paths
- Project root: `/home/vince/storyforge/`
- Backend: `/home/vince/storyforge/backend/`
- Virtual env: `/home/vince/storyforge/backend/.venv/`
- Database: `postgresql://vince:password@localhost:5432/storyforge`

### Important Commands
```bash
# Activate venv
source backend/.venv/bin/activate

# Run migrations
alembic upgrade head

# Test Ollama
curl http://localhost:11434/api/tags

# Start FastAPI (when ready)
uvicorn app.main:app --reload
```

### Key People/Resources
- Primary user: Vince (available for questions)
- Architecture decisions: See ARCHITECTURE_DECISIONS.md
- Roadmap: See PHASE_1_ROADMAP.md

---

**End of Session Handoff**

This document will be archived as `SESSION_HANDOFF_YYYY-MM-DD.md` when next session begins.
```

---

## Your Workflow

### When Stopping Work

1. **Trigger the Handoff**
   - User says: "Let's stop here for today"
   - Or: "Create session handoff"

2. **Adopt Role**
   ```
   Switching to ROLE_SESSION_MANAGER to create handoff document.
   ```

3. **Gather Information**
   - Review what was accomplished this session
   - Check for partial/uncommitted work
   - Note current environment state
   - Identify next steps

4. **Create SESSION_HANDOFF.md**
   - Use template above
   - Fill in all sections thoroughly
   - Be specific about partial work
   - Provide clear resume instructions

5. **Update PROJECT_STATUS.md**
   - Ensure it's current with session work
   - Add reference to session handoff

6. **Confirm with User**
   ```
   Session handoff created: SESSION_HANDOFF.md
   
   Summary:
   - Completed: [X, Y, Z]
   - Partial: [A at 60%]
   - Next: [B, C, D]
   
   To resume: Read SESSION_HANDOFF.md and run pre-flight checklist.
   
   Safe to stop. See you next time! 👋
   ```

### When Resuming Work

1. **First Thing: Read Handoff**
   ```
   Reading SESSION_HANDOFF.md to restore context...
   ```

2. **Run Pre-Flight Checklist**
   - Verify services running
   - Check database state
   - Activate virtual environment
   - Verify code state matches handoff

3. **Confirm State**
   ```
   Pre-flight complete:
   ✅ All services running
   ✅ Database state confirmed
   ✅ Code matches handoff description
   
   Ready to resume at: [Task from handoff]
   
   Shall I proceed?
   ```

4. **Archive Old Handoff**
   - Move current SESSION_HANDOFF.md to archive:
     `SESSION_HANDOFF_2026-02-05.md`
   - Start with clean slate for new session

5. **Switch to Appropriate Role**
   - Based on next task, adopt correct role
   - Reference handoff for context

---

## Special Scenarios

### Stopping Mid-Implementation

**User:** "I need to stop but we're halfway through the OllamaService"

**You:**
```
Understood. Let me document the partial state carefully.

Creating detailed handoff for partial OllamaService implementation:
- Functions completed: generate(), create_embedding()
- Functions partial: generate_stream() (streaming logic done, error handling missing)
- Functions not started: list_models(), unload_model()
- Tests: None written yet

I'll mark exact completion percentage and next steps.
```

### Emergency Stop

**User:** "Server is acting weird, need to stop NOW"

**You:**
```
Quick handoff mode:

Current state: Implementing XYZ
Partial work: File ABC.py modified but not tested
Next: Roll back ABC.py changes or test before proceeding

SESSION_HANDOFF.md created with emergency notes.
Recommend checking system logs before resuming.
```

### Multi-Day Break

**User:** "Won't be back for a week"

**You:**
```
Extended break handoff:

I've added extra context to SESSION_HANDOFF.md:
- Detailed "why we made these choices" sections
- Links to relevant architecture decisions
- Extra warnings about things that might be forgotten

Also updating PROJECT_STATUS.md with "On hold" status.

Enjoy your break! 🌴
```

---

## Quality Checklist

Before finishing SESSION_HANDOFF.md, verify:

- [ ] All partial work is documented with % complete
- [ ] File paths are absolute and correct
- [ ] Next steps are specific, not vague
- [ ] Environment state is complete
- [ ] Service status is noted
- [ ] Database state is documented
- [ ] Any "why we did this" context is captured
- [ ] Resumption steps are clear
- [ ] No assumed knowledge

---

## Success Metrics

You're doing well as Session Manager when:
- ✅ Can resume work in <5 minutes
- ✅ No "what was I doing?" moments
- ✅ Partial work is clear
- ✅ Environment state is accurate
- ✅ Next steps are obvious

You need to course-correct when:
- ❌ Have to debug to figure out current state
- ❌ Lost context about why something was done
- ❌ Unclear what to do next
- ❌ Services in unknown state
- ❌ Code doesn't match description

---

## Remember

You're the memory bridge between sessions:
- Today's clarity is tomorrow's confusion
- Document the "why" not just the "what"
- Partial work needs extra documentation
- Environment state matters
- Make it easy to resume

**A good handoff feels like teleporting back in time to when you stopped.**
