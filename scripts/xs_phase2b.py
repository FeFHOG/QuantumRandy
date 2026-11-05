"""Phase 2b: the refined cross-sectional family (docs/PHASE2B_CROSS_SECTIONAL_PROTOCOL.md).

Step 1, ``--metrics-spans PATH``: write the days of Binance metrics to download for each contract that enters the
Phase 2a development universe, from 30 days before its first universe day (not before 2021-12-01, when metrics
coverage begins for most contracts) to its last universe day. Feed the file to
``../RandysLab-STRICT4H/scripts/fetch_metrics.py --spans``. Holdout bars stay sealed. The factor evaluation is added
once the owner has chosen the Deflated Sharpe convention, before it is run.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from quantumrandy.xsection.panel import load_panel
from quantumrandy.xsection.universe import liquid_universe

UNIVERSE_SIZE = 50
METRICS_FIRST_DAY = pd.Timestamp("2021-12-01", tz="UTC")
METRICS_PAD_DAYS = 30


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--data", default=str(ROOT.parent / "RandysLab-STRICT4H" / "data" / "universe_1d_20261105"))
    ap.add_argument("--metrics-spans", required=True, help="Write {symbol: [first_day, last_day]} here")
    args = ap.parse_args()

    panel = load_panel(args.data)
    mask = liquid_universe(panel, top_n=UNIVERSE_SIZE)
    spans = metrics_spans(mask)
    Path(args.metrics_spans).write_text(json.dumps(spans, indent=1, sort_keys=True) + "\n", encoding="utf-8")
    days = sum((pd.Timestamp(b) - pd.Timestamp(a)).days + 1 for a, b in spans.values())
    print(f"{len(spans)} contracts, {days} contract-days -> {args.metrics_spans}")


def metrics_spans(mask: pd.DataFrame) -> dict[str, list[str]]:
    spans = {}
    for symbol in mask.columns[mask.any()]:
        days = mask.index[mask[symbol]]
        first = max(days[0] - pd.Timedelta(days=METRICS_PAD_DAYS), METRICS_FIRST_DAY)
        if days[-1] >= METRICS_FIRST_DAY:
            spans[symbol] = [str(first.date()), str(days[-1].date())]
    return spans


if __name__ == "__main__":
    main()
