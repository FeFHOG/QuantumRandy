from __future__ import annotations

import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.selector_pipeline import write_selector_candidate_highlight_summary


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Write a research-only Markdown summary for selector candidate highlight queues."
    )
    parser.add_argument("--review-dir", required=True, help="Directory containing selector pipeline review CSV files")
    parser.add_argument("--out", help="Output directory; defaults to --review-dir")
    args = parser.parse_args()

    manifest = write_selector_candidate_highlight_summary(args.review_dir, args.out)
    print(
        "Selector candidate highlights: "
        f"rows={manifest['highlight_rows']} "
        f"out={Path(manifest['outputs']['summary_markdown']).resolve()}"
    )


if __name__ == "__main__":
    main()
