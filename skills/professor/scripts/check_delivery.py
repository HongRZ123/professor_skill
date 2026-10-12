#!/usr/bin/env python3
"""Read-only audit of course materials and a lesson's observable delivery omissions."""
import argparse
import json
from pathlib import Path
from course_state import check_delivery, check_materials


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    parser.add_argument("--lesson")
    args = parser.parse_args()
    root = Path(args.root).expanduser().resolve()
    result = check_delivery(root, args.lesson) if args.lesson else check_materials(root)
    print(json.dumps(result, ensure_ascii=False, indent=2))
    return 0 if result["ok"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
