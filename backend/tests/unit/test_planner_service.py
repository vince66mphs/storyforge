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

    async def test_unknown_characters_structured_data(self, svc):
        svc.ollama.generate.return_value = json.dumps({
            "setting": "dark tavern",
            "characters_present": ["Alice", "Gareth", "Nyla"],
            "key_events": ["Gareth challenges the group", "Nyla serves drinks"],
            "emotional_tone": "tense",
            "continuity_notes": "",
            "continuity_warnings": [],
        })

        entities = [{"name": "Alice", "type": "character", "description": "Hero"}]
        result = await svc.plan_beat("ctx", "Go to tavern", entities)

        assert "unknown_characters" in result
        uc = result["unknown_characters"]
        assert len(uc) == 2
        names = {c["name"] for c in uc}
        assert names == {"Gareth", "Nyla"}
        # Each should have structured fields
        for c in uc:
            assert c["entity_type"] == "character"
            assert c["description"]  # non-empty
            assert c["base_prompt"]  # non-empty
            assert c["name"] in c["base_prompt"]

    async def test_no_unknown_characters_when_all_known(self, svc):
        svc.ollama.generate.return_value = json.dumps({
            "setting": "castle",
            "characters_present": ["Alice"],
            "key_events": ["Alice enters"],
            "emotional_tone": "calm",
            "continuity_notes": "",
            "continuity_warnings": [],
        })

        entities = [{"name": "Alice", "type": "character", "description": "Hero"}]
        result = await svc.plan_beat("ctx", "Go home", entities)
        assert "unknown_characters" not in result

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


class TestCheckContinuity:
    async def test_returns_parsed_issues(self, svc):
        svc.ollama.generate.return_value = json.dumps([
            {"scene": 2, "issue": "Jake was driving in scene 1 but passenger in scene 2", "severity": "error"},
            {"scene": 3, "issue": "Sun sets twice", "severity": "warning"},
        ])
        scenes = [
            {"number": 1, "content": "Jake drove down the highway."},
            {"number": 2, "content": "Jake sat in the passenger seat."},
            {"number": 3, "content": "The sun set again."},
        ]
        issues = await svc.check_continuity(scenes, [])
        assert len(issues) == 2
        assert issues[0]["scene"] == 2
        assert issues[0]["severity"] == "error"
        assert issues[1]["scene"] == 3

    async def test_returns_empty_list_when_clean(self, svc):
        svc.ollama.generate.return_value = "[]"
        scenes = [{"number": 1, "content": "A normal scene."}]
        issues = await svc.check_continuity(scenes, [])
        assert issues == []

    async def test_handles_markdown_fences(self, svc):
        svc.ollama.generate.return_value = '```json\n[{"scene": 1, "issue": "test", "severity": "warning"}]\n```'
        scenes = [{"number": 1, "content": "Test."}]
        issues = await svc.check_continuity(scenes, [])
        assert len(issues) == 1
        assert issues[0]["issue"] == "test"

    async def test_fallback_on_invalid_json(self, svc):
        svc.ollama.generate.return_value = "This is not JSON at all"
        scenes = [{"number": 1, "content": "Test."}]
        issues = await svc.check_continuity(scenes, [])
        assert len(issues) == 1
        assert "Failed to parse" in issues[0]["issue"]

    async def test_fallback_on_ollama_failure(self, svc):
        svc.ollama.generate.side_effect = RuntimeError("connection lost")
        scenes = [{"number": 1, "content": "Test."}]
        issues = await svc.check_continuity(scenes, [])
        assert len(issues) == 1
        assert "failed" in issues[0]["issue"].lower()

    async def test_includes_world_bible_in_prompt(self, svc):
        svc.ollama.generate.return_value = "[]"
        scenes = [{"number": 1, "content": "Jake walked."}]
        wb = [{"name": "Jake", "type": "character", "description": "A tall man"}]
        await svc.check_continuity(scenes, wb)
        prompt = svc.ollama.generate.call_args.kwargs["prompt"]
        assert "Jake" in prompt
        assert "tall man" in prompt


class TestParseContinuity:
    def test_valid_array(self, svc):
        raw = json.dumps([{"scene": 1, "issue": "test", "severity": "warning"}])
        result = svc._parse_continuity(raw)
        assert len(result) == 1

    def test_missing_severity_defaults_to_warning(self, svc):
        raw = json.dumps([{"scene": 1, "issue": "test"}])
        result = svc._parse_continuity(raw)
        assert result[0]["severity"] == "warning"

    def test_non_list_returns_error(self, svc):
        raw = json.dumps({"scene": 1, "issue": "test"})
        result = svc._parse_continuity(raw)
        assert len(result) == 1
        assert "Unexpected" in result[0]["issue"]

    def test_extracts_array_from_text(self, svc):
        raw = 'Here are the issues: [{"scene": 1, "issue": "test"}] Done!'
        result = svc._parse_continuity(raw)
        assert len(result) == 1
