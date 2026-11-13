"""A tiny XML tree that serialises text as CDATA (ElementTree can't write CDATA)."""

from __future__ import annotations

from dataclasses import dataclass, field
from xml.sax.saxutils import quoteattr

_NEEDS_CDATA = ("<", ">", "&")


@dataclass
class Node:
    """An XML element. ``text=None`` with no children is written as an empty element (``<x/>``)."""

    tag: str
    attrs: dict[str, str] = field(default_factory=dict)
    text: str | None = None
    children: list[Node] = field(default_factory=list)
    raw: str | None = None
    """Pre-serialised XML written verbatim instead of this node (for raw question sources)."""

    def add(self, tag: str, text: str | None = None, **attrs: str) -> Node:
        child = Node(tag, dict(attrs), text)
        self.children.append(child)
        return child

    def add_text(self, tag: str, text: str, **attrs: str) -> Node:
        """Add ``<tag attrs><text>…</text></tag>``, Moodle's usual shape for a text field."""
        child = self.add(tag, **attrs)
        child.add("text", text)
        return child


def serialize(node: Node, level: int = 0) -> str:
    indent = "  " * level
    if node.raw is not None:
        return indent + node.raw.strip() + "\n"
    attrs = "".join(f" {name}={quoteattr(value)}" for name, value in node.attrs.items())
    if node.children:
        inner = "".join(serialize(child, level + 1) for child in node.children)
        return f"{indent}<{node.tag}{attrs}>\n{inner}{indent}</{node.tag}>\n"
    if node.text is None:
        return f"{indent}<{node.tag}{attrs}/>\n"
    return f"{indent}<{node.tag}{attrs}>{_text(node.text)}</{node.tag}>\n"


def _text(text: str) -> str:
    if not any(char in text for char in _NEEDS_CDATA):
        return text
    return "<![CDATA[" + text.replace("]]>", "]]]]><![CDATA[>") + "]]>"
