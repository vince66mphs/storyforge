# Setup Instructions - Getting Started with StoryForge 2.0

## Overview
This guide walks you through initializing the StoryForge 2.0 project using Claude Code on the debian-storybook-lxc server.

---

## Prerequisites

**Server Details:**
- Host: debian-storybook-lxc (192.168.1.71)
- SSH Access: `ssh vince@192.168.1.71`
- Project Path: `/home/vince/storyforge/`

**Already Installed:**
- ✅ PostgreSQL (running, needs database reset)
- ✅ Ollama (running on :11434)
- ✅ ComfyUI (running on :8188)
- ✅ Python 3.11+
- ✅ GPU passthrough configured

**Models Available:**
- phi4:latest
- dolphin-mistral:7b
- gemma2:9b
- nomic-embed-text:latest

---

## Step 1: Upload Project Documents

### 1.1 Connect to Server
```bash
ssh vince@192.168.1.71
cd /home/vince/storyforge/
```

### 1.2 Create Docs Directory
```bash
mkdir -p /home/vince/storyforge/docs
```

### 1.3 Upload Foundation Documents

Using your preferred method (scp, SFTP, or paste into nano), upload these files to `/home/vince/storyforge/`:

**Required files:**
1. `CLAUDE.md` - Main instructions for Claude Code
2. `PROJECT_CHARTER.md` - Vision and goals
3. `PHASE_1_ROADMAP.md` - MVP implementation plan
4. `TECH_STACK.md` - Technical decisions
5. `ARCHITECTURE_DECISIONS.md` - Decision rationale
6. `SETUP_INSTRUCTIONS.md` - This file

**Example using scp (from Windows):**
```powershell
# From directory containing the generated .md files
scp CLAUDE.md vince@192.168.1.71:/home/vince/storyforge/
scp PROJECT_CHARTER.md vince@192.168.1.71:/home/vince/storyforge/
scp PHASE_1_ROADMAP.md vince@192.168.1.71:/home/vince/storyforge/
scp TECH_STACK.md vince@192.168.1.71:/home/vince/storyforge/
scp ARCHITECTURE_DECISIONS.md vince@192.168.1.71:/home/vince/storyforge/
scp SETUP_INSTRUCTIONS.md vince@192.168.1.71:/home/vince/storyforge/
```

### 1.4 Verify Upload
```bash
ls -la /home/vince/storyforge/*.md
```

You should see all 6 .md files listed.

---

## Step 2: Prepare the Environment

### 2.1 Clean Up Old Databases (if needed)
```bash
# Connect to PostgreSQL
sudo -u postgres psql

# Inside psql:
DROP DATABASE IF EXISTS storyforge;
DROP DATABASE IF EXISTS storyforge_old;  # If exists from previous iteration

# List databases to confirm
\l

# Exit psql
\q
```

### 2.2 Verify Services Running
```bash
# Check PostgreSQL
sudo systemctl status postgresql

# Check Ollama
curl http://localhost:11434/api/tags

# Check ComfyUI
curl http://localhost:8188/system_stats
```

All services should be active/running.

---

## Step 3: Start Claude Code

### 3.1 Navigate to Project Directory
```bash
cd /home/vince/storyforge/
```

### 3.2 Start Claude Code
```bash
claude-code
```

This launches Claude Code in the current directory.

---

## Step 4: Initialize Claude Code with Project Context

### 4.1 First Prompt - Load Context

**Copy and paste this into Claude Code:**

```
I'm starting a new project called StoryForge 2.0. Please read the following documents to understand the project:

1. CLAUDE.md - Your main instructions
2. PROJECT_CHARTER.md - Project vision and goals
3. TECH_STACK.md - Technical decisions
4. PHASE_1_ROADMAP.md - MVP implementation plan
5. ARCHITECTURE_DECISIONS.md - Decision rationale

After reading these documents, please:
1. Confirm you understand the project scope
2. Adopt the ROLE_ARCHITECT role
3. Outline the first 3 tasks from Stage 1 of PHASE_1_ROADMAP.md
4. Ask if I'm ready to proceed with implementation
```

### 4.2 Expected Response

Claude Code should:
- Read all 5 documents
- Confirm understanding
- Identify as "ROLE_ARCHITECT"
- List tasks:
  1. Create project directory structure
  2. Initialize Python virtual environment
  3. Create requirements.txt with core dependencies
- Wait for your confirmation to proceed

---

## Step 5: Begin Implementation

### 5.1 Confirm Start

Once Claude Code has outlined the tasks, respond:

```
Yes, please proceed with Stage 1.1: Project Structure. Create the directory structure, initialize the virtual environment, and create requirements.txt based on TECH_STACK.md.
```

### 5.2 Claude Code Will Execute

Claude Code should:
- Create directory tree (backend/, frontend/, static/, etc.)
- Run `python3 -m venv .venv`
- Generate requirements.txt with FastAPI, SQLAlchemy, etc.
- Activate virtual environment
- Install dependencies

### 5.3 After Completion

Claude Code should automatically:
- Switch to ROLE_PROJECT_MANAGER
- Create `PROJECT_STATUS.md` with:
  - Completed: Stage 1.1 (Project Structure)
  - Current Status: Ready for Stage 1.2 (Database Setup)
  - Next Steps: Initialize PostgreSQL database and Alembic

---

## Step 6: Continue Iterative Development

### 6.1 The Development Loop

For each subsequent task:

**You provide:**
```
Please proceed with the next task: [task description from PHASE_1_ROADMAP.md]
```

**Claude Code will:**
1. Adopt appropriate role (Architect, Implementation, Database, etc.)
2. Reference relevant documents
3. Outline approach
4. Execute work
5. Update PROJECT_STATUS.md
6. Suggest next steps

### 6.2 Checking Progress

At any time, you can ask:
```
Please show me the current status from PROJECT_STATUS.md
```

Or:
```
What are the next 3 tasks in the roadmap?
```

---

## Step 7: Role-Based Prompts

### When You Need Different Perspectives

**Architecture Decisions:**
```
Adopt ROLE_ARCHITECT. I need to decide between [Option A] and [Option B] for [feature]. Please analyze the tradeoffs and make a recommendation based on our TECH_STACK.md constraints.
```

**Implementation:**
```
Adopt ROLE_IMPLEMENTATION. Please implement the StoryGenerationService as outlined in PHASE_1_ROADMAP.md Stage 3.3. Reference TECH_STACK.md for Ollama integration details.
```

**Database Work:**
```
Adopt ROLE_DATABASE. Please create the nodes table schema from PHASE_1_ROADMAP.md Stage 2.1 and generate the Alembic migration.
```

**Service Integration:**
```
Adopt ROLE_INTEGRATION. Please create the ComfyUI client service that can queue workflows and retrieve generated images. Reference TECH_STACK.md for API details.
```

**Progress Tracking:**
```
Adopt ROLE_PROJECT_MANAGER. Please update PROJECT_STATUS.md with what we've completed today and identify any blockers.
```

---

## Troubleshooting

### Claude Code Can't Find Documents

**Issue:** "I don't see CLAUDE.md"

**Solution:**
```bash
# Verify files are in correct location
ls -la /home/vince/storyforge/*.md

# Make sure Claude Code is started in correct directory
cd /home/vince/storyforge/
claude-code
```

### PostgreSQL Connection Issues

**Issue:** Can't connect to database

**Solution:**
```bash
# Check PostgreSQL is running
sudo systemctl status postgresql

# Check if database exists
sudo -u postgres psql -l

# Verify credentials in .env file
cat backend/.env
```

### Ollama Not Responding

**Issue:** LLM generation fails

**Solution:**
```bash
# Check Ollama service
curl http://localhost:11434/api/tags

# List loaded models
ollama list

# If not running, start it
sudo systemctl start ollama
```

### ComfyUI Issues

**Issue:** Image generation fails

**Solution:**
```bash
# Check ComfyUI is running
curl http://localhost:8188/system_stats

# Check logs
journalctl -u comfyui -f

# If not running, start it
sudo systemctl start comfyui
```

### Virtual Environment Issues

**Issue:** Dependencies not found

**Solution:**
```bash
# Activate virtual environment
cd /home/vince/storyforge/backend
source .venv/bin/activate

# Verify activation (should show (.venv) in prompt)
which python

# Reinstall if needed
pip install -r requirements.txt
```

---

## Tips for Working with Claude Code

### 1. Always Reference Documents
When asking Claude Code to do something, remind it which documents to reference:
```
Reference PHASE_1_ROADMAP.md Stage 2.1 and create the database schema.
```

### 2. Request Status Updates
After significant work:
```
Switch to ROLE_PROJECT_MANAGER and update PROJECT_STATUS.md with what we just completed.
```

### 3. Break Down Large Tasks
Instead of:
```
Build the entire API layer
```

Use:
```
Create the Story endpoints (POST /api/stories, GET /api/stories/{id}) as defined in PHASE_1_ROADMAP.md Stage 4.1
```

### 4. Ask for Clarification
If Claude Code's approach seems off:
```
Wait, let me clarify the requirements. Reference ARCHITECTURE_DECISIONS.md AD-003 - we're using a single model for Phase 1, not MoA yet.
```

### 5. Review Before Executing
For destructive operations:
```
Before you drop the database, please show me the exact SQL commands you'll run so I can verify.
```

---

## What Success Looks Like

### After 1-2 Hours
- ✅ Project structure created
- ✅ Virtual environment set up
- ✅ Database schema defined
- ✅ Basic Ollama integration working
- ✅ PROJECT_STATUS.md tracking progress

### After 1-2 Days
- ✅ All Stage 1-3 tasks complete (Services layer)
- ✅ REST API endpoints working
- ✅ Can generate a simple scene via API
- ✅ Can generate an image via ComfyUI

### After 3-5 Days
- ✅ MVP complete (all 6 stages)
- ✅ CLI interface working
- ✅ Can write multi-scene story with branches
- ✅ Characters maintain visual consistency
- ✅ Export to Markdown works

---

## Ready to Begin?

Once you've completed Steps 1-4 above, you're ready to build!

Remember:
- Claude Code is your development partner
- The role documents guide its perspective
- PROJECT_STATUS.md tracks everything
- The roadmap is your north star
- Take it one stage at a time

**First command to Claude Code after setup:**
```
I'm ready to begin development. Please read all project documents and adopt ROLE_ARCHITECT to start Stage 1.1: Project Structure from PHASE_1_ROADMAP.md.
```

Let's build StoryForge 2.0! 🚀
