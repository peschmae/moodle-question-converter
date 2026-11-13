"""Markdown ↔ HTML for question texts.

The converter supports a deliberately small Markdown subset so that both directions are exact:

- paragraphs, ``#`` headings, ``-``/``*`` and ``1.`` lists (one level)
- fenced code blocks, rendered as ``<pre>`` with the collection's code style; an info string
  becomes ``class="language-…"``
- raw HTML: a block starting with ``<`` is passed through; ```` ```{=html} ```` fences pass
  through anything, including blank lines
- inline: ```code```, ``**strong**``, ``*em*``, ``[link](url)``, ``![alt](image)``

Anything that can't be written in this subset is kept as raw HTML when converting back.
"""

from __future__ import annotations

import html
import re
from collections.abc import Callable

RAW_HTML_INFO = "{=html}"

_FENCE = re.compile(r"^```(.*)$")
_HEADING = re.compile(r"^(#{1,6}) (.*)$")
_BULLET = re.compile(r"^[-*] (.*)$")
_NUMBERED = re.compile(r"^\d+\. (.*)$")
_INLINE = re.compile(
    r"(?P<code>`(?P<code_text>[^`]+)`)"
    r"|(?P<image>!\[(?P<alt>[^\]]*)\]\((?P<src>[^)\s]+)\))"
    r"|(?P<link>\[(?P<label>[^\]\[]+)\]\((?P<href>[^)\s]+)\))"
    r"|(?P<strong>\*\*(?P<strong_text>.+?)\*\*)"
    r"|(?P<em>\*(?P<em_text>[^*\s][^*]*?)\*)"
)
_TAG_START = re.compile(r"<(?=[A-Za-z/!])")
_ENTITY = re.compile(r"&(?=#?\w+;)")

ImageSource = Callable[[str], str]
"""Maps an image path from the Markdown to the ``src`` written into HTML."""


def code_style(line_height: float | str) -> str:
    """The ``style`` of ``<pre>`` code blocks in Moodle."""
    return f"font-family: monospace; line-height: {line_height};"


def render(markdown: str, *, pre_style: str, image_src: ImageSource = str) -> str:
    """Render the Markdown subset to HTML; blocks are separated by line breaks."""
    return "\n".join(_render_block(block, pre_style, image_src) for block in split_blocks(markdown))


def render_inline(text: str, image_src: ImageSource = str) -> str:
    """Render inline Markdown (no paragraphs)."""
    out: list[str] = []
    position = 0
    for match in _INLINE.finditer(text):
        out.append(_escape_text(text[position : match.start()]))
        out.append(_render_inline_match(match, image_src))
        position = match.end()
    out.append(_escape_text(text[position:]))
    return "".join(out)


def split_blocks(markdown: str) -> list[list[str]]:
    """Split Markdown into blocks (lists of lines); fenced code keeps its blank lines."""
    blocks: list[list[str]] = []
    current: list[str] = []
    in_fence = False
    for line in markdown.strip("\n").split("\n"):
        if in_fence:
            current.append(line)
            if line.rstrip() == "```":
                blocks.append(current)
                current, in_fence = [], False
            continue
        if _FENCE.match(line):
            if current:
                blocks.append(current)
            current, in_fence = [line], True
            continue
        if not line.strip():
            if current:
                blocks.append(current)
                current = []
            continue
        current.append(line)
    if current:
        blocks.append(current)
    return blocks


def _render_block(lines: list[str], pre_style: str, image_src: ImageSource) -> str:
    first = lines[0]
    fence = _FENCE.match(first)
    if fence:
        info = fence.group(1).strip()
        body = "\n".join(lines[1:-1] if lines[-1].rstrip() == "```" else lines[1:])
        if info == RAW_HTML_INFO:
            return body
        css_class = f' class="language-{html.escape(info)}"' if info else ""
        return f'<pre style="{pre_style}"{css_class}>{html.escape(body, quote=False)}</pre>'
    if first.startswith("<"):
        return "\n".join(lines)
    heading = _HEADING.match(first)
    if heading and len(lines) == 1:
        level = len(heading.group(1))
        return f"<h{level}>{render_inline(heading.group(2), image_src)}</h{level}>"
    for pattern, tag in ((_BULLET, "ul"), (_NUMBERED, "ol")):
        if pattern.match(first):
            items = _list_items(lines, pattern)
            if items is not None:
                rendered = "".join(f"<li>{render_inline(item, image_src)}</li>" for item in items)
                return f"<{tag}>{rendered}</{tag}>"
    return f"<p>{render_inline(chr(10).join(lines), image_src)}</p>"


def _list_items(lines: list[str], pattern: re.Pattern[str]) -> list[str] | None:
    items: list[str] = []
    for line in lines:
        match = pattern.match(line)
        if match:
            items.append(match.group(1))
        elif items and line.startswith("  "):
            items[-1] += "\n" + line.strip()
        else:
            return None
    return items


def _render_inline_match(match: re.Match[str], image_src: ImageSource) -> str:
    if match.group("code"):
        return f"<code>{html.escape(match.group('code_text'), quote=False)}</code>"
    if match.group("image"):
        src = html.escape(image_src(match.group("src")))
        return f'<img src="{src}" alt="{html.escape(match.group("alt"))}">'
    if match.group("link"):
        label = render_inline(match.group("label"), image_src)
        return f'<a href="{html.escape(match.group("href"))}">{label}</a>'
    if match.group("strong"):
        return f"<strong>{render_inline(match.group('strong_text'), image_src)}</strong>"
    return f"<em>{render_inline(match.group('em_text'), image_src)}</em>"


def _escape_text(text: str) -> str:
    """Escape ``&`` and ``<`` unless they start an entity or an HTML tag (raw HTML is allowed)."""
    text = _ENTITY.sub("\0", text).replace("&", "&amp;").replace("\0", "&")
    parts = _TAG_START.split(text)
    return "<".join(part.replace("<", "&lt;") for part in parts)
