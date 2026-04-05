from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path


REPO_ROOT = Path(__file__).resolve().parents[1]
BACKEND_ROOT = REPO_ROOT / "backend"
if str(BACKEND_ROOT) not in sys.path:
    sys.path.insert(0, str(BACKEND_ROOT))

from app.services.human_eval_review_service import HumanEvalReviewService  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Summarize a Sparkle human evaluation review run.")
    parser.add_argument("input", help="Path to the JSON review payload, or '-' to read from stdin.")
    parser.add_argument("--output", help="Optional output path.")
    parser.add_argument("--format", choices=("json", "markdown"), default="markdown")
    args = parser.parse_args()

    if args.input == "-":
        payload = json.loads(sys.stdin.read())
    else:
        input_path = Path(args.input)
        payload = json.loads(input_path.read_text(encoding="utf-8"))
    service = HumanEvalReviewService()
    summary = service.summarize_review_run(payload)

    rendered = (
        json.dumps(summary, ensure_ascii=False, indent=2)
        if args.format == "json"
        else service.render_markdown_summary(summary)
    )
    if args.output:
        Path(args.output).write_text(rendered, encoding="utf-8")
    else:
        sys.stdout.write(rendered)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
