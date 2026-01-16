"""SpecLeft Result Collector."""

from __future__ import annotations

import json
from collections import defaultdict
from datetime import datetime
from pathlib import Path
from typing import Any, Optional


class ResultCollector:
    """Collects pytest results and transforms them into SpecLeft format."""

    def __init__(self, output_dir: str = ".specleft/results") -> None:
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def collect(self, pytest_results: list[dict[str, Any]]) -> dict[str, Any]:
        features_map: dict[str, dict[str, list[dict]]] = defaultdict(
            lambda: defaultdict(list)
        )

        for result in pytest_results:
            features_map[result["feature_id"]][result["scenario_id"]].append(result)

        features_list = []
        total_executions = total_passed = total_failed = total_skipped = 0
        total_duration = 0.0

        for feature_id in sorted(features_map.keys()):
            scenarios_list = []
            for scenario_id in sorted(features_map[feature_id].keys()):
                executions = features_map[feature_id][scenario_id]
                scenario_passed = sum(1 for e in executions if e["status"] == "passed")
                scenario_failed = sum(1 for e in executions if e["status"] == "failed")
                scenario_skipped = sum(
                    1 for e in executions if e["status"] == "skipped"
                )

                scenarios_list.append(
                    {
                        "scenario_id": scenario_id,
                        "is_parameterized": executions[0].get(
                            "is_parameterized", False
                        ),
                        "executions": executions,
                        "summary": {
                            "total": len(executions),
                            "passed": scenario_passed,
                            "failed": scenario_failed,
                        },
                    }
                )

                total_executions += len(executions)
                total_passed += scenario_passed
                total_failed += scenario_failed
                total_skipped += scenario_skipped
                total_duration += sum(e.get("duration", 0) for e in executions)

            features_list.append(
                {"feature_id": feature_id, "scenarios": scenarios_list}
            )

        return {
            "run_id": datetime.now().isoformat(),
            "summary": {
                "total_features": len(features_list),
                "total_scenarios": sum(len(f["scenarios"]) for f in features_list),
                "total_executions": total_executions,
                "passed": total_passed,
                "failed": total_failed,
                "skipped": total_skipped,
                "duration": round(total_duration, 3),
            },
            "features": features_list,
        }

    def write(self, data: dict[str, Any], filename: Optional[str] = None) -> Path:
        if filename is None:
            filename = f"results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        filepath = self.output_dir / filename
        with filepath.open("w") as file_obj:
            json.dump(data, file_obj, indent=2, default=str)
        return filepath

    def get_latest_results(self) -> Optional[dict[str, Any]]:
        json_files = sorted(self.output_dir.glob("results_*.json"))
        if not json_files:
            return None
        with json_files[-1].open() as file_obj:
            return json.load(file_obj)
