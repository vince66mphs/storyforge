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
