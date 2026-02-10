"""Tests for PlannerService — mocked OllamaService."""

import json
from unittest.mock import AsyncMock, patch

import pytest

from app.services.planner_service import FALLBACK_BEAT, PlannerService


@pytest.fixture
def svc():
    service = PlannerService()
    service.ollama = AsyncMock()
    return service


class TestParseBeat:
    def test_valid_json(self, svc):
        raw = json.dumps({
            "setting": "castle",
            "characters_present": ["Alice"],
            "key_events": ["Enter castle"],
            "emotional_tone": "tense",
            "continuity_notes": "",
            "continuity_warnings": [],
        })
        result = svc._parse_beat(raw)
        assert result["setting"] == "castle"

    def test_json_with_markdown_fences(self, svc):
        raw = '```json\n{"setting": "forest"}\n```'
        result = svc._parse_beat(raw)
        assert result["setting"] == "forest"

    def test_json_embedded_in_text(self, svc):
        raw = 'Here is the plan:\n{"setting": "cave", "key_events": ["explore"]}\nDone!'
        result = svc._parse_beat(raw)
        assert result["setting"] == "cave"

    def test_invalid_json_returns_fallback(self, svc):
        raw = "This is not JSON at all"
        result = svc._parse_beat(raw)
        assert result == FALLBACK_BEAT

    def test_missing_fields_get_defaults(self, svc):
        raw = json.dumps({"setting": "beach"})
        result = svc._parse_beat(raw)
        assert result["setting"] == "beach"
        assert result["characters_present"] == []
        assert result["key_events"] == []


class TestPlanBeat:
    async def test_successful_plan(self, svc):
        svc.ollama.generate.return_value = json.dumps({
            "setting": "forest",
            "characters_present": ["Alice"],
            "key_events": ["Walk through forest"],
            "emotional_tone": "mysterious",
            "continuity_notes": "",
            "continuity_warnings": [],
        })

        result = await svc.plan_beat("context", "Go to the forest")
        assert result["setting"] == "forest"
        svc.ollama.generate.assert_called_once()

    async def test_ollama_failure_returns_fallback(self, svc):
        svc.ollama.generate.side_effect = RuntimeError("connection lost")

        result = await svc.plan_beat("context", "Go somewhere")
        assert "Planner error" in result["continuity_warnings"][0]

    async def test_unknown_characters_warned(self, svc):
        svc.ollama.generate.return_value = json.dumps({
            "setting": "tavern",
            "characters_present": ["Alice", "UnknownGuy"],
            "key_events": ["Meet at tavern"],
            "emotional_tone": "lively",
            "continuity_notes": "",
            "continuity_warnings": [],
        })

        entities = [{"name": "Alice", "type": "character", "description": "Hero"}]
        result = await svc.plan_beat("ctx", "Go to tavern", entities)
        warnings = result["continuity_warnings"]
        assert any("UnknownGuy" in w for w in warnings)

    async def test_world_bible_included_in_prompt(self, svc):
        svc.ollama.generate.return_value = json.dumps({
            "setting": "town",
            "characters_present": [],
            "key_events": [],
            "emotional_tone": "",
            "continuity_notes": "",
            "continuity_warnings": [],
        })

        entities = [{"name": "Bob", "type": "character", "description": "A knight"}]
        await svc.plan_beat("ctx", "Go to town", entities)
        prompt = svc.ollama.generate.call_args.kwargs["prompt"]
        assert "Bob" in prompt
        assert "knight" in prompt
