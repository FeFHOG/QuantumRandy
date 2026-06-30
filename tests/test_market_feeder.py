from __future__ import annotations

from quantumrandy.market_feeder import bars_from_binance, config_from_dict


def test_config_normalizes_binance_symbol() -> None:
    cfg = config_from_dict({"binance": {"symbol": "BTC/USDT:USDT"}, "runtime": {"url": "http://127.0.0.1:8787/"}})

    assert cfg.symbol == "BTCUSDT"
    assert cfg.runtime_url == "http://127.0.0.1:8787"
    assert cfg.include_unclosed is False


def test_bars_from_binance_aligns_latest_prior_funding_rate() -> None:
    klines = [
        [1_704_067_200_000, "100", "105", "99", "104", "1000", 1_704_081_599_999],
        [1_704_081_600_000, "104", "108", "103", "107", "1100", 1_704_095_999_999],
        [1_704_096_000_000, "107", "109", "101", "102", "1200", 1_704_110_399_999],
    ]
    funding = [
        {"fundingTime": 1_704_067_200_000, "fundingRate": "0.0001"},
        {"fundingTime": 1_704_096_000_000, "fundingRate": "-0.0002"},
    ]

    bars = bars_from_binance(klines, funding)

    assert [item["funding_rate"] for item in bars] == [0.0001, 0.0001, -0.0002]
    assert bars[0]["timestamp"] == "2024-01-01T00:00:00+00:00"
    assert bars[1]["close"] == 107.0
