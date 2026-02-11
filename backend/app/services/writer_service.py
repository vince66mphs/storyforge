"""Writer service — expands planner beats into prose.

The writer is the second pass of the MoA (Mixture of Agents) pipeline.
It takes a structured beat from the PlannerService and generates vivid
narrative prose, respecting the content mode.
"""

import logging
import re
from collections.abc import AsyncIterator

from app.core.config import get_settings
from app.services.ollama_service import OllamaService

logger = logging.getLogger(__name__)

WRITER_SYSTEM_UNRESTRICTED = (
    "You are a creative fiction writer collaborating with a reader on an interactive story. "
    "You will be given a scene plan (beat) and story context. "
    "Expand the beat into vivid, engaging prose — 2-4 paragraphs. "
    "Follow the beat's structure (setting, characters, events, tone) but do NOT "
    "echo the beat verbatim or reference it as a plan. Write naturally as narrative prose. "
    "End at a moment that invites the reader to choose what happens next. "
    "Do not break the fourth wall or mention that you are an AI. "
    "You have full creative freedom — explore any themes, emotions, or situations "
    "the story demands without restriction.\n\n"
    "STRICT RULES — violating any of these ruins the story:\n"
    "- Output ONLY narrative prose. No meta-commentary, sign-offs, or questions to the reader "
    "(e.g. never write 'Let me know if you would like me to continue').\n"
    "- Never include [WORLD BIBLE], Scene plan:, or any formatting markers in your output.\n"
    "- Do not repeat the opening description at the end of the scene.\n"
    "- Text messages between characters must be described as text on a screen, not spoken aloud.\n"
    "- Maintain physical consistency: whoever is driving stays driving unless the scene "
    "shows them switching. Track spatial positions (inside/outside, seated/standing).\n"
    "- Time of day must progress naturally — the sun sets once, not repeatedly."
)

WRITER_SYSTEM_SAFE = (
    "You are a creative fiction writer collaborating with a reader on an interactive story. "
    "You will be given a scene plan (beat) and story context. "
    "Expand the beat into vivid, engaging prose — 2-4 paragraphs. "
    "Follow the beat's structure (setting, characters, events, tone) but do NOT "
    "echo the beat verbatim or reference it as a plan. Write naturally as narrative prose. "
    "End at a moment that invites the reader to choose what happens next. "
    "Do not break the fourth wall or mention that you are an AI. "
    "Keep content appropriate for a general audience — avoid graphic violence, "
    "explicit sexual content, and excessive profanity.\n\n"
    "STRICT RULES — violating any of these ruins the story:\n"
    "- Output ONLY narrative prose. No meta-commentary, sign-offs, or questions to the reader "
    "(e.g. never write 'Let me know if you would like me to continue').\n"
    "- Never include [WORLD BIBLE], Scene plan:, or any formatting markers in your output.\n"
    "- Do not repeat the opening description at the end of the scene.\n"
    "- Text messages between characters must be described as text on a screen, not spoken aloud.\n"
    "- Maintain physical consistency: whoever is driving stays driving unless the scene "
    "shows them switching. Track spatial positions (inside/outside, seated/standing).\n"
    "- Time of day must progress naturally — the sun sets once, not repeatedly."
)


class WriterService:
    """Expands planner beats into narrative prose."""

    def __init__(self):
        self.ollama = OllamaService()
        settings = get_settings()
        self._writer_models = {
            "unrestricted": settings.writer_model_unrestricted,
            "safe": settings.writer_model_safe,
        }
        self._keep_alive = settings.writer_keep_alive

    # Patterns that indicate the prose has ended and model artifacts follow.
    # Each pattern matches at the START of a line.
    _CUTOFF_PATTERNS = re.compile(
        r"^("
        r"Let me know\b"
        r"|I'll provide\b"
        r"|Continue with\b"
        r"|I hope you enjoy"
        r"|If you would like"
        r"|Would you like"
        r"|Feel free to\b"
        r"|I made some\b"
        r"|Here are some\b"
        r"|These are just\b"
        r"|Note:|Notes:"
        r"|\(Note:"
        r"|\[WORLD BIBLE\]"
        r"|Scene plan:"
        r"|---\s*$"
        r")",
        re.MULTILINE | re.IGNORECASE,
    )

    @staticmethod
    def _clean_output(text: str) -> str:
        """Strip leaked model artifacts from writer output.

        Detects meta-commentary, sign-offs, [WORLD BIBLE] blocks, and
        scene plan dumps that appear after the actual prose, and removes
        everything from the first such marker onward.
        """
        # Split into lines and scan for cutoff markers
        lines = text.split("\n")
        cutoff_idx: int | None = None

        for i, line in enumerate(lines):
            stripped = line.strip()
            # Skip blank lines — they might just be paragraph breaks
            if not stripped:
                continue
            if WriterService._CUTOFF_PATTERNS.match(stripped):
                # A lone "---" inside prose is legitimate (section break)
                # Only treat it as cutoff if ANY remaining line contains meta-commentary
                if stripped.startswith("---"):
                    remaining_lines = [
                        l.strip() for l in lines[i + 1:] if l.strip()
                    ]
                    if not remaining_lines or any(
                        WriterService._CUTOFF_PATTERNS.match(l)
                        for l in remaining_lines
                    ):
                        cutoff_idx = i
                        break
                    # Legitimate horizontal rule inside prose — skip
                    continue
                cutoff_idx = i
                break

        if cutoff_idx is not None:
            text = "\n".join(lines[:cutoff_idx])

        return text.rstrip()

    def _get_model(self, content_mode: str) -> str:
        return self._writer_models.get(content_mode, self._writer_models["unrestricted"])

    def _get_system_prompt(self, content_mode: str) -> str:
        if content_mode == "safe":
            return WRITER_SYSTEM_SAFE
        return WRITER_SYSTEM_UNRESTRICTED

    def _format_beat_prompt(self, beat: dict, context: str) -> str:
        """Format beat and context into a writer prompt."""
        parts = [f"Story so far:\n{context}"]

        parts.append("\nScene plan:")
        parts.append(f"  Setting: {beat.get('setting', 'Continuing from previous')}")

        characters = beat.get("characters_present", [])
        if characters:
            parts.append(f"  Characters present: {', '.join(characters)}")

        events = beat.get("key_events", [])
        if events:
            parts.append("  Key events:")
            for event in events:
                parts.append(f"    - {event}")

        tone = beat.get("emotional_tone", "")
        if tone:
            parts.append(f"  Emotional tone: {tone}")

        continuity = beat.get("continuity_notes", "")
        if continuity:
            parts.append(f"  Continuity notes: {continuity}")

        parts.append("\nWrite this scene as narrative prose:")
        return "\n".join(parts)

    async def write_scene(
        self,
        beat: dict,
        context: str,
        content_mode: str,
    ) -> str:
        """Generate complete scene prose from a beat.

        Args:
            beat: Structured beat from PlannerService.
            context: Assembled story context.
            content_mode: 'unrestricted' or 'safe'.

        Returns:
            The generated prose text.
        """
        model = self._get_model(content_mode)
        system = self._get_system_prompt(content_mode)
        prompt = self._format_beat_prompt(beat, context)

        logger.info("Writing scene with model=%s, mode=%s", model, content_mode)

        raw = await self.ollama.generate(
            prompt=prompt,
            system=system,
            model=model,
            keep_alive=self._keep_alive,
        )
        return self._clean_output(raw)

    async def write_scene_stream(
        self,
        beat: dict,
        context: str,
        content_mode: str,
    ) -> AsyncIterator[str]:
        """Stream scene prose generation from a beat.

        Args:
            beat: Structured beat from PlannerService.
            context: Assembled story context.
            content_mode: 'unrestricted' or 'safe'.

        Yields:
            Text chunks as they are generated.
        """
        model = self._get_model(content_mode)
        system = self._get_system_prompt(content_mode)
        prompt = self._format_beat_prompt(beat, context)

        logger.info("Streaming scene with model=%s, mode=%s", model, content_mode)

        async for chunk in self.ollama.generate_stream(
            prompt=prompt,
            system=system,
            model=model,
            keep_alive=self._keep_alive,
        ):
            yield chunk
