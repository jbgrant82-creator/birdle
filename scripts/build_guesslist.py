#!/usr/bin/env python3
"""Builds data/guesses.json, the guess-validation word list, from a raw open
English word list filtered to the four Birdle lengths (4/5/6/7).

Source: dwyl/english-words words_alpha.txt (MIT-licensed, a superset of
/usr/share/dict/words that also includes inflected forms like "fledged").

The guess pool is intentionally permissive (per HANDOFF.md §1: "any valid
English word of the right length" — the guess/answer asymmetry is load-
bearing, players need to be able to burn a turn on a probe word). The game
client unions this list with the wordbank answers themselves at runtime, so
an answer word is ALWAYS a valid guess even if it's a proper noun the raw
dictionary wouldn't contain (e.g. ZAZU, GWAIHIR) — see HANDOFF.md §9's
"Bank entries that aren't valid in your guess-validation word list" warning.

Usage:
    python3 scripts/build_guesslist.py [path/to/words_alpha.txt]
"""
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
DEFAULT_SOURCE = ROOT / ".cache" / "words_alpha.txt"
OUT_DIR = ROOT / "data" / "guesses"
WORDBANK_PATH = ROOT / "data" / "wordbank.json"

LENGTHS = (4, 5, 6, 7)


def main():
    src = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SOURCE
    if not src.exists():
        sys.exit(f"source word list not found: {src}\n"
                  f"fetch dwyl/english-words words_alpha.txt there first, or "
                  f"pass a path as argv[1].")

    by_length = {n: set() for n in LENGTHS}
    with open(src) as f:
        for line in f:
            w = line.strip().lower()
            if len(w) in by_length and w.isalpha():
                by_length[len(w)].add(w)

    bank = json.loads(WORDBANK_PATH.read_text())
    answers_by_length = {n: set() for n in LENGTHS}
    for entry in bank["words"]:
        answers_by_length[entry["length"]].add(entry["word"].lower())

    OUT_DIR.mkdir(parents=True, exist_ok=True)
    coverage_report = {}
    for n in LENGTHS:
        # Union with answers so every bank word is guessable even if the
        # open dictionary doesn't have it (proper nouns, Pokémon, etc).
        missing_from_dict = answers_by_length[n] - by_length[n]
        combined = sorted(by_length[n] | answers_by_length[n])
        # One file per length — a daily puzzle only ever needs one of these,
        # same "don't ship what you don't need" rule as the audio preloading
        # in HANDOFF.md §6.
        (OUT_DIR / f"{n}.json").write_text(json.dumps(combined))
        coverage_report[n] = {
            "dictionary_words": len(by_length[n]),
            "bank_answers": len(answers_by_length[n]),
            "bank_answers_missing_from_dictionary": sorted(missing_from_dict),
            "total_guessable": len(combined),
        }

    print(f"wrote {OUT_DIR.relative_to(ROOT)}/{{4,5,6,7}}.json")
    for n in LENGTHS:
        r = coverage_report[n]
        print(f"  length {n}: {r['dictionary_words']} dict words + "
              f"{len(r['bank_answers_missing_from_dictionary'])} bank-only "
              f"words added = {r['total_guessable']} total guessable")
        if r["bank_answers_missing_from_dictionary"]:
            print(f"    bank-only (not in open dictionary): "
                  f"{', '.join(r['bank_answers_missing_from_dictionary'])}")


if __name__ == "__main__":
    main()
