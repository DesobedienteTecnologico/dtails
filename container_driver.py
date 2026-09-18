#!/usr/bin/env python3
"""Entry point run inside the dtails-build container (see Dockerfile).

Rebuilds AppState from a JSON state file the host wrote, then runs the exact
same build pipeline (src/runner.py) the GUI and CLI already use — just with
this container's pinned tool versions instead of whatever squashfs-tools/
mtools/dosfstools happen to be on the host, so mksquashfs/mkfs.fat output is
byte-identical no matter which machine invokes the container.
"""
import json
import sys
from pathlib import Path

REPO = Path("/work")
sys.path.insert(0, str(REPO))

from src.state import AppState                # noqa: E402
from src.runner import run_selected_actions_stream  # noqa: E402


def main() -> int:
    if len(sys.argv) != 2:
        print("usage: container_driver.py <state.json>", file=sys.stderr)
        return 2

    data = json.loads(Path(sys.argv[1]).read_text(encoding="utf-8"))

    state = AppState()
    state.options_json = data.get("options_json") or {}
    state.selected_image = data.get("selected_image") or ""
    state.selected_device = data.get("selected_device") or {}
    state.selected_additions = data.get("selected_additions") or []
    state.selected_deletions = data.get("selected_deletions") or []
    state.version_overrides = data.get("version_overrides") or {}

    if not state.selected_image:
        print("[ERROR] state.json has no selected_image", file=sys.stderr)
        return 2

    def sink(text: str) -> None:
        sys.stdout.write(text)
        sys.stdout.flush()

    run_selected_actions_stream(state, state.selected_image, sink=sink, cwd=str(REPO))
    return 0


if __name__ == "__main__":
    sys.exit(main())
