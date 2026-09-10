"""Enrich experiment run summaries from raw evaluator data and camera telemetry."""

from __future__ import annotations

import argparse
import csv
import json
from collections import Counter
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", choices=("pilot", "formal"), default="pilot")
    return parser.parse_args()


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(newline="", encoding="utf-8") as handle:
        return list(csv.DictReader(handle))


def duration_by_state(rows: list[dict[str, str]], state: str) -> float:
    if len(rows) < 2:
        return 0.0
    total = 0.0
    for current, following in zip(rows, rows[1:]):
        if current["state"] == state:
            total += float(following["time_s"]) - float(current["time_s"])
    return total


def main() -> None:
    args = parse_args()
    results_root = PROJECT_ROOT / "results" / args.set
    summary_rows = read_csv(results_root / "run_summary.csv")
    summaries_by_id = {row["run_id"]: row for row in summary_rows}
    summaries = list(summaries_by_id.values())
    scenario_payload = json.loads(
        (PROJECT_ROOT / "scenarios" / "scenarios.json").read_text(encoding="utf-8")
    )
    scenarios = {item["id"]: item for item in scenario_payload["scenarios"]}
    enriched: list[dict[str, object]] = []

    for summary in summaries:
        run_id = summary["run_id"]
        base_scenario_id = summary["scenario_id"].removesuffix("_baseline")
        scenario = scenarios.get(base_scenario_id, {})
        telemetry = read_csv(results_root / "telemetry" / f"{run_id}.csv")
        raw = read_csv(results_root / "raw" / f"{run_id}.csv")
        states = Counter(row["state"] for row in telemetry)
        detections = [row for row in telemetry if row["obstacle_present"] == "1"]
        expected_obstacle = bool(
            scenario.get("enable_static") or scenario.get("enable_moving")
        )
        first_stop_distance = ""
        first_stop = next((row for row in telemetry if row["state"] == "STOP_WAIT"), None)
        if first_stop and raw:
            stop_time = float(first_stop["time_s"])
            nearest = min(raw, key=lambda row: abs(float(row["time_s"]) - stop_time))
            first_stop_distance = nearest["moving_clearance_m"]
        enriched.append(
            {
                **summary,
                "detection_true_positive": int(expected_obstacle and bool(detections)),
                "detection_false_positive": int(not expected_obstacle and bool(detections)),
                "stop_wait_observed": int(states["STOP_WAIT"] > 0),
                "avoid_observed": int(states["AVOID"] > 0),
                "rejoin_observed": int(states["REJOIN"] > 0),
                "stop_wait_time_s": f"{duration_by_state(telemetry, 'STOP_WAIT'):.3f}",
                "avoidance_time_s": f"{duration_by_state(telemetry, 'AVOID'):.3f}",
                "rejoin_time_s": f"{duration_by_state(telemetry, 'REJOIN'):.3f}",
                "moving_stop_distance_m": first_stop_distance,
                "final_state": telemetry[-1]["state"] if telemetry else "",
            }
        )

    output = results_root / "enriched_summary.csv"
    if enriched:
        with output.open("w", newline="", encoding="utf-8") as handle:
            writer = csv.DictWriter(handle, fieldnames=list(enriched[0]))
            writer.writeheader()
            writer.writerows(enriched)
    print(output)
    print(f"runs={len(enriched)}")


if __name__ == "__main__":
    main()
