"""Build the local submission package integrity manifest."""

from __future__ import annotations

import hashlib
import json
from datetime import datetime, timezone
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
OUTPUT = PROJECT_ROOT / "SUBMISSION_MANIFEST.json"
EXCLUDED_DIR_NAMES = {
    ".agents",
    ".codex",
    ".git",
    ".pytest_cache",
    "__pycache__",
    "node_modules",
}
EXCLUDED_FILE_SUFFIXES = {".pyc", ".pyo"}


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def is_packaged_file(path: Path) -> bool:
    if not path.is_file() or path == OUTPUT:
        return False
    relative = path.relative_to(PROJECT_ROOT)
    if any(part in EXCLUDED_DIR_NAMES for part in relative.parts[:-1]):
        return False
    if relative.name.startswith("."):
        return False
    return path.suffix not in EXCLUDED_FILE_SUFFIXES


def main() -> None:
    files = []
    for path in sorted(PROJECT_ROOT.rglob("*")):
        if not is_packaged_file(path):
            continue
        relative = path.relative_to(PROJECT_ROOT).as_posix()
        files.append(
            {
                "path": relative,
                "size_bytes": path.stat().st_size,
                "sha256": sha256(path),
            }
        )

    payload = {
        "package_name": PROJECT_ROOT.name,
        "created_utc": datetime.now(timezone.utc).isoformat(),
        "hash_algorithm": "SHA-256",
        "manifest_self_excluded": True,
        "file_count": len(files),
        "total_size_bytes": sum(item["size_bytes"] for item in files),
        "files": files,
    }
    OUTPUT.write_text(json.dumps(payload, indent=2) + "\n", encoding="utf-8")
    print(OUTPUT)
    print(f"files={payload['file_count']} bytes={payload['total_size_bytes']}")


if __name__ == "__main__":
    main()
