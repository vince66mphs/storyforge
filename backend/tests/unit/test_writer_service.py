"""Tests for WriterService — mocked OllamaService."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from app.services.writer_service import (
    WRITER_SYSTEM_SAFE,
    WRITER_SYSTEM_UNRESTRICTED,
    WriterService,
)
from tests.factories import make_beat


@pytest.fixture
def svc():
    service = WriterService()
    service.ollama = AsyncMock()
    service.ollama.generate.return_value = "The forest was dark and silent."
    return service


class TestModelSelection:
    def test_unrestricted_model(self, svc):
        model = svc._get_model("unrestricted")
        assert model == svc._writer_models["unrestricted"]

    def test_safe_model(self, svc):
        model = svc._get_model("safe")
        assert model == svc._writer_models["safe"]

    def test_unknown_mode_defaults_to_unrestricted(self, svc):
        model = svc._get_model("unknown")
        assert model == svc._writer_models["unrestricted"]


class TestSystemPrompt:
    def test_unrestricted_prompt(self, svc):
        prompt = svc._get_system_prompt("unrestricted")
        assert prompt == WRITER_SYSTEM_UNRESTRICTED

    def test_safe_prompt(self, svc):
        prompt = svc._get_system_prompt("safe")
        assert prompt == WRITER_SYSTEM_SAFE


class TestFormatBeatPrompt:
    def test_includes_beat_fields(self, svc):
        beat = make_beat(setting="castle", characters=["Alice", "Bob"])
        result = svc._format_beat_prompt(beat, "context text")
        assert "castle" in result
        assert "Alice" in result
        assert "Bob" in result
        assert "context text" in result

    def test_includes_events_and_tone(self, svc):
        beat = make_beat(events=["Fight dragon"], tone="epic")
        result = svc._format_beat_prompt(beat, "ctx")
        assert "Fight dragon" in result
        assert "epic" in result


class TestWriteScene:
    async def test_generates_prose(self, svc):
        beat = make_beat()
        result = await svc.write_scene(beat, "context", "unrestricted")
        assert result == "The forest was dark and silent."
        svc.ollama.generate.assert_called_once()

    async def test_passes_correct_model_for_safe(self, svc):
        beat = make_beat()
        await svc.write_scene(beat, "context", "safe")
        call_kwargs = svc.ollama.generate.call_args.kwargs
        assert call_kwargs["model"] == svc._writer_models["safe"]
        assert call_kwargs["system"] == WRITER_SYSTEM_SAFE


class TestCleanOutput:
    """Tests for WriterService._clean_output()."""

    def test_strips_let_me_know(self):
        text = "The car sped down the highway.\n\nLet me know if you would like me to continue."
        assert WriterService._clean_output(text) == "The car sped down the highway."

    def test_strips_world_bible_block(self):
        text = (
            "Rain hammered the windshield.\n\n"
            "[WORLD BIBLE]\nCharacter: Jake\nRole: Driver"
        )
        assert WriterService._clean_output(text) == "Rain hammered the windshield."

    def test_strips_scene_plan_dump(self):
        text = (
            "She glanced at the rearview mirror.\n\n"
            "Scene plan:\n  Setting: Highway at dusk\n  Characters: Jake, Mia"
        )
        assert WriterService._clean_output(text) == "She glanced at the rearview mirror."

    def test_strips_separator_then_meta(self):
        text = (
            "The city lights flickered below.\n\n"
            "---\n\n"
            "Let me know if you'd like me to continue with the next scene."
        )
        assert WriterService._clean_output(text) == "The city lights flickered below."

    def test_strips_ill_provide(self):
        text = "Jake floored the gas pedal.\n\nI'll provide the next scene when you're ready."
        assert WriterService._clean_output(text) == "Jake floored the gas pedal."

    def test_strips_continue_with(self):
        text = "The door slammed shut.\n\nContinue with chapter 3?"
        assert WriterService._clean_output(text) == "The door slammed shut."

    def test_strips_would_you_like(self):
        text = "Mia checked her phone.\n\nWould you like me to continue?"
        assert WriterService._clean_output(text) == "Mia checked her phone."

    def test_strips_feel_free(self):
        text = "The engine roared to life.\n\nFeel free to direct the story."
        assert WriterService._clean_output(text) == "The engine roared to life."

    def test_preserves_clean_prose(self):
        text = "The forest was dark and silent. An owl hooted in the distance.\n\nJake pressed on."
        assert WriterService._clean_output(text) == text

    def test_preserves_legitimate_horizontal_rule(self):
        text = (
            "Part one ended.\n\n"
            "---\n\n"
            "Part two began with a crash."
        )
        # Legitimate --- followed by more prose should be preserved
        assert WriterService._clean_output(text) == text

    def test_strips_trailing_whitespace(self):
        text = "The rain stopped.   \n\n  "
        assert WriterService._clean_output(text) == "The rain stopped."

    def test_empty_string(self):
        assert WriterService._clean_output("") == ""

    def test_strips_separator_then_empty(self):
        text = "The end.\n\n---\n\n"
        assert WriterService._clean_output(text) == "The end."


class TestWriteSceneStream:
    async def test_streams_chunks(self, svc):
        async def mock_stream(*args, **kwargs):
            yield "Hello "
            yield "world"

        svc.ollama.generate_stream = mock_stream

        beat = make_beat()
        chunks = []
        async for chunk in svc.write_scene_stream(beat, "ctx", "unrestricted"):
            chunks.append(chunk)
        assert chunks == ["Hello ", "world"]
