"""Pre-bake the rolling dashboard payload as a static JSON asset."""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[2]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from ellectric.service.dashboard import build_rolling_demo  # noqa: E402


DEFAULT_OUTPUT = PROJECT_ROOT / "ellectric" / "web" / "public" / "rolling-demo.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Build static rolling-demo.json")
    parser.add_argument("--start", default="2025-10-01", help="UTC start date (YYYY-MM-DD)")
    parser.add_argument("--days", type=int, default=30, help="Number of days, clamped by service")
    parser.add_argument("--output", type=Path, default=DEFAULT_OUTPUT, help="Output JSON path")
    args = parser.parse_args()

    payload = build_rolling_demo(start=args.start, days=args.days)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text(
        json.dumps(payload.model_dump(mode="json"), ensure_ascii=False, separators=(",", ":")),
        encoding="utf-8",
    )
    rows = payload.meta.rows if payload.meta else 0
    warnings = len(payload.warnings)
    print(f"wrote {args.output} ({rows} rows, {warnings} warnings)")


if __name__ == "__main__":
    main()
