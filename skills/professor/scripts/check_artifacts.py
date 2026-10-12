#!/usr/bin/env python3
"""Check a course or a prepared lesson; no network or model calls."""
import argparse
import json
from pathlib import Path
from course_state import check_workspace, check_lesson, load_state, WorkspaceError


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--root", required=True)
    p.add_argument("--lesson", help="Validate this prepared lesson before publishing")
    args = p.parse_args()
    root = Path(args.root).expanduser().resolve()
    result = check_workspace(root)
    if args.lesson:
        try:
            check_lesson(root, load_state(root), args.lesson, allow_draft=True)
        except (WorkspaceError, OSError, ValueError, KeyError, TypeError) as exc:
            result["errors"].append(str(exc))
            result["ok"] = False
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
