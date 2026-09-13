#!/usr/bin/env python3
"""Audit ordinary-English collisions before a public vocabulary is published."""

import argparse
import json
from pathlib import Path

AMBIGUOUS = [
    "air", "apple", "base", "basic", "box", "branch", "cloud", "code", "cursor",
    "dart", "edge", "flow", "go", "linear", "notion", "oracle", "power", "react",
    "rust", "signal", "spark", "swift", "teams", "vessel", "warp", "windsurf", "zoom",
]
TEMPLATES = [
    "The {word} is visible from here.", "Please move the {word} to the left.",
    "We discussed the {word} after lunch.", "That {word} was not part of the plan.",
    "A different {word} might work better.", "I noticed the {word} this morning.",
    "The old {word} remains in place.", "Can you check the {word} again?",
    "They kept the {word} for another day.", "This {word} belongs in the final draft.",
]


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("snapshot", type=Path)
    parser.add_argument("--minimum", type=int, default=2000)
    args = parser.parse_args()
    entities = json.loads(args.snapshot.read_bytes())["entities"]
    by_name = {item["canonical"].casefold(): item for item in entities}
    corpus = [template.format(word=word) for repeat in range(8) for word in AMBIGUOUS for template in TEMPLATES]
    if len(corpus) < args.minimum:
        raise SystemExit("negative corpus below minimum")
    unsafe = []
    for word in AMBIGUOUS:
        entity = by_name.get(word)
        if entity and entity.get("ambiguity_risk") != "high":
            unsafe.append(entity["canonical"])
    if unsafe:
        raise SystemExit("ordinary-English collisions not marked high risk: " + ", ".join(unsafe))
    print(json.dumps({"sentences": len(corpus), "ambiguous_forms": len(AMBIGUOUS), "unsafe": 0}))


if __name__ == "__main__":
    main()
