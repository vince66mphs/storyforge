"""Shared text-cleaning utilities for model output."""

import re

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


def clean_model_output(text: str) -> str:
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
        if _CUTOFF_PATTERNS.match(stripped):
            # A lone "---" inside prose is legitimate (section break)
            # Only treat it as cutoff if ANY remaining line contains meta-commentary
            if stripped.startswith("---"):
                remaining_lines = [
                    l.strip() for l in lines[i + 1:] if l.strip()
                ]
                if not remaining_lines or any(
                    _CUTOFF_PATTERNS.match(l)
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
