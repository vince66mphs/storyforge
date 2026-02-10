#!/usr/bin/env python3
"""StoryForge 2.0 — Interactive Story CLI."""

import asyncio
import sys
import uuid

from sqlalchemy import select

from app.core.database import async_session
from app.models.node import Node
from app.models.story import Story
from app.models.world_bible import WorldBibleEntity
from app.core.exceptions import ServiceUnavailableError
from app.services.asset_service import AssetService
from app.services.context_service import ContextService
from app.services.illustration_service import IllustrationService
from app.services.story_service import StoryGenerationService


# ── Terminal formatting ────────────────────────────────────────────────

BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[36m"
GREEN = "\033[32m"
YELLOW = "\033[33m"
MAGENTA = "\033[35m"
RED = "\033[31m"
RESET = "\033[0m"


def header(text: str) -> str:
    return f"\n{BOLD}{CYAN}{text}{RESET}\n"


def dim(text: str) -> str:
    return f"{DIM}{text}{RESET}"


def info(text: str):
    print(f"{GREEN}> {text}{RESET}")


def warn(text: str):
    print(f"{YELLOW}> {text}{RESET}")


def error(text: str):
    print(f"{RED}> {text}{RESET}")


HELP_TEXT = f"""
{BOLD}Commands:{RESET}
  {CYAN}/new{RESET}              Create a new story
  {CYAN}/load{RESET}             Load an existing story
  {CYAN}/status{RESET}           Show current story info
  {CYAN}/mode [safe|unrestricted]{RESET}  View or set content mode
  {CYAN}/context{RESET}          Show assembled RAG context for current scene
  {CYAN}/tree{RESET}             Show the narrative tree
  {CYAN}/branch{RESET}           Create an alternative from the current scene
  {CYAN}/goto <n>{RESET}         Jump to a node by tree number
  {CYAN}/beat{RESET}             Show the planner beat for the current scene
  {CYAN}/entities{RESET}         List world bible entities
  {CYAN}/detect{RESET}           Auto-detect entities in current scene
  {CYAN}/image <n>{RESET}        Generate image for entity by number
  {CYAN}/illustrate{RESET}       Generate scene illustration for current node
  {CYAN}/export{RESET}           Export story to markdown
  {CYAN}/help{RESET}             Show this help
  {CYAN}/quit{RESET}             Exit

  {DIM}Anything else is treated as a direction for the next scene.{RESET}
"""


# ── CLI Application ───────────────────────────────────────────────────

class StoryForgeCLI:
    def __init__(self):
        self.story_svc = StoryGenerationService()
        self.asset_svc = AssetService()
        self.illustration_svc = IllustrationService()
        self.context_svc = ContextService()
        self.story: Story | None = None
        self.current_node: Node | None = None

    async def run(self):
        print(header("StoryForge 2.0"))
        print(dim("  AI-powered interactive storytelling\n"))
        print(HELP_TEXT)

        async with async_session() as session:
            self.session = session

            # Offer to load or create
            stories = await self._list_stories()
            if stories:
                print(f"  Found {len(stories)} existing stor{'y' if len(stories) == 1 else 'ies'}.")
                print(f"  Type {CYAN}/load{RESET} to continue one, or {CYAN}/new{RESET} to start fresh.\n")
            else:
                print(f"  No stories yet. Type {CYAN}/new{RESET} to begin.\n")

            await self._input_loop()

    async def _input_loop(self):
        while True:
            try:
                prompt = input(f"\n{BOLD}>{RESET} ").strip()
            except (EOFError, KeyboardInterrupt):
                print()
                info("Goodbye!")
                break

            if not prompt:
                continue

            if prompt.startswith("/"):
                parts = prompt.split(maxsplit=1)
                cmd = parts[0].lower()
                arg = parts[1] if len(parts) > 1 else ""

                if cmd in ("/quit", "/exit", "/q"):
                    info("Goodbye!")
                    break
                elif cmd == "/help":
                    print(HELP_TEXT)
                elif cmd == "/new":
                    await self._new_story()
                elif cmd == "/load":
                    await self._load_story()
                elif cmd == "/status":
                    await self._show_status()
                elif cmd == "/tree":
                    await self._show_tree()
                elif cmd == "/branch":
                    await self._branch(arg)
                elif cmd == "/goto":
                    await self._goto_node(arg)
                elif cmd == "/entities":
                    await self._list_entities()
                elif cmd == "/detect":
                    await self._detect_entities()
                elif cmd == "/image":
                    await self._generate_image(arg)
                elif cmd == "/illustrate":
                    await self._illustrate_scene()
                elif cmd == "/mode":
                    await self._set_mode(arg)
                elif cmd == "/context":
                    await self._show_context()
                elif cmd == "/beat":
                    await self._show_beat()
                elif cmd == "/export":
                    await self._export()
                else:
                    warn(f"Unknown command: {cmd} (type /help)")
            else:
                await self._generate_scene(prompt)

    # ── Story Management ──────────────────────────────────────────────

    async def _list_stories(self) -> list[Story]:
        result = await self.session.execute(
            select(Story).order_by(Story.created_at.desc())
        )
        return list(result.scalars().all())

    async def _new_story(self):
        try:
            title = input(f"  {BOLD}Title:{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if not title:
            warn("Title required.")
            return

        try:
            genre = input(f"  {BOLD}Genre{RESET} {DIM}(optional):{RESET} ").strip() or None
        except (EOFError, KeyboardInterrupt):
            genre = None

        try:
            opening = input(f"  {BOLD}Opening scene direction:{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            return
        if not opening:
            warn("Opening direction required.")
            return

        # Create story + root node
        story = Story(title=title, genre=genre)
        self.session.add(story)
        await self.session.flush()

        root = Node(
            story_id=story.id,
            content=f"[Beginning of '{title}']",
            node_type="root",
        )
        self.session.add(root)
        await self.session.flush()
        story.current_leaf_id = root.id
        await self.session.commit()
        await self.session.refresh(story)
        await self.session.refresh(root)

        self.story = story
        self.current_node = root
        info(f"Created: {title} ({story.id})")

        # Generate the opening scene
        await self._generate_scene(opening)

    async def _load_story(self):
        stories = await self._list_stories()
        if not stories:
            warn("No stories found. Use /new to create one.")
            return

        print(header("Your Stories"))
        for i, s in enumerate(stories, 1):
            genre = f" [{s.genre}]" if s.genre else ""
            print(f"  {BOLD}{i}.{RESET} {s.title}{dim(genre)}")

        try:
            choice = input(f"\n  {BOLD}#{RESET} ").strip()
        except (EOFError, KeyboardInterrupt):
            return

        try:
            idx = int(choice) - 1
            if not 0 <= idx < len(stories):
                raise ValueError
        except ValueError:
            warn("Invalid selection.")
            return

        self.story = stories[idx]

        # Load current leaf node
        if self.story.current_leaf_id:
            result = await self.session.execute(
                select(Node).where(Node.id == self.story.current_leaf_id)
            )
            self.current_node = result.scalar_one_or_none()

        info(f"Loaded: {self.story.title}")

        # Show the current scene
        if self.current_node:
            print(header("Current Scene"))
            print(f"  {self.current_node.content}\n")

    async def _show_status(self):
        if not self.story:
            warn("No story loaded. Use /new or /load.")
            return

        await self.session.refresh(self.story)
        result = await self.session.execute(
            select(Node).where(Node.story_id == self.story.id)
        )
        nodes = result.scalars().all()

        result = await self.session.execute(
            select(WorldBibleEntity).where(
                WorldBibleEntity.story_id == self.story.id
            )
        )
        entities = result.scalars().all()

        genre = f" [{self.story.genre}]" if self.story.genre else ""
        print(header("Story Status"))
        print(f"  {BOLD}Title:{RESET}    {self.story.title}{dim(genre)}")
        print(f"  {BOLD}ID:{RESET}       {self.story.id}")
        print(f"  {BOLD}Nodes:{RESET}    {len(nodes)}")
        print(f"  {BOLD}Entities:{RESET} {len(entities)}")
        if self.current_node:
            print(f"  {BOLD}Current:{RESET}  {self.current_node.node_type} ({self.current_node.id})")
        # Story settings
        mode = self.story.content_mode or "unrestricted"
        mode_color = RED if mode == "unrestricted" else GREEN
        print(f"  {BOLD}Mode:{RESET}     {mode_color}{mode}{RESET}")
        ai_label = f"{GREEN}On{RESET}" if self.story.auto_illustrate else f"{DIM}Off{RESET}"
        print(f"  {BOLD}Auto-Ill:{RESET} {ai_label}")
        print(f"  {BOLD}Context:{RESET}  {self.story.context_depth} ancestors")

    # ── Tree Navigation ───────────────────────────────────────────────

    async def _show_tree(self):
        if not self.story:
            warn("No story loaded.")
            return

        result = await self.session.execute(
            select(Node)
            .where(Node.story_id == self.story.id)
            .order_by(Node.created_at)
        )
        all_nodes = list(result.scalars().all())

        if not all_nodes:
            warn("No nodes in story.")
            return

        # Build tree structure
        node_map = {n.id: n for n in all_nodes}
        children_map: dict[uuid.UUID | None, list[Node]] = {}
        root = None
        for n in all_nodes:
            children_map.setdefault(n.parent_id, []).append(n)
            if n.parent_id is None:
                root = n

        print(header("Narrative Tree"))
        self._node_index = []
        self._print_tree(root, node_map, children_map, indent=0)
        print(dim(f"\n  Use /goto <n> to jump to a node."))

    def _print_tree(self, node, node_map, children_map, indent):
        if node is None:
            return
        idx = len(self._node_index) + 1
        self._node_index.append(node)

        prefix = "  " + "  " * indent
        marker = f"{YELLOW}*{RESET}" if node.id == (self.current_node.id if self.current_node else None) else " "
        preview = node.content[:60].replace("\n", " ")
        if len(node.content) > 60:
            preview += "..."
        type_tag = dim(f"[{node.node_type}]")

        print(f"{prefix}{marker}{BOLD}{idx}.{RESET} {type_tag} {preview}")

        for child in children_map.get(node.id, []):
            self._print_tree(child, node_map, children_map, indent + 1)

    async def _goto_node(self, arg: str):
        if not self.story:
            warn("No story loaded.")
            return

        if not hasattr(self, "_node_index") or not self._node_index:
            warn("Run /tree first to see available nodes.")
            return

        try:
            idx = int(arg) - 1
            if not 0 <= idx < len(self._node_index):
                raise ValueError
        except ValueError:
            warn(f"Invalid node number. Use 1-{len(self._node_index)}.")
            return

        node = self._node_index[idx]

        # Refresh from DB in case it's stale
        result = await self.session.execute(
            select(Node).where(Node.id == node.id)
        )
        self.current_node = result.scalar_one()
        self.story.current_leaf_id = self.current_node.id
        await self.session.commit()

        info(f"Jumped to node {idx + 1} ({self.current_node.node_type})")
        print(header("Scene"))
        print(f"  {self.current_node.content}\n")

    # ── Scene Generation ──────────────────────────────────────────────

    async def _generate_scene(self, user_prompt: str):
        if not self.story or not self.current_node:
            warn("No story loaded. Use /new or /load.")
            return

        print(header("Generating..."))

        node = None
        async for chunk in self.story_svc.generate_scene_stream(
            session=self.session,
            story_id=self.story.id,
            parent_node_id=self.current_node.id,
            user_prompt=user_prompt,
        ):
            if isinstance(chunk, dict):
                phase = chunk.get("phase", "")
                if phase == "planning":
                    print(f"  {DIM}Planning scene...{RESET}")
                elif phase == "writing":
                    print(f"  {DIM}Writing...{RESET}")
                    sys.stdout.write("  ")
            elif isinstance(chunk, str):
                sys.stdout.write(chunk)
                sys.stdout.flush()
            else:
                node = chunk

        print("\n")

        if node:
            self.current_node = node
            info(f"Scene saved ({len(node.content)} chars)")
            if node.continuity_warnings:
                for w in node.continuity_warnings:
                    warn(f"Continuity: {w}")

    async def _branch(self, user_prompt: str):
        if not self.story or not self.current_node:
            warn("No story loaded.")
            return

        if self.current_node.parent_id is None:
            warn("Cannot branch from the root node.")
            return

        if not user_prompt:
            try:
                user_prompt = input(f"  {BOLD}Alternative direction:{RESET} ").strip()
            except (EOFError, KeyboardInterrupt):
                return
            if not user_prompt:
                warn("Direction required for branching.")
                return

        print(header("Branching..."))

        # Build the branch using streaming: get context from parent, then stream
        result = await self.session.execute(
            select(Node).where(Node.id == self.current_node.id)
        )
        ref_node = result.scalar_one()

        node = None
        async for chunk in self.story_svc.generate_scene_stream(
            session=self.session,
            story_id=self.story.id,
            parent_node_id=ref_node.parent_id,
            user_prompt=user_prompt,
        ):
            if isinstance(chunk, dict):
                phase = chunk.get("phase", "")
                if phase == "planning":
                    print(f"  {DIM}Planning scene...{RESET}")
                elif phase == "writing":
                    print(f"  {DIM}Writing...{RESET}")
                    sys.stdout.write("  ")
            elif isinstance(chunk, str):
                sys.stdout.write(chunk)
                sys.stdout.flush()
            else:
                node = chunk

        print("\n")

        if node:
            self.current_node = node
            info(f"Branch saved ({len(node.content)} chars)")
            if node.continuity_warnings:
                for w in node.continuity_warnings:
                    warn(f"Continuity: {w}")

    # ── Mode & Context ─────────────────────────────────────────────────

    async def _set_mode(self, arg: str):
        if not self.story:
            warn("No story loaded. Use /new or /load.")
            return

        arg = arg.strip().lower()
        if not arg:
            mode = self.story.content_mode or "unrestricted"
            mode_color = RED if mode == "unrestricted" else GREEN
            info(f"Current mode: {mode_color}{mode}{RESET}")
            print(f"  {DIM}Usage: /mode safe  or  /mode unrestricted{RESET}")
            return

        if arg not in ("safe", "unrestricted"):
            error(f"Invalid mode: '{arg}'. Use 'safe' or 'unrestricted'.")
            return

        self.story.content_mode = arg
        await self.session.commit()
        await self.session.refresh(self.story)
        mode_color = RED if arg == "unrestricted" else GREEN
        info(f"Content mode set to {mode_color}{arg}{RESET}")

    async def _show_context(self):
        if not self.story or not self.current_node:
            warn("No story loaded. Use /new or /load.")
            return

        if self.current_node.node_type == "root":
            warn("Cannot show context for the root node. Generate a scene first.")
            return

        info("Building RAG context...")

        try:
            context = await self.context_svc.build_context(
                session=self.session,
                story_id=self.story.id,
                parent_node_id=self.current_node.id,
                user_prompt="(context preview)",
                ancestor_depth=self.story.context_depth,
            )
        except ServiceUnavailableError as e:
            error(f"Cannot build context: {e}")
            return

        if not context:
            warn("No context assembled (story may be too short).")
            return

        print(header("RAG Context"))
        # Color-code section headers
        for line in context.split("\n"):
            if line.startswith("[") and line.endswith("]"):
                print(f"  {CYAN}{BOLD}{line}{RESET}")
            else:
                print(f"  {line}")

    # ── Beat Display ─────────────────────────────────────────────────

    async def _show_beat(self):
        if not self.story or not self.current_node:
            warn("No story loaded.")
            return

        beat = self.current_node.beat
        if not beat:
            warn("No planner beat for this scene (single-model mode or root node).")
            return

        print(header("Scene Beat"))
        print(f"  {BOLD}Setting:{RESET}    {beat.get('setting', '?')}")

        chars = beat.get("characters_present", [])
        if chars:
            print(f"  {BOLD}Characters:{RESET} {', '.join(chars)}")

        events = beat.get("key_events", [])
        if events:
            print(f"  {BOLD}Events:{RESET}")
            for ev in events:
                print(f"    - {ev}")

        tone = beat.get("emotional_tone", "")
        if tone:
            print(f"  {BOLD}Tone:{RESET}       {tone}")

        notes = beat.get("continuity_notes", "")
        if notes:
            print(f"  {BOLD}Continuity:{RESET} {notes}")

        warnings = beat.get("continuity_warnings", [])
        if warnings:
            print(f"  {YELLOW}{BOLD}Warnings:{RESET}")
            for w in warnings:
                print(f"    {YELLOW}- {w}{RESET}")

    # ── Scene Illustration ─────────────────────────────────────────────

    async def _illustrate_scene(self):
        if not self.story or not self.current_node:
            warn("No story loaded.")
            return

        if self.current_node.node_type == "root":
            warn("Cannot illustrate the root node.")
            return

        info("Generating scene illustration...")

        # Refresh story and node from DB
        result = await self.session.execute(
            select(Story).where(Story.id == self.story.id)
        )
        story = result.scalar_one()
        result = await self.session.execute(
            select(Node).where(Node.id == self.current_node.id)
        )
        node = result.scalar_one()

        filename = await self.illustration_svc.illustrate_scene(
            self.session, node, story
        )

        if filename:
            info(f"Illustration saved: static/images/{filename}")
            self.current_node = node
        else:
            error("Illustration generation failed.")

    # ── Entities ──────────────────────────────────────────────────────

    async def _list_entities(self):
        if not self.story:
            warn("No story loaded.")
            return

        result = await self.session.execute(
            select(WorldBibleEntity)
            .where(WorldBibleEntity.story_id == self.story.id)
            .order_by(WorldBibleEntity.entity_type, WorldBibleEntity.name)
        )
        entities = list(result.scalars().all())

        if not entities:
            warn("No entities yet. Use /detect to find them in scenes.")
            return

        self._entity_index = entities
        print(header("World Bible"))
        for i, e in enumerate(entities, 1):
            img = f" {GREEN}[img]{RESET}" if e.reference_image_path else ""
            print(
                f"  {BOLD}{i}.{RESET} {MAGENTA}[{e.entity_type}]{RESET} "
                f"{e.name}{img} — {dim(e.description[:60])}"
            )
        print(dim(f"\n  Use /image <n> to generate a reference image."))

    async def _detect_entities(self):
        if not self.story or not self.current_node:
            warn("No story loaded.")
            return

        info("Detecting entities in current scene...")
        detected = await self.asset_svc.detect_entities(self.current_node.content)

        if not detected:
            warn("No entities detected in this scene.")
            return

        # Check for existing
        existing = await self.asset_svc.get_entity_references(
            self.session, self.story.id, [e["name"] for e in detected]
        )
        existing_names = {e.name.lower() for e in existing}

        created = []
        for entity_data in detected:
            if entity_data["name"].lower() in existing_names:
                continue
            entity = await self.asset_svc.create_entity(
                self.session, self.story.id, entity_data
            )
            created.append(entity)
            existing_names.add(entity_data["name"].lower())

        skipped = len(detected) - len(created)
        info(f"Detected {len(detected)} entities, created {len(created)} new" +
             (f" (skipped {skipped} existing)" if skipped else ""))

        for e in created:
            print(f"  {MAGENTA}[{e.entity_type}]{RESET} {e.name} — {dim(e.description[:60])}")

    async def _generate_image(self, arg: str):
        if not self.story:
            warn("No story loaded.")
            return

        if not hasattr(self, "_entity_index") or not self._entity_index:
            warn("Run /entities first to see the list.")
            return

        try:
            idx = int(arg) - 1
            if not 0 <= idx < len(self._entity_index):
                raise ValueError
        except ValueError:
            warn(f"Invalid entity number. Use 1-{len(self._entity_index)}.")
            return

        entity = self._entity_index[idx]

        # Refresh from DB
        result = await self.session.execute(
            select(WorldBibleEntity).where(WorldBibleEntity.id == entity.id)
        )
        entity = result.scalar_one()

        info(f"Generating image for {entity.name}...")
        info(f"Prompt: {entity.base_prompt[:80]}...")

        filename = await self.asset_svc.generate_entity_image(
            self.session, entity
        )
        info(f"Image saved: static/images/{filename}")

    # ── Export ─────────────────────────────────────────────────────────

    async def _export(self):
        if not self.story or not self.current_node:
            warn("No story loaded.")
            return

        from pathlib import Path
        from app.core.config import get_settings

        settings = get_settings()

        # Get the path from root to current node
        path_nodes: list[Node] = []
        current_id = self.current_node.id
        while current_id is not None:
            result = await self.session.execute(
                select(Node).where(Node.id == current_id)
            )
            node = result.scalar_one_or_none()
            if node is None:
                break
            path_nodes.append(node)
            current_id = node.parent_id
        path_nodes.reverse()

        # Get entities
        result = await self.session.execute(
            select(WorldBibleEntity)
            .where(WorldBibleEntity.story_id == self.story.id)
            .order_by(WorldBibleEntity.entity_type, WorldBibleEntity.name)
        )
        entities = list(result.scalars().all())

        # Build markdown
        lines = [
            f"# {self.story.title}\n",
        ]
        if self.story.genre:
            lines.append(f"*Genre: {self.story.genre}*\n")
        lines.append("")

        # Entities section
        if entities:
            lines.append("## World Bible\n")
            for e in entities:
                lines.append(f"### {e.name} ({e.entity_type})\n")
                lines.append(f"{e.description}\n")
                if e.reference_image_path:
                    img_path = Path(settings.static_dir) / "images" / e.reference_image_path
                    lines.append(f"![{e.name}]({img_path})\n")
                lines.append("")

        # Story scenes
        lines.append("## Story\n")
        for i, node in enumerate(path_nodes):
            if node.node_type == "root":
                continue
            lines.append(f"### Scene {i}\n")
            lines.append(f"{node.content}\n")
            lines.append("---\n")

        # Write file
        export_dir = Path(settings.export_dir)
        export_dir.mkdir(parents=True, exist_ok=True)
        safe_title = "".join(c if c.isalnum() or c in " -_" else "" for c in self.story.title)
        filename = f"{safe_title}.md"
        filepath = export_dir / filename
        filepath.write_text("\n".join(lines))

        info(f"Exported to {filepath}")


# ── Entry Point ───────────────────────────────────────────────────────

def main():
    try:
        asyncio.run(StoryForgeCLI().run())
    except KeyboardInterrupt:
        print(f"\n{GREEN}> Goodbye!{RESET}")


if __name__ == "__main__":
    main()
