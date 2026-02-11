"""EPUB export service — builds an EPUB file from story data."""

import io
import mimetypes
from pathlib import Path

from ebooklib import epub


STYLESHEET = """\
body {
  font-family: Georgia, "Times New Roman", serif;
  line-height: 1.8;
  margin: 1em;
  color: #222;
}
h1 { text-align: center; margin: 2em 0 0.5em; }
h2 { margin: 1.5em 0 0.5em; }
h3 { margin: 1em 0 0.4em; }
p.genre { text-align: center; font-style: italic; color: #666; }
img { max-width: 100%; height: auto; display: block; margin: 1em auto; }
.entity-group { margin-bottom: 1.5em; }
hr { border: none; border-top: 1px solid #ccc; margin: 2em 0; }
"""

MEDIA_TYPES = {
    ".png": "image/png",
    ".jpg": "image/jpeg",
    ".jpeg": "image/jpeg",
    ".webp": "image/webp",
    ".gif": "image/gif",
}


def _media_type(filename: str) -> str:
    ext = Path(filename).suffix.lower()
    return MEDIA_TYPES.get(ext, mimetypes.guess_type(filename)[0] or "application/octet-stream")


def _add_image(book: epub.EpubBook, static_dir: str, filename: str) -> str | None:
    """Read an image from disk and add it to the EPUB. Returns the href or None."""
    image_path = Path(static_dir) / "images" / filename
    if not image_path.is_file():
        return None

    content = image_path.read_bytes()
    href = f"images/{filename}"
    img = epub.EpubImage()
    img.file_name = href
    img.media_type = _media_type(filename)
    img.content = content
    book.add_item(img)
    return href


def build_epub(
    title: str,
    genre: str | None,
    scenes: list[dict],
    entities: list[dict],
    static_dir: str,
) -> bytes:
    """Build an EPUB file and return its bytes.

    Args:
        title: Story title.
        genre: Optional genre string.
        scenes: List of dicts with keys: content, illustration_path (optional).
        entities: List of dicts with keys: name, entity_type, description,
                  reference_image_path (optional).
        static_dir: Path to the static files directory.

    Returns:
        EPUB file content as bytes.
    """
    book = epub.EpubBook()

    # Metadata
    book.set_identifier(f"storyforge-{title}")
    book.set_title(title)
    book.set_language("en")
    if genre:
        book.add_metadata("DC", "subject", genre)

    # Stylesheet
    css = epub.EpubItem(
        uid="style",
        file_name="style/default.css",
        media_type="text/css",
        content=STYLESHEET.encode("utf-8"),
    )
    book.add_item(css)

    spine: list = ["nav"]
    toc: list = []

    # ── Title page ──
    title_html = f"<h1>{_esc(title)}</h1>"
    if genre:
        title_html += f'<p class="genre">{_esc(genre)}</p>'

    title_ch = epub.EpubHtml(title="Title", file_name="title.xhtml", lang="en")
    title_ch.content = title_html.encode("utf-8")
    title_ch.add_item(css)
    book.add_item(title_ch)
    spine.append(title_ch)
    toc.append(title_ch)

    # ── World Bible chapter ──
    if entities:
        wb_parts = ["<h2>World Bible</h2>"]
        grouped: dict[str, list[dict]] = {}
        for e in entities:
            grouped.setdefault(e["entity_type"], []).append(e)

        type_labels = {"character": "Characters", "location": "Locations", "prop": "Props"}
        for etype in ["character", "location", "prop"]:
            group = grouped.get(etype, [])
            if not group:
                continue
            wb_parts.append(f'<div class="entity-group"><h3>{type_labels.get(etype, etype.title())}</h3>')
            for e in group:
                wb_parts.append(f"<h4>{_esc(e['name'])}</h4>")
                wb_parts.append(f"<p>{_esc(e['description'])}</p>")
                ref_img = e.get("reference_image_path")
                if ref_img:
                    href = _add_image(book, static_dir, ref_img)
                    if href:
                        wb_parts.append(f'<img src="{href}" alt="{_esc(e["name"])}" />')
            wb_parts.append("</div>")

        wb_ch = epub.EpubHtml(title="World Bible", file_name="world_bible.xhtml", lang="en")
        wb_ch.content = "\n".join(wb_parts).encode("utf-8")
        wb_ch.add_item(css)
        book.add_item(wb_ch)
        spine.append(wb_ch)
        toc.append(wb_ch)

    # ── Scene chapters ──
    for i, scene in enumerate(scenes, 1):
        parts = [f"<h2>Chapter {i}</h2>"]

        illust = scene.get("illustration_path")
        if illust:
            href = _add_image(book, static_dir, illust)
            if href:
                parts.append(f'<img src="{href}" alt="Chapter {i} illustration" />')

        # Convert content paragraphs
        for para in scene["content"].split("\n\n"):
            stripped = para.strip()
            if stripped:
                parts.append(f"<p>{_esc(stripped)}</p>")

        ch = epub.EpubHtml(
            title=f"Chapter {i}",
            file_name=f"chapter_{i:03d}.xhtml",
            lang="en",
        )
        ch.content = "\n".join(parts).encode("utf-8")
        ch.add_item(css)
        book.add_item(ch)
        spine.append(ch)
        toc.append(ch)

    # Finalize
    book.toc = toc
    book.add_item(epub.EpubNcx())
    book.add_item(epub.EpubNav())
    book.spine = spine

    # Write to bytes
    buf = io.BytesIO()
    epub.write_epub(buf, book)
    return buf.getvalue()


def _esc(text: str) -> str:
    """Escape HTML special characters."""
    return (
        text.replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
        .replace('"', "&quot;")
    )
