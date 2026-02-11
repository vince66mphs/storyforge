"""Unit tests for EPUB export service."""

import zipfile
from io import BytesIO
from pathlib import Path

import pytest

from app.services.epub_service import build_epub


class TestBuildEpub:
    def test_basic_scenes_only(self, tmp_path: Path):
        """EPUB with scenes and no images returns valid bytes."""
        scenes = [
            {"content": "The rain fell hard on the city streets."},
            {"content": "She opened the door to find no one there."},
        ]
        result = build_epub(
            title="Test Story",
            genre="mystery",
            scenes=scenes,
            entities=[],
            static_dir=str(tmp_path),
        )
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_output_is_valid_zip(self, tmp_path: Path):
        """EPUB files must be valid ZIP archives per the spec."""
        scenes = [{"content": "A single scene."}]
        result = build_epub(
            title="Zip Test",
            genre=None,
            scenes=scenes,
            entities=[],
            static_dir=str(tmp_path),
        )
        buf = BytesIO(result)
        assert zipfile.is_zipfile(buf)

    def test_contains_expected_files(self, tmp_path: Path):
        """EPUB should contain title, chapter, and nav files."""
        scenes = [
            {"content": "Chapter one content."},
            {"content": "Chapter two content."},
        ]
        result = build_epub(
            title="Structure Test",
            genre="fantasy",
            scenes=scenes,
            entities=[],
            static_dir=str(tmp_path),
        )
        buf = BytesIO(result)
        with zipfile.ZipFile(buf) as zf:
            names = zf.namelist()
            # Should have title page, two chapters, nav, and ncx
            assert any("title.xhtml" in n for n in names)
            assert any("chapter_001.xhtml" in n for n in names)
            assert any("chapter_002.xhtml" in n for n in names)

    def test_with_entities(self, tmp_path: Path):
        """EPUB with entities includes world bible chapter."""
        scenes = [{"content": "Some scene content."}]
        entities = [
            {
                "name": "Elara",
                "entity_type": "character",
                "description": "A brave warrior.",
                "reference_image_path": None,
            },
            {
                "name": "Dark Forest",
                "entity_type": "location",
                "description": "An ancient forest.",
                "reference_image_path": None,
            },
        ]
        result = build_epub(
            title="Entity Test",
            genre="fantasy",
            scenes=scenes,
            entities=entities,
            static_dir=str(tmp_path),
        )
        buf = BytesIO(result)
        with zipfile.ZipFile(buf) as zf:
            names = zf.namelist()
            assert any("world_bible.xhtml" in n for n in names)

    def test_missing_image_handled_gracefully(self, tmp_path: Path):
        """Missing image files should not cause errors."""
        scenes = [
            {
                "content": "A scene with a missing illustration.",
                "illustration_path": "nonexistent_image.png",
            },
        ]
        entities = [
            {
                "name": "Ghost",
                "entity_type": "character",
                "description": "A spectral figure.",
                "reference_image_path": "also_missing.png",
            },
        ]
        # Should not raise
        result = build_epub(
            title="Missing Images",
            genre=None,
            scenes=scenes,
            entities=entities,
            static_dir=str(tmp_path),
        )
        assert isinstance(result, bytes)
        assert len(result) > 0

    def test_embedded_image(self, tmp_path: Path):
        """Images that exist on disk should be embedded in the EPUB."""
        images_dir = tmp_path / "images"
        images_dir.mkdir()
        (images_dir / "scene1.png").write_bytes(b"\x89PNG fake image data")

        scenes = [
            {"content": "A scene with an illustration.", "illustration_path": "scene1.png"},
        ]
        result = build_epub(
            title="Image Test",
            genre=None,
            scenes=scenes,
            entities=[],
            static_dir=str(tmp_path),
        )
        buf = BytesIO(result)
        with zipfile.ZipFile(buf) as zf:
            names = zf.namelist()
            assert any("scene1.png" in n for n in names)

    def test_no_genre(self, tmp_path: Path):
        """EPUB without genre should still build successfully."""
        scenes = [{"content": "Content without genre."}]
        result = build_epub(
            title="No Genre",
            genre=None,
            scenes=scenes,
            entities=[],
            static_dir=str(tmp_path),
        )
        assert isinstance(result, bytes)

    def test_html_escaping(self, tmp_path: Path):
        """Special characters in content should be escaped."""
        scenes = [{"content": 'He said "x < y & z > w" loudly.'}]
        result = build_epub(
            title="Escape <Test>",
            genre=None,
            scenes=scenes,
            entities=[],
            static_dir=str(tmp_path),
        )
        buf = BytesIO(result)
        with zipfile.ZipFile(buf) as zf:
            for name in zf.namelist():
                if "chapter_001" in name:
                    content = zf.read(name).decode("utf-8")
                    assert "&lt;" in content
                    assert "&amp;" in content
                    break
