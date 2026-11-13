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
from dataclasses import dataclass, field
from html.parser import HTMLParser
from urllib.parse import quote, unquote

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


# --- HTML → Markdown -------------------------------------------------------------------------

ImagePath = Callable[[str], str]
"""Maps an image ``src`` from HTML to the path written into the Markdown."""

_VOID = frozenset(
    {"area", "base", "br", "col", "embed", "hr", "img", "input", "link", "meta", "wbr"}
)
_PLUGINFILE = "@@PLUGINFILE@@/"


@dataclass
class _Element:
    tag: str
    attrs: dict[str, str]
    children: list[_Element | str] = field(default_factory=list)


class _TreeBuilder(HTMLParser):
    """Builds a small tree and remembers where each top-level node starts and ends."""

    def __init__(self, source: str) -> None:
        super().__init__(convert_charrefs=True)
        self.root = _Element("", {})
        self.stack = [self.root]
        self.top_level: list[tuple[int, int]] = []
        self._line_starts = [0]
        for index, char in enumerate(source):
            if char == "\n":
                self._line_starts.append(index + 1)
        self._source = source
        self._top_start: int | None = None

    def _offset(self) -> int:
        line, column = self.getpos()
        return self._line_starts[line - 1] + column

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        start = self._offset()
        element = _Element(tag, {name: value or "" for name, value in attrs})
        self.stack[-1].children.append(element)
        if len(self.stack) == 1:
            self._top_start = start
        if tag in _VOID:
            if len(self.stack) == 1:
                end = self._source.index(">", start) + 1
                self.top_level.append((start, end))
        else:
            self.stack.append(element)

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        start = self._offset()
        self.stack[-1].children.append(_Element(tag, {n: v or "" for n, v in attrs}))
        if len(self.stack) == 1:
            self.top_level.append((start, self._source.index(">", start) + 1))

    def handle_endtag(self, tag: str) -> None:
        if len(self.stack) > 1 and self.stack[-1].tag == tag:
            self.stack.pop()
            if len(self.stack) == 1 and self._top_start is not None:
                end = self._source.index(">", self._offset()) + 1
                self.top_level.append((self._top_start, end))
                self._top_start = None

    def handle_data(self, data: str) -> None:
        self.stack[-1].children.append(data)
        if len(self.stack) == 1 and data.strip():
            start = self._offset()
            end = self._source.find("<", start)
            self.top_level.append((start, end if end >= 0 else len(self._source)))


def to_markdown(html_text: str, *, pre_style: str, image_path: ImagePath = str) -> str:
    """Convert HTML to the Markdown subset where rendering it back gives the same HTML;
    everything else is kept as raw HTML."""
    builder = _TreeBuilder(html_text)
    builder.feed(html_text)
    builder.close()
    if len(builder.stack) != 1:
        return _raw(html_text.strip())
    blocks = [html_text[start:end] for start, end in builder.top_level]
    return "\n\n".join(_block_to_markdown(block, pre_style, image_path) for block in blocks)


def same_html(first: str, second: str) -> bool:
    """Whether two HTML fragments have the same tags, attributes and (decoded) text."""
    return _tokens(first) == _tokens(second)


def _block_to_markdown(block: str, pre_style: str, image_path: ImagePath) -> str:
    builder = _TreeBuilder(block)
    builder.feed(block)
    builder.close()
    nodes = builder.root.children
    sources: dict[str, str] = {}

    def to_path(src: str) -> str:
        path = image_path(src)
        sources[path] = src
        return path

    candidate: str | None = None
    if len(nodes) == 1 and isinstance(nodes[0], _Element):
        candidate = _element_to_markdown(nodes[0], pre_style, to_path)
    if candidate is not None:
        rendered = render(candidate, pre_style=pre_style, image_src=lambda p: sources.get(p, p))
        if same_html(rendered, block):
            return candidate
    return _raw(block)


def _raw(block: str) -> str:
    plain = block.startswith("<") and "\n\n" not in block and "\n```" not in block
    return block if plain else f"```{RAW_HTML_INFO}\n{block}\n```"


def _element_to_markdown(element: _Element, pre_style: str, image_path: ImagePath) -> str | None:
    tag = element.tag
    if tag == "p":
        return _inline(element.children, image_path)
    if tag == "pre" and element.attrs.get("style") == pre_style:
        if any(isinstance(child, _Element) for child in element.children):
            return None
        css_class = element.attrs.get("class", "")
        info = css_class.removeprefix("language-") if css_class.startswith("language-") else ""
        if set(element.attrs) - {"style", "class"} or (css_class and not info):
            return None
        return f"```{info}\n{''.join(str(c) for c in element.children)}\n```"
    if tag in {"h1", "h2", "h3", "h4", "h5", "h6"} and not element.attrs:
        text = _inline(element.children, image_path)
        return None if text is None else f"{'#' * int(tag[1])} {text}"
    if tag in {"ul", "ol"} and not element.attrs:
        items: list[str] = []
        for number, child in enumerate(element.children, 1):
            if not isinstance(child, _Element) or child.tag != "li" or child.attrs:
                return None
            text = _inline(child.children, image_path)
            if text is None:
                return None
            marker = "-" if tag == "ul" else f"{number}."
            items.append(f"{marker} {text.replace(chr(10), chr(10) + '  ')}")
        return "\n".join(items)
    return None


def _inline(children: list[_Element | str], image_path: ImagePath) -> str | None:
    out: list[str] = []
    for child in children:
        if isinstance(child, str):
            out.append(child)
            continue
        if (
            child.tag == "code"
            and not child.attrs
            and _only_text(child)
            and "`" not in _text(child)
        ):
            out.append(f"`{_text(child)}`")
        elif child.tag in {"strong", "em"} and not child.attrs:
            inner = _inline(child.children, image_path)
            if inner is None:
                return None
            mark = "**" if child.tag == "strong" else "*"
            out.append(f"{mark}{inner}{mark}")
        elif child.tag == "a" and set(child.attrs) == {"href"}:
            inner = _inline(child.children, image_path)
            if inner is None:
                return None
            out.append(f"[{inner}]({child.attrs['href']})")
        elif child.tag == "img" and set(child.attrs) <= {"src", "alt"} and "src" in child.attrs:
            out.append(f"![{child.attrs.get('alt', '')}]({image_path(child.attrs['src'])})")
        else:
            return None
    return "".join(out)


def _only_text(element: _Element) -> bool:
    return all(isinstance(child, str) for child in element.children)


def _text(element: _Element) -> str:
    return "".join(child for child in element.children if isinstance(child, str))


class _Tokenizer(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tokens: list[tuple[str, ...]] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        flat = tuple(f"{name}={value or ''}" for name, value in sorted(attrs))
        self.tokens.append(("start", tag, *flat))

    def handle_startendtag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        self.handle_starttag(tag, attrs)

    def handle_endtag(self, tag: str) -> None:
        self.tokens.append(("end", tag))

    def handle_data(self, data: str) -> None:
        if self.tokens and self.tokens[-1][0] == "text":
            self.tokens[-1] = ("text", self.tokens[-1][1] + data)
        else:
            self.tokens.append(("text", data))


def _tokens(fragment: str) -> list[tuple[str, ...]]:
    tokenizer = _Tokenizer()
    tokenizer.feed(fragment)
    tokenizer.close()
    return tokenizer.tokens


def plugin_file_name(src: str) -> str | None:
    """The file name of a ``@@PLUGINFILE@@/…`` reference, else ``None``."""
    return unquote(src[len(_PLUGINFILE) :]) if src.startswith(_PLUGINFILE) else None


def plugin_file_src(name: str) -> str:
    return _PLUGINFILE + quote(name)


def image_paths(markdown: str) -> list[str]:
    """Paths of the Markdown images (``![alt](path)``) in a text."""
    return [match.group("src") for match in _INLINE.finditer(markdown) if match.group("image")]


def is_external(src: str) -> bool:
    return bool(re.match(r"^[a-z][a-z0-9+.-]*:", src, re.IGNORECASE))
