#!/usr/bin/env python3
"""Check the deterministic spoken-word budget for the Faber Proof demo."""

from __future__ import annotations

import argparse
import json
import re
import sys
from dataclasses import asdict, dataclass
from pathlib import Path

REPOSITORY_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCRIPT = REPOSITORY_ROOT / "docs" / "DEMO_SCRIPT.md"
START_MARKER = "<!-- NARRATION START -->"
END_MARKER = "<!-- NARRATION END -->"
DEFAULT_MIN_WORDS = 388
DEFAULT_MAX_WORDS = 396
FAST_WORDS_PER_MINUTE = 150
SLOW_WORDS_PER_MINUTE = 140
WORD_PATTERN = re.compile(r"[A-Za-z0-9]+(?:['-][A-Za-z0-9]+)*")
COMMENT_PATTERN = re.compile(r"<!--.*?-->", flags=re.DOTALL)


class NarrationError(ValueError):
    """The narration block cannot be analyzed safely."""


@dataclass(frozen=True)
class NarrationAnalysis:
    schema: str
    status: str
    word_count: int
    minimum_words: int
    maximum_words: int
    estimated_seconds_at_150_wpm: float
    estimated_seconds_at_140_wpm: float
    target_seconds_minimum: int
    target_seconds_maximum: int
    note: str

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


def extract_narration(text: str) -> str:
    if text.count(START_MARKER) != 1 or text.count(END_MARKER) != 1:
        raise NarrationError("demo script must contain exactly one narration marker pair")
    start = text.index(START_MARKER) + len(START_MARKER)
    end = text.index(END_MARKER)
    if end <= start:
        raise NarrationError("narration end marker must follow the start marker")
    narration = COMMENT_PATTERN.sub(" ", text[start:end]).strip()
    if not narration:
        raise NarrationError("narration block is empty")
    return narration


def analyze_narration(
    text: str,
    *,
    minimum_words: int = DEFAULT_MIN_WORDS,
    maximum_words: int = DEFAULT_MAX_WORDS,
) -> NarrationAnalysis:
    if minimum_words <= 0 or maximum_words < minimum_words:
        raise NarrationError("word-count bounds are invalid")
    words = WORD_PATTERN.findall(extract_narration(text))
    word_count = len(words)
    status = "pass" if minimum_words <= word_count <= maximum_words else "fail"
    return NarrationAnalysis(
        schema="faber.demo_narration_analysis.v1",
        status=status,
        word_count=word_count,
        minimum_words=minimum_words,
        maximum_words=maximum_words,
        estimated_seconds_at_150_wpm=round(word_count * 60 / FAST_WORDS_PER_MINUTE, 1),
        estimated_seconds_at_140_wpm=round(word_count * 60 / SLOW_WORDS_PER_MINUTE, 1),
        target_seconds_minimum=155,
        target_seconds_maximum=170,
        note=(
            "Mechanical word-count estimate only; the human speaker must complete a "
            "timed rehearsal."
        ),
    )


def _json_text(analysis: NarrationAnalysis) -> str:
    return json.dumps(analysis.to_dict(), indent=2, sort_keys=True) + "\n"


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        description="Check the spoken narration block in docs/DEMO_SCRIPT.md."
    )
    parser.add_argument("--script", type=Path, default=DEFAULT_SCRIPT)
    parser.add_argument("--min-words", type=int, default=DEFAULT_MIN_WORDS)
    parser.add_argument("--max-words", type=int, default=DEFAULT_MAX_WORDS)
    parser.add_argument("--json", action="store_true", help="Print the analysis as JSON.")
    parser.add_argument("--json-out", type=Path)
    args = parser.parse_args(argv)

    try:
        analysis = analyze_narration(
            args.script.read_text(encoding="utf-8"),
            minimum_words=args.min_words,
            maximum_words=args.max_words,
        )
    except (OSError, NarrationError) as exc:
        print(f"demo script check failed: {exc}", file=sys.stderr)
        return 2

    text = _json_text(analysis)
    if args.json_out is not None:
        args.json_out.parent.mkdir(parents=True, exist_ok=True)
        args.json_out.write_text(text, encoding="utf-8", newline="\n")
    if args.json:
        print(text, end="")
    else:
        print(
            f"{analysis.status.upper()}: {analysis.word_count} words; "
            f"{analysis.estimated_seconds_at_150_wpm}s at 150 wpm to "
            f"{analysis.estimated_seconds_at_140_wpm}s at 140 wpm"
        )
        print(analysis.note)
    return 0 if analysis.status == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
