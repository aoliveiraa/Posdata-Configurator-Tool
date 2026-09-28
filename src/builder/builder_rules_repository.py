from __future__ import annotations

import json

from pathlib import Path

from typing import Any
from typing import Dict


SUPPORTED_MARKETS = {
    "AU",
    "CA",
    "DE",
    "ES",
    "PT",
    "UK",
    "US",
}


DEFAULT_RULES_ROOT = Path(
    "config/builder_rules"
)


class BuilderRulesRepository:
    """
    Sprint 2.0.1

    Central source of truth
    for Builder FROM_SCRATCH generation.

    Load order:

        common.json
              +
        market.json
              ↓
        merged rules
    """

    def __init__(
        self,
        rules_root: str | Path = DEFAULT_RULES_ROOT,
    ):
        self.rules_root = Path(
            rules_root
        )

    def available_markets(
        self,
    ) -> list[str]:

        result = []

        for market in sorted(
            SUPPORTED_MARKETS
        ):

            market_file = (
                self.rules_root
                / f"{market}.json"
            )

            if market_file.is_file():
                result.append(
                    market
                )

        return result

    def common_rules_file(
        self,
    ) -> Path:

        return (
            self.rules_root
            / "common.json"
        )

    def market_rules_file(
        self,
        market: str,
    ) -> Path:

        normalized = (
            str(market or "")
            .strip()
            .upper()
        )

        return (
            self.rules_root
            / f"{normalized}.json"
        )

    def load(
        self,
        market: str,
    ) -> Dict[str, Any]:

        normalized_market = (
            str(market or "")
            .strip()
            .upper()
        )

        result = {
            "status": "READY",
            "market": normalized_market,
            "rules_root": str(
                self.rules_root
            ),
            "warnings": [],
            "errors": [],
            "rules": {},
        }

        if (
            normalized_market
            not in SUPPORTED_MARKETS
        ):
            result["status"] = "FAIL"

            result["errors"].append(
                f"Unsupported market: "
                f"{normalized_market}"
            )

            return result

        common_file = (
            self.common_rules_file()
        )

        market_file = (
            self.market_rules_file(
                normalized_market
            )
        )

        common_rules = (
            self._load_json(
                common_file
            )
        )

        market_rules = (
            self._load_json(
                market_file
            )
        )

        if (
            common_rules is None
        ):
            result["status"] = "FAIL"

            result["errors"].append(
                f"Rules file not found: "
                f"{common_file}"
            )

            return result

        if (
            market_rules is None
        ):
            result["status"] = "FAIL"

            result["errors"].append(
                f"Rules file not found: "
                f"{market_file}"
            )

            return result

        merged_rules = (
            self._deep_merge(
                common_rules,
                market_rules,
            )
        )

        result["rules"] = (
            merged_rules
        )

        return result

    def _load_json(
        self,
        path: Path,
    ) -> Dict[str, Any] | None:

        if not path.is_file():
            return None

        try:

            with path.open(
                "r",
                encoding="utf-8",
            ) as stream:

                data = json.load(
                    stream
                )

        except (
            OSError,
            json.JSONDecodeError,
        ):
            return None

        if not isinstance(
            data,
            dict,
        ):
            return None

        return data

    def _deep_merge(
        self,
        base: Dict[str, Any],
        override: Dict[str, Any],
    ) -> Dict[str, Any]:

        result = dict(base)

        for key, value in override.items():

            if (
                key in result
                and isinstance(
                    result[key],
                    dict,
                )
                and isinstance(
                    value,
                    dict,
                )
            ):
                result[key] = (
                    self._deep_merge(
                        result[key],
                        value,
                    )
                )

            else:
                result[key] = value

        return result