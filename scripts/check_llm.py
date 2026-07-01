from __future__ import annotations

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from quantumrandy.llm import call_llm


def main() -> None:
    content = call_llm(
        messages=[
            {"role": "system", "content": "You are a concise API health-check assistant."},
            {
                "role": "user",
                "content": (
                    "Return JSON only. Format: "
                    "{\"ok\": true, \"formulas\": [\"zscore(ret(close,6),48)\"]}"
                ),
            },
        ],
        temperature=0.0,
    )
    print(json.dumps({"raw": content}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
