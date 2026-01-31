"""Subprocess worker for embedding: reads texts from JSON file, writes embeddings to JSON file.
Run: python -m unmet.embed_worker input.json output.json
Isolates segfaults from the main process."""
from __future__ import annotations

import json
import sys


def main() -> int:
    if len(sys.argv) != 3:
        print("Usage: python -m unmet.embed_worker input.json output.json", file=sys.stderr)
        return 1
    input_path = sys.argv[1]
    output_path = sys.argv[2]
    try:
        with open(input_path, encoding="utf-8") as f:
            texts = json.load(f)
        from .gemini_client import embed_batch
        embeddings = embed_batch(texts)
        with open(output_path, "w", encoding="utf-8") as f:
            json.dump(embeddings, f)
        return 0
    except Exception as e:
        print(f"embed_worker failed: {e}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
