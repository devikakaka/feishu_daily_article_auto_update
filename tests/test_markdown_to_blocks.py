"""Unit tests for markdown_to_blocks module."""

from src.markdown_to_blocks import markdown_to_feishu_blocks


def test_heading1():
    """Test # heading → block_type 3 (heading1)."""
    blocks = markdown_to_feishu_blocks("# Heading 1")
    assert len(blocks) == 1
    assert blocks[0]["block_type"] == 3
    assert "heading1" in blocks[0]
    assert blocks[0]["heading1"]["elements"][0]["text_run"]["content"] == "Heading 1"


def test_heading2():
    """Test ## heading → block_type 4 (heading2)."""
    blocks = markdown_to_feishu_blocks("## Heading 2")
    assert len(blocks) == 1
    assert blocks[0]["block_type"] == 4
    assert "heading2" in blocks[0]


def test_heading3():
    """Test ### heading → block_type 5 (heading3)."""
    blocks = markdown_to_feishu_blocks("### Heading 3")
    assert len(blocks) == 1
    assert blocks[0]["block_type"] == 5
    assert "heading3" in blocks[0]


def test_paragraph():
    """Test plain text → block_type 2 (text)."""
    blocks = markdown_to_feishu_blocks("This is a paragraph.")
    assert len(blocks) == 1
    assert blocks[0]["block_type"] == 2
    assert "text" in blocks[0]


def test_bullet_list():
    """Test - item → block_type 12 (bullet)."""
    blocks = markdown_to_feishu_blocks("- Item 1\n- Item 2")
    assert len(blocks) == 2
    assert blocks[0]["block_type"] == 12
    assert "bullet" in blocks[0]


def test_ordered_list():
    """Test 1. item → block_type 13 (ordered)."""
    blocks = markdown_to_feishu_blocks("1. First\n2. Second")
    assert len(blocks) == 2
    assert blocks[0]["block_type"] == 13
    assert "ordered" in blocks[0]


def test_code_block():
    """Test fenced code block → block_type 14 (code)."""
    blocks = markdown_to_feishu_blocks("```python\nprint('hello')\n```")
    assert len(blocks) == 1
    assert blocks[0]["block_type"] == 14
    assert "code" in blocks[0]


def test_quote():
    """Test > quote → block_type 15 (quote)."""
    blocks = markdown_to_feishu_blocks("> This is a quote")
    assert len(blocks) == 1
    assert blocks[0]["block_type"] == 15
    assert "quote" in blocks[0]


def test_divider():
    """Test --- → block_type 22 (divider)."""
    blocks = markdown_to_feishu_blocks("---")
    assert len(blocks) == 1
    assert blocks[0]["block_type"] == 22
    assert "divider" in blocks[0]


def test_bold_inline():
    """Test **bold** text inline styling."""
    blocks = markdown_to_feishu_blocks("**Bold text**")
    assert len(blocks) == 1
    elements = blocks[0]["text"]["elements"]
    assert elements[0]["text_run"]["text_element_style"]["bold"] is True
    assert elements[0]["text_run"]["content"] == "Bold text"


def test_italic_inline():
    """Test *italic* text inline styling."""
    blocks = markdown_to_feishu_blocks("*Italic text*")
    assert len(blocks) == 1
    elements = blocks[0]["text"]["elements"]
    assert elements[0]["text_run"]["text_element_style"]["italic"] is True


def test_inline_code():
    """Test `code` inline styling."""
    blocks = markdown_to_feishu_blocks("`inline code`")
    assert len(blocks) == 1
    elements = blocks[0]["text"]["elements"]
    assert elements[0]["text_run"]["text_element_style"]["inline_code"] is True


def test_link_inline():
    """Test [text](url) inline styling."""
    blocks = markdown_to_feishu_blocks("[Link text](https://example.com)")
    assert len(blocks) == 1
    elements = blocks[0]["text"]["elements"]
    assert elements[0]["text_run"]["text_element_style"]["link"]["url"] == "https://example.com"


def test_mixed_inline():
    """Test mixed inline styles."""
    blocks = markdown_to_feishu_blocks("**Bold** and *italic* and `code`")
    assert len(blocks) == 1
    elements = blocks[0]["text"]["elements"]
    assert len(elements) == 5  # bold, " and ", italic, " and ", code


def test_blank_lines_skipped():
    """Test that blank lines are skipped."""
    blocks = markdown_to_feishu_blocks("# Heading\n\n\nParagraph\n\n")
    assert len(blocks) == 2


def test_complex_markdown():
    """Test a complex markdown document."""
    md = """# Title

This is a paragraph with **bold** and *italic*.

## Section 1

- Item 1
- Item 2

1. First
2. Second

> A quote

---

```
code block
```
"""
    blocks = markdown_to_feishu_blocks(md)
    assert len(blocks) == 10  # 1 heading + 1 paragraph + 1 heading + 2 bullets + 2 ordered + 1 quote + 1 divider + 1 code