"""Run from the repository: uv run --extra games python examples/chess/play.py [flags]."""

import sys

from litjev.games.cli import play

if __name__ == "__main__":
    sys.argv.insert(1, "chess")
    play()
