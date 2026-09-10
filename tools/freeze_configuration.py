"""Create a local, content-addressed manifest for the formal controller."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT_ROOT / "config" / "frozen_experiment_configuration.json"
INPUTS = [
    PROJECT_ROOT / "controllers" / "vision_controller" / name
    for name in (
        "config.py",
        "control.py",
        "models.py",
        "perception.py",
        "tracking.py",
        "telemetry.py",
        "vision_controller.py",
    )
] + [
    PROJECT_ROOT / "controllers" / "experiment_supervisor" / "experiment_supervisor.py",
    PROJECT_ROOT / "controllers" / "experiment_supervisor" / "metrics.py",
    PROJECT_ROOT / "controllers" / "baseline_ground" / "baseline_ground.py",
    PROJECT_ROOT / "tools" / "generate_research_world.py",
    PROJECT_ROOT / "tools" / "run_scenarios.py",
    PROJECT_ROOT / "tools" / "summarize_results.py",
    PROJECT_ROOT / "scenarios" / "scenarios.json",
    PROJECT_ROOT / "worlds" / "autonomous_epuck_experiment.wbt",
    PROJECT_ROOT / "worlds" / "ground_sensor_baseline.wbt",
    PROJECT_ROOT / "requirements.txt",
]


def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> None:
    missing = [str(path) for path in INPUTS if not path.exists()]
    if missing:
        raise FileNotFoundError(f"Cannot freeze missing files: {missing}")
    files = {
        path.relative_to(PROJECT_ROOT).as_posix(): digest(path)
        for path in sorted(INPUTS)
    }
    aggregate = hashlib.sha256(
        "\n".join(f"{name}:{value}" for name, value in files.items()).encode("utf-8")
    ).hexdigest()
    manifest = {
        "name": "Frozen formal vision controller",
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "configuration_id": aggregate[:16],
        "sha256": aggregate,
        "files": files,
        "note": "Local content manifest; this is not a Git commit or remote version.",
    }
    OUTPUT.parent.mkdir(parents=True, exist_ok=True)
    OUTPUT.write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT)
    print(manifest["configuration_id"])


if __name__ == "__main__":
    main()
