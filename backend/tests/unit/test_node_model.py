"""Tests for Node model properties."""

import uuid

from app.models.node import Node


class TestNodeProperties:
    def _make_node(self, metadata_=None):
        return Node(
            story_id=uuid.uuid4(),
            content="Test",
            node_type="scene",
            metadata_=metadata_,
        )

    def test_beat_property_with_beat(self):
        beat = {"setting": "forest", "characters_present": ["Alice"]}
        node = self._make_node(metadata_={"beat": beat})
        assert node.beat == beat

    def test_beat_property_none_metadata(self):
        node = self._make_node(metadata_=None)
        assert node.beat is None

    def test_beat_property_no_beat_key(self):
        node = self._make_node(metadata_={"other": "data"})
        assert node.beat is None

    def test_illustration_path_present(self):
        node = self._make_node(metadata_={"illustration_path": "img_001.png"})
        assert node.illustration_path == "img_001.png"

    def test_illustration_path_absent(self):
        node = self._make_node(metadata_=None)
        assert node.illustration_path is None

    def test_continuity_warnings_present(self):
        node = self._make_node(
            metadata_={"continuity_warnings": ["Name mismatch"]}
        )
        assert node.continuity_warnings == ["Name mismatch"]

    def test_continuity_warnings_empty(self):
        node = self._make_node(metadata_={})
        assert node.continuity_warnings == []

    def test_continuity_warnings_none_metadata(self):
        node = self._make_node(metadata_=None)
        assert node.continuity_warnings == []

    def test_repr(self):
        node = self._make_node()
        r = repr(node)
        assert "Node" in r
        assert "scene" in r
