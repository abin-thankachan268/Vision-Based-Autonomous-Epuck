"""Run deterministic Webots pilots or formal scenario repetitions."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
SCENARIOS_PATH = PROJECT_ROOT / "scenarios" / "scenarios.json"
DEFAULT_WEBOTS = Path(r"F:\Webots-R2025a\msys64\mingw64\bin\webots.exe")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("--set", choices=("pilot", "formal"), default="pilot")
    parser.add_argument("--repetitions", type=int)
    parser.add_argument("--scenario", action="append", default=[])
    parser.add_argument("--controller", choices=("vision", "baseline", "both"), default="vision")
    parser.add_argument("--webots", type=Path, default=DEFAULT_WEBOTS)
    parser.add_argument("--time-limit", type=float, default=120.0)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--force", action="store_true")
    return parser.parse_args()


def load_scenarios() -> list[dict]:
    payload = json.loads(SCENARIOS_PATH.read_text(encoding="utf-8"))
    return payload["scenarios"]


def verify_frozen_configuration() -> None:
    manifest_path = PROJECT_ROOT / "config" / "frozen_experiment_configuration.json"
    if not manifest_path.exists():
        raise RuntimeError("Freeze the final configuration before formal testing")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    changed = []
    for relative_name, expected in manifest["files"].items():
        path = PROJECT_ROOT / Path(relative_name)
        actual = hashlib.sha256(path.read_bytes()).hexdigest() if path.exists() else "missing"
        if actual != expected:
            changed.append(relative_name)
    if changed:
        raise RuntimeError(f"Frozen configuration changed: {changed}")


def planned_controllers(requested: str, scenario: dict) -> list[str]:
    values = ["vision", "baseline"] if requested == "both" else [requested]
    if scenario["category"] != "lane":
        values = [value for value in values if value == "vision"]
    return values


def run_one(
    webots: Path,
    scenario: dict,
    controller: str,
    repetition: int,
    results_set: str,
    time_limit: float,
    dry_run: bool,
    force: bool,
) -> None:
    scenario_id = scenario["id"]
    if controller == "baseline":
        scenario_id += "_baseline"
    seed = 10_000 + repetition
    run_id = f"{scenario_id}_r{repetition:02d}_s{seed:04d}"
    output_root = PROJECT_ROOT / "results" / results_set
    raw_path = output_root / "raw" / f"{run_id}.csv"
    if raw_path.exists() and not force:
        print(f"SKIP existing {run_id}")
        return

    world = PROJECT_ROOT / "worlds" / (
        "ground_sensor_baseline.wbt" if controller == "baseline" else "autonomous_epuck_experiment.wbt"
    )
    command = [
        str(webots),
        "--batch",
        "--mode=fast",
        "--no-rendering",
        "--stdout",
        "--stderr",
        str(world),
    ]
    print("DRY" if dry_run else "RUN", run_id)
    if dry_run:
        return

    environment = os.environ.copy()
    configuration_id = "unfrozen"
    if results_set == "formal":
        manifest = json.loads(
            (PROJECT_ROOT / "config" / "frozen_experiment_configuration.json").read_text(encoding="utf-8")
        )
        configuration_id = manifest["configuration_id"]
    environment.update(
        {
            "EPUCK_SCENARIO_ID": scenario_id,
            "EPUCK_REPETITION": str(repetition),
            "EPUCK_SEED": str(seed),
            "EPUCK_RESULTS_SET": results_set,
            "EPUCK_CONTROLLER_MODE": controller,
            "EPUCK_CONFIGURATION_ID": configuration_id,
            "EPUCK_ROUTE": scenario.get("route", "full"),
            "EPUCK_LIGHTING": scenario.get("lighting", "nominal"),
            "EPUCK_ENABLE_STATIC": "1" if scenario.get("enable_static") else "0",
            "EPUCK_ENABLE_MOVING": "1" if scenario.get("enable_moving") else "0",
            "EPUCK_STATIC_POSITION": scenario.get("static_position", "center"),
            "EPUCK_OBSTACLE_LAYOUT": scenario.get("obstacle_layout", "single"),
            "EPUCK_MOVING_SPEED": str(scenario.get("moving_speed", 0.15)),
            "EPUCK_TIME_LIMIT": str(time_limit),
            "EPUCK_CAPTURE_FRAMES": "0",
        }
    )
    log_directory = output_root / "logs"
    log_directory.mkdir(parents=True, exist_ok=True)
    log_path = log_directory / f"{run_id}.log"
    with log_path.open("w", encoding="utf-8") as log:
        completed = subprocess.run(
            command,
            cwd=PROJECT_ROOT,
            env=environment,
            stdout=log,
            stderr=subprocess.STDOUT,
            check=False,
        )
    if completed.returncode != 0:
        raise RuntimeError(f"Webots failed for {run_id}; see {log_path}")

    if controller == "vision":
        source = PROJECT_ROOT / "controllers" / "vision_controller" / "vision_telemetry.csv"
        telemetry_directory = output_root / "telemetry"
        telemetry_directory.mkdir(parents=True, exist_ok=True)
        if source.exists():
            shutil.copy2(source, telemetry_directory / f"{run_id}.csv")


def main() -> None:
    args = parse_args()
    if not args.webots.exists():
        raise FileNotFoundError(args.webots)
    if args.set == "formal":
        verify_frozen_configuration()
    repetitions = args.repetitions or (10 if args.set == "formal" else 1)
    if repetitions < 1:
        raise ValueError("--repetitions must be positive")
    selected = load_scenarios()
    if args.scenario:
        wanted = set(args.scenario)
        selected = [scenario for scenario in selected if scenario["id"] in wanted]
        missing = wanted - {scenario["id"] for scenario in selected}
        if missing:
            raise ValueError(f"Unknown scenario IDs: {sorted(missing)}")
    for scenario in selected:
        for controller in planned_controllers(args.controller, scenario):
            for repetition in range(1, repetitions + 1):
                run_one(
                    args.webots,
                    scenario,
                    controller,
                    repetition,
                    args.set,
                    args.time_limit,
                    args.dry_run,
                    args.force,
                )


if __name__ == "__main__":
    main()
