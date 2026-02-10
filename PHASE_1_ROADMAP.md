# Phase 1 Roadmap - MVP Foundation

## Goal
Build a working end-to-end system where users can write a story with AI assistance, generate consistent illustrations, and export the result.

## Success Criteria
- ✅ Story with 5+ scenes generated
- ✅ 3+ character references maintained visually
- ✅ Story branches (at least 1 fork) navigable
- ✅ Export to Markdown with embedded images works

---

## Task Breakdown

### Stage 1: Project Foundation (Infrastructure)

**1.1 Project Structure**
- [ ] Create directory structure:
  ```
  /home/vince/storyforge/
  ├── backend/
  │   ├── app/
  │   │   ├── api/         # FastAPI routers
  │   │   ├── core/        # Config, database
  │   │   ├── models/      # SQLAlchemy models
  │   │   ├── services/    # Business logic
  │   │   └── main.py
  │   ├── alembic/         # DB migrations
  │   ├── requirements.txt
  │   └── .env
  ├── frontend/            # (Phase 1: minimal/CLI)
  ├── static/              # Generated images
  ├── exports/             # Story exports
  └── docs/                # Project documentation
  ```
- [ ] Initialize Python virtual environment
- [ ] Create requirements.txt with core dependencies

**1.2 Database Setup**
- [ ] Drop existing databases in PostgreSQL
- [ ] Create new `storyforge` database
- [ ] Install pgvector extension
- [ ] Initialize Alembic for migrations
- [ ] Create database configuration module

**Deliverable:** Empty project structure with working database connection

---

### Stage 2: Data Layer (The Narrative DAG)

**2.1 Core Database Schema**

Create three primary tables:

**stories table:**
```sql
- id (UUID, PK)
- title (VARCHAR)
- genre (VARCHAR, nullable)
- created_at (TIMESTAMP)
- updated_at (TIMESTAMP)
- current_leaf_id (UUID, FK to nodes, nullable)
- metadata (JSONB)
```

**nodes table (The Multiverse Tree):**
```sql
- id (UUID, PK)
- story_id (UUID, FK to stories)
- parent_id (UUID, FK to nodes, nullable for root)
- content (TEXT)
- summary (TEXT, nullable)
- embedding (VECTOR(768), nullable)
- node_type (VARCHAR: 'root', 'scene', 'choice')
- created_at (TIMESTAMP)
- metadata (JSONB)
```

**world_bible table (Asset Catalog):**
```sql
- id (UUID, PK)
- story_id (UUID, FK to stories)
- entity_type (VARCHAR: 'character', 'location', 'prop')
- name (VARCHAR)
- description (TEXT)
- base_prompt (TEXT) # For image generation
- reference_image_path (VARCHAR, nullable)
- image_seed (BIGINT, nullable)
- embedding (VECTOR(768), nullable)
- metadata (JSONB)
- created_at (TIMESTAMP)
- version (INT, default 1) # For asset evolution
```

**2.2 Indexes**
- [ ] Create indexes on parent_id for tree traversal
- [ ] Create HNSW indexes on embedding columns for vector search
- [ ] Create indexes on story_id for partitioning

**2.3 SQLAlchemy Models**
- [ ] Create Story model
- [ ] Create Node model with self-referential parent
- [ ] Create WorldBible model
- [ ] Test relationships and queries

**Deliverable:** Working database schema with Alembic migration

---

### Stage 3: Services Layer (AI Integration)

**3.1 Ollama Service**
```python
class OllamaService:
    def generate(model: str, prompt: str, system: str) -> str
    def generate_stream(model: str, prompt: str) -> AsyncIterator[str]
    def create_embedding(text: str) -> List[float]
```

**3.2 ComfyUI Service**
```python
class ComfyUIService:
    def generate_image(prompt: str, reference_image: str = None) -> str
    def queue_workflow(workflow: dict) -> str
    def get_image(filename: str) -> bytes
```

**3.3 Story Generation Service**
```python
class StoryGenerationService:
    def generate_scene(story_id: UUID, parent_node_id: UUID, user_prompt: str) -> Node
    def create_branch(node_id: UUID, user_prompt: str) -> Node
    def get_story_context(node_id: UUID, depth: int = 3) -> str
```

**3.4 Asset Management Service**
```python
class AssetService:
    def detect_entities(text: str) -> List[Dict]
    def create_entity(story_id: UUID, entity_data: Dict) -> WorldBible
    def get_entity_references(story_id: UUID, entity_names: List[str]) -> List[WorldBible]
    def generate_entity_image(entity: WorldBible) -> str
```

**Deliverable:** Working services that can generate text and images

---

### Stage 4: API Layer (FastAPI Endpoints)

**4.1 Story Endpoints**
```
POST   /api/stories                    # Create new story
GET    /api/stories/{story_id}         # Get story with current branch
GET    /api/stories/{story_id}/tree    # Get full DAG visualization data
DELETE /api/stories/{story_id}         # Delete story
```

**4.2 Node Endpoints**
```
POST   /api/stories/{story_id}/nodes           # Generate next scene
POST   /api/nodes/{node_id}/branch             # Create alternative branch
GET    /api/nodes/{node_id}                    # Get single node
GET    /api/nodes/{node_id}/path               # Get path from root to node
PATCH  /api/nodes/{node_id}                    # Edit node content manually
```

**4.3 Asset Endpoints**
```
POST   /api/stories/{story_id}/entities        # Manually add entity
GET    /api/stories/{story_id}/entities        # List all entities
GET    /api/entities/{entity_id}               # Get entity details
POST   /api/entities/{entity_id}/image         # Generate/regenerate image
PATCH  /api/entities/{entity_id}               # Update entity (versioning)
```

**4.4 Generation Endpoints (WebSocket)**
```
WS     /ws/generate                            # Streaming generation
```

**4.5 Export Endpoints**
```
GET    /api/stories/{story_id}/export/markdown # Export as .md with images
GET    /api/stories/{story_id}/export/json     # Export as JSON
```

**Deliverable:** Complete REST API with OpenAPI documentation

---

### Stage 5: Basic Interface

**Option A: CLI Interface (Fastest MVP)**
```python
# cli.py
def interactive_story():
    story = create_story(title="My Story")
    while True:
        user_input = input("> ")
        if user_input == "exit":
            break
        elif user_input == "branch":
            # Show available branches
        elif user_input == "export":
            # Export story
        else:
            # Generate next scene
            stream_response(story, user_input)
```

**Option B: Minimal Web UI (Better UX)**
- Simple React app with:
  - Text input for prompts
  - Streaming text display
  - Image gallery of generated illustrations
  - Entity sidebar showing characters/locations
  - Export button

**Recommendation:** Start with CLI (Option A), add web UI in Stage 6

**Deliverable:** Working interface to create and navigate stories

---

### Stage 6: Integration & Polish

**6.1 End-to-End Testing**
- [ ] Test: Create story → Generate 5 scenes → Export
- [ ] Test: Create character → Generate image → Reuse in scene
- [ ] Test: Branch at scene 3 → Generate alternative → Navigate both

**6.2 Export Implementation**
- [ ] Markdown export with embedded images (base64 or file references)
- [ ] Copy images to export directory
- [ ] Generate table of contents
- [ ] Format code blocks and dialogue

**6.3 Error Handling**
- [ ] Ollama connection failures
- [ ] ComfyUI timeout/failures
- [ ] Database constraint violations
- [ ] Graceful degradation (e.g., skip images if ComfyUI down)

**6.4 Documentation**
- [ ] API documentation (auto-generated via FastAPI)
- [ ] User guide for CLI/interface
- [ ] Deployment guide
- [ ] Update PROJECT_STATUS.md with final MVP status

**Deliverable:** Production-ready MVP

---

## Development Order (Suggested)

**Week 1: Foundation**
1. Stage 1: Project structure
2. Stage 2: Database schema
3. Basic CRUD operations (without AI)

**Week 2: Intelligence**
4. Stage 3: Ollama integration
5. Stage 3: ComfyUI integration
6. Test single scene generation

**Week 3: API & Interface**
7. Stage 4: REST API
8. Stage 5: CLI interface
9. Test branching narratives

**Week 4: Complete MVP**
10. Stage 6: Export functionality
11. Stage 6: Error handling
12. Stage 6: Documentation

---

## Testing Strategy

After each stage:
1. Write integration test demonstrating feature works
2. Update PROJECT_STATUS.md with results
3. Document any issues in PROJECT_STATUS.md
4. Don't proceed to next stage until current is stable

---

## Phase 1 Non-Goals

Things we are NOT implementing yet:
- ❌ Multi-agent MoA (Planner/Writer split)
- ❌ Model swapping based on task
- ❌ RAG for long-form memory (use last N nodes only)
- ❌ Redux/PuLID advanced consistency (basic IP-Adapter only)
- ❌ Rich web UI with DAG visualization
- ❌ LoRA training pipeline
- ❌ Audio narration

These are Phase 2 features.

---

## Ready to Start?

Begin with:
1. Adopt ROLE_ARCHITECT
2. Create initial project structure (Stage 1.1)
3. Set up virtual environment and requirements.txt
4. Switch to ROLE_PROJECT_MANAGER
5. Create PROJECT_STATUS.md with Stage 1.1 as first task
