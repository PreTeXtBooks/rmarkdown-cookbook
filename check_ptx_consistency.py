#!/usr/bin/env python3

from __future__ import annotations

import html
import re
import sys
import xml.etree.ElementTree as ET
from collections import Counter
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parent
LEFT_DOUBLE_QUOTE = "\u201c"
RIGHT_DOUBLE_QUOTE = "\u201d"
RIGHT_SINGLE_QUOTE = "\u2019"

CHAPTER_PAIRS = [
    ("01-installation.Rmd", "pretext/source/ch_intro.ptx"),
    ("02-overview.Rmd", "pretext/source/ch_overview.ptx"),
    ("03-basics.Rmd", "pretext/source/ch_basics.ptx"),
    ("04-content.Rmd", "pretext/source/ch_content.ptx"),
    ("05-formatting.Rmd", "pretext/source/ch_formatting.ptx"),
    ("06-latex.Rmd", "pretext/source/ch_latex.ptx"),
    ("07-html.Rmd", "pretext/source/ch_html.ptx"),
    ("08-word.Rmd", "pretext/source/ch_word.ptx"),
    ("09-multiformat.Rmd", "pretext/source/ch_multiformat.ptx"),
    ("10-tables.Rmd", "pretext/source/ch_tables.ptx"),
    ("11-chunk-options.Rmd", "pretext/source/ch_chunk-options.ptx"),
    ("12-output-hooks.Rmd", "pretext/source/ch_output-hooks.ptx"),
    ("13-chunk-hooks.Rmd", "pretext/source/ch_chunk-hooks.ptx"),
    ("14-knitr-misc.Rmd", "pretext/source/ch_knitr-misc.ptx"),
    ("15-languages.Rmd", "pretext/source/ch_languages.ptx"),
    ("16-projects.Rmd", "pretext/source/ch_projects.ptx"),
    ("17-workflow.Rmd", "pretext/source/ch_workflow.ptx"),
]

STOP_WORDS = {
    "all",
    "also",
    "and",
    "are",
    "but",
    "can",
    "each",
    "for",
    "from",
    "get",
    "got",
    "had",
    "has",
    "have",
    "here",
    "how",
    "into",
    "its",
    "just",
    "let",
    "may",
    "more",
    "not",
    "our",
    "out",
    "such",
    "than",
    "that",
    "the",
    "their",
    "them",
    "then",
    "there",
    "these",
    "they",
    "this",
    "those",
    "use",
    "using",
    "via",
    "was",
    "what",
    "when",
    "where",
    "which",
    "who",
    "why",
    "will",
    "with",
    "would",
    "you",
    "your",
}

# These thresholds are set from the current converted book so the check catches
# substantial drift without failing on expected markup differences between Rmd and PTX.
PROSE_RECALL_THRESHOLD = 0.85
HEADING_RECALL_THRESHOLD = 0.75
MIN_REFERENCE_ENTRIES = 5
MIN_TOKEN_LENGTH = 3


def split_rmd(text: str) -> tuple[str, list[str]]:
    lines = text.splitlines()
    prose_lines: list[str] = []
    code_blocks: list[str] = []
    i = 0

    if lines and lines[0].strip() == "---":
        i = 1
        while i < len(lines) and lines[i].strip() != "---":
            i += 1
        if i < len(lines):
            i += 1

    while i < len(lines):
        line = lines[i]

        match = re.match(r"^\s*([`~]{3,})(.*)$", line)
        if match:
            fence = match.group(1)
            fence_char = fence[0]
            fence_length = len(fence)
            code_lines: list[str] = []
            i += 1
            while i < len(lines):
                stripped = lines[i].strip()
                if stripped and set(stripped) == {fence_char} and len(stripped) >= fence_length:
                    break
                code_lines.append(lines[i])
                i += 1
            code_blocks.append("\n".join(code_lines))
        else:
            prose_lines.append(line)
        i += 1

    return "\n".join(prose_lines), code_blocks


def normalize_inline(text: str) -> str:
    text = html.unescape(text)
    text = text.lower()
    text = text.replace(LEFT_DOUBLE_QUOTE, '"')
    text = text.replace(RIGHT_DOUBLE_QUOTE, '"')
    text = text.replace(RIGHT_SINGLE_QUOTE, "'")
    text = re.sub(r"`([^`]*)`", lambda m: m.group(1), text)
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " IMG ", text)
    text = re.sub(r"\[([^\]]+)\]\([^)]+\)", lambda m: f" {m.group(1)} ", text)
    text = re.sub(r"https?://\S+", " URL ", text)
    text = re.sub(r"\[@[^\]]+\]", " CITE ", text)
    text = re.sub(r"\\@ref\([^)]*\)", " XREF ", text)
    text = re.sub(r"\\[A-Za-z]+\{([^}]*)\}", lambda m: f" {m.group(1)} ", text)
    text = re.sub(r"\{#[-A-Za-z0-9_]+\}", " ", text)
    text = re.sub(r"\{\.[-A-Za-z0-9_ ]+\}", " ", text)
    text = re.sub(r"<[^>]+>", " ", text)
    text = re.sub(r"[^a-z0-9]+", " ", text)
    return " ".join(text.split())


def tokenize(text: str) -> Counter[str]:
    words = normalize_inline(text).split()
    return Counter(word for word in words if len(word) >= MIN_TOKEN_LENGTH and word not in STOP_WORDS)


def calculate_token_recall(expected: Counter[str], actual: Counter[str]) -> float:
    total = sum(expected.values())
    if total == 0:
        return 1.0
    return sum((expected & actual).values()) / total


def extract_rmd_headings(prose: str) -> list[str]:
    headings = []
    for match in re.finditer(r"^(#+)\s+(.+)$", prose, flags=re.MULTILINE):
        heading = normalize_inline(match.group(2))
        if heading:
            headings.append(heading)
    return headings


def parse_xml(path: Path) -> ET.Element:
    try:
        return ET.fromstring(path.read_text(encoding="utf-8"))
    except ET.ParseError as exc:
        raise ValueError(f"Failed to parse XML in {path}") from exc


def extract_ptx_titles(root: ET.Element) -> list[str]:
    titles = []
    for element in root.iter():
        if element.tag.split("}")[-1] == "title":
            title = normalize_inline(" ".join(element.itertext()))
            if title:
                titles.append(title)
    return titles


def check_chapter(repo_root: Path, rmd_path: str, ptx_path: str) -> list[str]:
    rmd_full_path = repo_root / rmd_path
    ptx_full_path = repo_root / ptx_path

    prose, _ = split_rmd(rmd_full_path.read_text(encoding="utf-8"))
    ptx_text = ptx_full_path.read_text(encoding="utf-8")
    root = parse_xml(ptx_full_path)

    prose_recall = calculate_token_recall(tokenize(prose), tokenize(ptx_text))
    titles = extract_ptx_titles(root)
    headings = extract_rmd_headings(prose)
    matched_headings = sum(1 for heading in headings if heading in titles)
    heading_recall = 1.0 if not headings else matched_headings / len(headings)

    errors = []
    if prose_recall < PROSE_RECALL_THRESHOLD:
        errors.append(
            f"{rmd_path} -> {ptx_path}: prose token recall {prose_recall:.3f} is below {PROSE_RECALL_THRESHOLD:.2f}"
        )
    if heading_recall < HEADING_RECALL_THRESHOLD:
        errors.append(
            f"{rmd_path} -> {ptx_path}: heading recall {heading_recall:.3f} is below {HEADING_RECALL_THRESHOLD:.2f}"
        )
    return errors


def check_backmatter(repo_root: Path) -> list[str]:
    prose, _ = split_rmd((repo_root / "18-references.Rmd").read_text(encoding="utf-8"))
    root = parse_xml(repo_root / "pretext/source/meta_backmatter.ptx")
    titles = set(extract_ptx_titles(root))
    bibliography_entries = sum(1 for element in root.iter() if element.tag.split("}")[-1] == "biblio")

    errors = []
    if "references" not in titles:
        errors.append("18-references.Rmd -> pretext/source/meta_backmatter.ptx: missing References title")
    if "references" not in normalize_inline(prose):
        errors.append("18-references.Rmd: could not find the References heading in the source")
    if bibliography_entries < MIN_REFERENCE_ENTRIES:
        errors.append(
            "18-references.Rmd -> pretext/source/meta_backmatter.ptx: "
            f"expected at least {MIN_REFERENCE_ENTRIES} bibliography entries, found {bibliography_entries}"
        )
    return errors


def main() -> int:
    errors: list[str] = []
    for rmd_path, ptx_path in CHAPTER_PAIRS:
        errors.extend(check_chapter(REPO_ROOT, rmd_path, ptx_path))
    errors.extend(check_backmatter(REPO_ROOT))

    if errors:
        print("PTX consistency check failed:")
        for error in errors:
            print(f"- {error}")
        return 1

    print("PTX consistency check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
