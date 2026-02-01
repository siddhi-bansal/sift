"""Entrypoint for python -m sift (Sift newsletter pipeline)."""
from .cli import main

if __name__ == "__main__":
    raise SystemExit(main())
