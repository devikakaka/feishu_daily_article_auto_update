"""Markdown to Feishu Docx Block format converter."""

import re
from typing import List, Dict


def markdown_to_feishu_blocks(md: str) -> List[Dict]:
    """
    Convert a markdown string into a list of Feishu docx block dicts.

    Feishu block types:
    - 2: text (paragraph)
    - 3: heading1
    - 4: heading2
    - 5: heading3
    - 12: bullet (unordered list)
    - 13: ordered (ordered list)
    - 14: code block
    - 15: quote
    - 22: divider (horizontal rule)
    """
    lines = md.split("\n")
    blocks = []
    i = 0

    while i < len(lines):
        line = lines[i]
        stripped = line.strip()

        # Blank line → skip
        if not stripped:
            i += 1
            continue

        # Headings (must check ### before ## before #)
        if stripped.startswith("### "):
            blocks.append(_heading(5, stripped[4:]))
        elif stripped.startswith("## "):
            blocks.append(_heading(4, stripped[3:]))
        elif stripped.startswith("# "):
            blocks.append(_heading(3, stripped[2:]))

        # Horizontal rule (---, ***, or ___)
        elif re.match(r"^-{3,}$", stripped) or re.match(r"^\*{3,}$", stripped) or re.match(r"^_{3,}$", stripped):
            blocks.append({"block_type": 22, "divider": {}})

        # Bullet list (- or *)
        elif re.match(r"^[\-\*] ", stripped):
            text = re.sub(r"^[\-\*] ", "", stripped)
            blocks.append(_block(12, "bullet", text))

        # Ordered list (1. 2. etc.)
        elif re.match(r"^\d+\. ", stripped):
            text = re.sub(r"^\d+\. ", "", stripped)
            blocks.append(_block(13, "ordered", text))

        # Fenced code block
        elif stripped.startswith("```"):
            code_lines = []
            i += 1
            while i < len(lines) and not lines[i].strip().startswith("```"):
                code_lines.append(lines[i])
                i += 1
            blocks.append(_code_block("\n".join(code_lines)))

        # Block quote
        elif stripped.startswith("> "):
            blocks.append(_block(15, "quote", stripped[2:]))

        # Regular paragraph
        else:
            blocks.append(_block(2, "text", stripped))

        i += 1

    return blocks


def _text_elements(text: str) -> List[Dict]:
    """Parse inline markdown formatting into Feishu text_run elements."""
    pattern = re.compile(
        r"(\*\*(.+?)\*\*"  # bold
        r"|\*(.+?)\*"  # italic
        r"|`(.+?)`"  # inline code
        r"|\[(.+?)\]\((.+?)\)"  # link
        r"|([^*`\[]+)"  # plain text
        r")"
    )
    elements = []
    for m in pattern.finditer(text):
        if m.group(2):  # bold
            elements.append(_run(m.group(2), {"bold": True}))
        elif m.group(3):  # italic
            elements.append(_run(m.group(3), {"italic": True}))
        elif m.group(4):  # inline code
            elements.append(_run(m.group(4), {"inline_code": True}))
        elif m.group(5):  # link
            elements.append(_run(m.group(5), {"link": {"url": m.group(6)}}))
        elif m.group(7):  # plain
            elements.append(_run(m.group(7), {}))

    return elements or [_run(text, {})]


def _run(content: str, style: Dict) -> Dict:
    """Create a text_run element."""
    return {"text_run": {"content": content, "text_element_style": style}}


def _block(block_type: int, key: str, text: str) -> Dict:
    """Create a standard block (text, bullet, ordered, quote)."""
    return {
        "block_type": block_type,
        key: {
            "elements": _text_elements(text),
            "style": {},
        },
    }


def _heading(level: int, text: str) -> Dict:
    """Create a heading block. block_type 3=heading1, 4=heading2, 5=heading3."""
    key = f"heading{level - 2}"
    return {
        "block_type": level,
        key: {
            "elements": _text_elements(text),
            "style": {},
        },
    }


def _code_block(code: str) -> Dict:
    """Create a code block."""
    return {
        "block_type": 14,
        "code": {
            "elements": [_run(code, {})],
            "style": {"language": 1},  # 1 = PlainText
        },
    }