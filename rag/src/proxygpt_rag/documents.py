from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from pathlib import Path
from uuid import NAMESPACE_URL, UUID, uuid5


_HEADING = re.compile(r"^(#{1,6})[ \t]+(.+?)\s*#*\s*$")
_WORD_BOUNDARY_MINIMUM = 1


@dataclass(frozen=True)
class Chunk:
    point_id: UUID
    source: str
    title: str
    heading: str
    chunk_index: int
    text: str
    document_sha256: str

    @property
    def citation(self) -> str:
        return f"{self.source}#chunk-{self.chunk_index:04d}"


def iter_markdown(root: Path) -> list[tuple[Path, str]]:
    if not root.exists():
        raise FileNotFoundError(f"Document source path does not exist: {root}")
    if not root.is_dir():
        raise NotADirectoryError(f"Document source path is not a directory: {root}")

    documents: list[tuple[Path, str]] = []
    for path in sorted(root.rglob("*.md")):
        if path.is_symlink() or any(part.startswith(".") for part in path.relative_to(root).parts):
            continue
        if path.is_file():
            documents.append((path, path.relative_to(root).as_posix()))

    return documents


def chunk_markdown(
    text: str,
    *,
    source: str,
    title: str,
    max_chars: int,
    overlap: int,
) -> list[Chunk]:
    if max_chars <= 0:
        raise ValueError("max_chars must be greater than zero.")
    if overlap < 0 or overlap >= max_chars:
        raise ValueError("overlap must be between 0 and max_chars - 1.")

    normalized = text.replace("\r\n", "\n").replace("\r", "\n").strip()
    if not normalized:
        return []

    digest = hashlib.sha256(normalized.encode("utf-8")).hexdigest()
    sections = _markdown_sections(normalized, title)
    chunks: list[Chunk] = []

    for heading, section_text in sections:
        for piece in _split_text(section_text, max_chars=max_chars, overlap=overlap):
            index = len(chunks) + 1
            chunks.append(
                Chunk(
                    point_id=uuid5(NAMESPACE_URL, f"proxygpt-rag:{source}:{index}"),
                    source=source,
                    title=title,
                    heading=heading,
                    chunk_index=index,
                    text=piece,
                    document_sha256=digest,
                )
            )

    return chunks


def _markdown_sections(text: str, fallback_title: str) -> list[tuple[str, str]]:
    sections: list[tuple[str, str]] = []
    heading_stack: list[tuple[int, str]] = []
    current_heading = fallback_title
    current_lines: list[str] = []

    for line in text.splitlines():
        match = _HEADING.match(line)
        if match:
            body = "\n".join(current_lines).strip()
            if body:
                sections.append((current_heading, body))

            level = len(match.group(1))
            heading_text = match.group(2).strip()
            heading_stack = [(depth, name) for depth, name in heading_stack if depth < level]
            heading_stack.append((level, heading_text))
            current_heading = " > ".join(name for _, name in heading_stack)
            current_lines = [line]
        else:
            current_lines.append(line)

    body = "\n".join(current_lines).strip()
    if body:
        sections.append((current_heading, body))

    return sections


def _split_text(text: str, *, max_chars: int, overlap: int) -> list[str]:
    chunks: list[str] = []
    start = 0

    while start < len(text):
        end = min(start + max_chars, len(text))
        if end < len(text):
            boundary = text.rfind("\n\n", start + max_chars // 2, end)
            if boundary == -1:
                boundary = text.rfind(" ", start + _WORD_BOUNDARY_MINIMUM, end)
            if boundary <= start:
                boundary = end
        else:
            boundary = end

        piece = text[start:boundary].strip()
        if piece:
            if len(piece) > max_chars:
                raise RuntimeError("Internal chunking error: chunk exceeded max_chars.")
            chunks.append(piece)

        if boundary >= len(text):
            break

        next_start = max(start + 1, boundary - overlap)
        while next_start < boundary and text[next_start].isspace():
            next_start += 1
        if next_start >= boundary:
            next_start = boundary
        start = next_start

    return chunks
