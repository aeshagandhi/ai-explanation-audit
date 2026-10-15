"""Read and write the small, auditable files for the framing experiment.

All current inputs and raw responses live under datasets/framing. JSON writes
are atomic so an interrupted run does not leave a half-written checkpoint.
"""

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / "datasets/framing"


def read_json(path: Path):
    """Load a study document from disk."""
    return json.loads(path.read_text(encoding="utf-8"))


def write_json(path: Path, document) -> None:
    """Replace a JSON document only after its complete content is written."""
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_text(
        json.dumps(document, indent=2, allow_nan=False) + "\n", encoding="utf-8"
    )
    temporary.replace(path)


def file_hash(path: Path) -> str:
    """Fingerprint the exact file bytes used by this experiment."""
    return hashlib.sha256(path.read_bytes()).hexdigest()
