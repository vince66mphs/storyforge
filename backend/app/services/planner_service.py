"""Planner service — generates structured story beats using phi4.

The planner is the first pass of the MoA (Mixture of Agents) pipeline.
It produces a JSON beat that guides the writer model for prose generation.
"""

import json
import logging

from app.core.config import get_settings
from app.services.ollama_service import OllamaService

logger = logging.getLogger(__name__)

PLANNER_SYSTEM_PROMPT = (
    "You are a story planner. Given context from an ongoing interactive story "
    "and the reader's direction, produce a structured JSON plan for the NEXT scene.\n\n"
    "Respond with ONLY valid JSON (no markdown fences, no commentary) matching this schema:\n"
    "{\n"
    '  "setting": "Where this scene takes place",\n'
    '  "characters_present": ["Name1", "Name2"],\n'
    '  "key_events": ["Event 1", "Event 2", "Event 3"],\n'
    '  "emotional_tone": "The dominant mood/atmosphere",\n'
    '  "continuity_notes": "Important details to maintain from prior scenes",\n'
    '  "continuity_warnings": ["Any inconsistencies or unknowns spotted"]\n'
    "}\n\n"
    "Keep events to 2-4 items. Be specific and actionable. "
    "If you spot characters or details that contradict earlier scenes, "
    "add warnings to continuity_warnings.\n\n"
    "PHYSICAL CONTINUITY — check these before planning:\n"
    "- Who is driving/navigating? Do not swap roles unless the plan includes an event showing the switch.\n"
    "- Time of day must advance, not repeat. If the sun already set, it stays dark.\n"
    "- Track character positions (inside/outside a vehicle, seated/standing, room location). "
    "Do not teleport characters between positions without an event covering the movement.\n"
    "- Communication mode: text messages are read on a screen, not spoken aloud. "
    "Phone calls are heard through a speaker or earpiece. Note the mode in continuity_notes.\n"
    "- If the prior scene established a specific physical detail (injury, clothing, weather), "
    "carry it forward in continuity_notes."
)

FALLBACK_BEAT = {
    "setting": "Continuing from previous scene",
    "characters_present": [],
    "key_events": ["Continue the story based on reader direction"],
    "emotional_tone": "Determined by context",
    "continuity_notes": "",
    "continuity_warnings": ["Planner produced invalid output — using fallback beat"],
}


class PlannerService:
    """Generates structured story beats for the MoA pipeline."""

    def __init__(self):
        self.ollama = OllamaService()
        settings = get_settings()
        self._model = settings.planner_model
        self._keep_alive = settings.planner_keep_alive

    async def plan_beat(
        self,
        context: str,
        user_prompt: str,
        world_bible_entities: list[dict] | None = None,
    ) -> dict:
        """Generate a structured beat for the next scene.

        Args:
            context: Assembled story context (from ContextService).
            user_prompt: The reader's direction.
            world_bible_entities: Known entities for continuity checking.

        Returns:
            A beat dict with planning fields. Always returns a valid dict
            (falls back to FALLBACK_BEAT on parse failure).
        """
        prompt_parts = [f"Story context:\n{context}"]

        if world_bible_entities:
            entity_list = "\n".join(
                f"- {e['name']} ({e['type']}): {e['description']}"
                for e in world_bible_entities
            )
            prompt_parts.append(f"\nKnown world bible entities:\n{entity_list}")

        prompt_parts.append(f"\nReader's direction: {user_prompt}")
        prompt_parts.append("\nPlan the next scene as JSON:")

        full_prompt = "\n".join(prompt_parts)

        logger.info("Planning beat with model=%s, prompt_len=%d", self._model, len(full_prompt))

        try:
            raw = await self.ollama.generate(
                prompt=full_prompt,
                system=PLANNER_SYSTEM_PROMPT,
                model=self._model,
                keep_alive=self._keep_alive,
            )
            beat = self._parse_beat(raw)
        except Exception as e:
            logger.warning("Planner failed: %s — using fallback beat", e)
            beat = dict(FALLBACK_BEAT)
            beat["continuity_warnings"] = [f"Planner error: {e}"]

        # Validate characters against world bible
        if world_bible_entities:
            known_names = {e["name"].lower() for e in world_bible_entities}
            unknown = [
                name for name in beat.get("characters_present", [])
                if name.lower() not in known_names
            ]
            if unknown:
                warnings = beat.get("continuity_warnings", [])
                warnings.append(f"Unknown characters (not in world bible): {', '.join(unknown)}")
                beat["continuity_warnings"] = warnings

                # Build structured data for one-click "Add to World Bible"
                beat["unknown_characters"] = [
                    {
                        "name": name,
                        "entity_type": "character",
                        "description": self._extract_character_context(beat, name),
                        "base_prompt": self._build_character_prompt(beat, name),
                    }
                    for name in unknown
                ]

        logger.info(
            "Beat planned: %d events, tone=%s, %d warnings",
            len(beat.get("key_events", [])),
            beat.get("emotional_tone", "?"),
            len(beat.get("continuity_warnings", [])),
        )
        return beat

    @staticmethod
    def _extract_character_context(beat: dict, name: str) -> str:
        """Pull a short description from beat events/setting for an unknown character."""
        parts = []
        for event in beat.get("key_events", []):
            if name.lower() in event.lower():
                parts.append(event)
        if not parts:
            parts.append(f"Character appearing in: {beat.get('setting', 'unknown setting')}")
        return "; ".join(parts)

    @staticmethod
    def _build_character_prompt(beat: dict, name: str) -> str:
        """Build a base image prompt for an unknown character."""
        setting = beat.get("setting", "")
        tone = beat.get("emotional_tone", "")
        prompt_parts = [f"portrait of {name}"]
        if setting:
            prompt_parts.append(setting)
        if tone:
            prompt_parts.append(f"{tone} atmosphere")
        return ", ".join(prompt_parts)

    def _parse_beat(self, raw: str) -> dict:
        """Parse JSON from planner output, handling markdown fences."""
        text = raw.strip()
        # Strip markdown code fences if present
        if text.startswith("```"):
            lines = text.split("\n")
            # Remove first line (```json or ```) and last line (```)
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()

        try:
            beat = json.loads(text)
        except json.JSONDecodeError as e:
            logger.warning("Failed to parse planner JSON: %s, attempting extraction", e)
            # Try to find JSON object in the response
            start = text.find("{")
            end = text.rfind("}") + 1
            if start >= 0 and end > start:
                try:
                    beat = json.loads(text[start:end])
                except json.JSONDecodeError:
                    logger.warning("Extraction also failed, using fallback beat")
                    return dict(FALLBACK_BEAT)
            else:
                logger.warning("No JSON found in planner output: %s", text[:200])
                return dict(FALLBACK_BEAT)

        # Ensure required fields exist
        beat.setdefault("setting", "")
        beat.setdefault("characters_present", [])
        beat.setdefault("key_events", [])
        beat.setdefault("emotional_tone", "")
        beat.setdefault("continuity_notes", "")
        beat.setdefault("continuity_warnings", [])

        return beat

    async def check_continuity(
        self,
        scenes: list[dict],
        world_bible: list[dict],
    ) -> list[dict]:
        """Analyze scenes for continuity issues without generating new content.

        Args:
            scenes: List of dicts with "number" and "content" keys.
            world_bible: List of dicts with "name", "type", "description" keys.

        Returns:
            List of issue dicts with "scene", "issue", "severity" keys.
        """
        scene_text = "\n\n".join(
            f"--- Scene {s['number']} ---\n{s['content']}" for s in scenes
        )

        entity_text = ""
        if world_bible:
            entity_text = "\nWorld Bible entities:\n" + "\n".join(
                f"- {e['name']} ({e['type']}): {e['description']}"
                for e in world_bible
            )

        system = (
            "You are a continuity checker for interactive fiction. "
            "Analyze the provided scenes and flag inconsistencies. "
            "Check for:\n"
            "- Physical inconsistencies (who is driving, position changes without movement)\n"
            "- Timeline/time-of-day errors (sun setting twice, morning after night without sleep)\n"
            "- Character knowledge contradictions (knowing something they shouldn't)\n"
            "- Unresolved plot threads or disappearing characters\n"
            "- World bible mismatches (descriptions contradicting established entities)\n\n"
            "Return ONLY a JSON array of objects. Each object must have:\n"
            '  "scene": <scene number (int)>,\n'
            '  "issue": "<description of the problem>",\n'
            '  "severity": "warning" or "error"\n\n'
            "If no issues are found, return an empty array: []\n"
            "Return ONLY valid JSON, no markdown fences or explanation."
        )

        prompt = f"Scenes to analyze:\n{scene_text}{entity_text}\n\nCheck for continuity issues:"

        logger.info("Checking continuity for %d scenes", len(scenes))

        try:
            raw = await self.ollama.generate(
                prompt=prompt,
                system=system,
                model=self._model,
                keep_alive=self._keep_alive,
            )
            issues = self._parse_continuity(raw)
        except Exception as e:
            logger.warning("Continuity check failed: %s", e)
            issues = [{"scene": 0, "issue": f"Continuity check failed: {e}", "severity": "error"}]

        logger.info("Continuity check found %d issues", len(issues))
        return issues

    def _parse_continuity(self, raw: str) -> list[dict]:
        """Parse JSON array from continuity check output."""
        text = raw.strip()
        if text.startswith("```"):
            lines = text.split("\n")
            lines = [l for l in lines if not l.strip().startswith("```")]
            text = "\n".join(lines).strip()

        try:
            result = json.loads(text)
        except json.JSONDecodeError:
            # Try to find JSON array in the response
            start = text.find("[")
            end = text.rfind("]") + 1
            if start >= 0 and end > start:
                try:
                    result = json.loads(text[start:end])
                except json.JSONDecodeError:
                    return [{"scene": 0, "issue": "Failed to parse continuity response", "severity": "error"}]
            else:
                return [{"scene": 0, "issue": "Failed to parse continuity response", "severity": "error"}]

        if not isinstance(result, list):
            return [{"scene": 0, "issue": "Unexpected response format", "severity": "error"}]

        # Validate each issue
        valid = []
        for item in result:
            if isinstance(item, dict) and "scene" in item and "issue" in item:
                item.setdefault("severity", "warning")
                valid.append(item)

        return valid
