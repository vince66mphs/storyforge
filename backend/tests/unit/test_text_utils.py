"""Tests for clean_model_output() — extracted text cleanup utility."""

from app.services.text_utils import clean_model_output


class TestCleanModelOutput:
    """Tests for the clean_model_output function."""

    def test_strips_let_me_know(self):
        text = "The car sped down the highway.\n\nLet me know if you would like me to continue."
        assert clean_model_output(text) == "The car sped down the highway."

    def test_strips_world_bible_block(self):
        text = (
            "Rain hammered the windshield.\n\n"
            "[WORLD BIBLE]\nCharacter: Jake\nRole: Driver"
        )
        assert clean_model_output(text) == "Rain hammered the windshield."

    def test_strips_scene_plan_dump(self):
        text = (
            "She glanced at the rearview mirror.\n\n"
            "Scene plan:\n  Setting: Highway at dusk\n  Characters: Jake, Mia"
        )
        assert clean_model_output(text) == "She glanced at the rearview mirror."

    def test_strips_separator_then_meta(self):
        text = (
            "The city lights flickered below.\n\n"
            "---\n\n"
            "Let me know if you'd like me to continue with the next scene."
        )
        assert clean_model_output(text) == "The city lights flickered below."

    def test_strips_ill_provide(self):
        text = "Jake floored the gas pedal.\n\nI'll provide the next scene when you're ready."
        assert clean_model_output(text) == "Jake floored the gas pedal."

    def test_strips_continue_with(self):
        text = "The door slammed shut.\n\nContinue with chapter 3?"
        assert clean_model_output(text) == "The door slammed shut."

    def test_strips_would_you_like(self):
        text = "Mia checked her phone.\n\nWould you like me to continue?"
        assert clean_model_output(text) == "Mia checked her phone."

    def test_strips_feel_free(self):
        text = "The engine roared to life.\n\nFeel free to direct the story."
        assert clean_model_output(text) == "The engine roared to life."

    def test_preserves_clean_prose(self):
        text = "The forest was dark and silent. An owl hooted in the distance.\n\nJake pressed on."
        assert clean_model_output(text) == text

    def test_preserves_legitimate_horizontal_rule(self):
        text = (
            "Part one ended.\n\n"
            "---\n\n"
            "Part two began with a crash."
        )
        # Legitimate --- followed by more prose should be preserved
        assert clean_model_output(text) == text

    def test_strips_trailing_whitespace(self):
        text = "The rain stopped.   \n\n  "
        assert clean_model_output(text) == "The rain stopped."

    def test_empty_string(self):
        assert clean_model_output("") == ""

    def test_strips_separator_then_empty(self):
        text = "The end.\n\n---\n\n"
        assert clean_model_output(text) == "The end."

    def test_strips_separator_then_editing_notes(self):
        text = (
            "The sedan vanished into the night.\n\n"
            "---\n\n"
            "I made some changes and suggestions:\n\n"
            "*   I changed some words for flow.\n"
            "*   I rewrote sentences for tension.\n\n"
            "Let me know if you need further assistance!"
        )
        assert clean_model_output(text) == "The sedan vanished into the night."

    def test_strips_i_made_some(self):
        text = "The door creaked open.\n\nI made some adjustments to the pacing above."
        assert clean_model_output(text) == "The door creaked open."

    def test_strips_here_are_some(self):
        text = "She ran.\n\nHere are some notes on the scene:"
        assert clean_model_output(text) == "She ran."

    def test_strips_parenthetical_note(self):
        text = (
            "The sedan surged forward.\n\n"
            "---\n\n"
            "(Note: I wrote this scene in prose form as requested. "
            "Let me know if you have any further requests!)"
        )
        assert clean_model_output(text) == "The sedan surged forward."
