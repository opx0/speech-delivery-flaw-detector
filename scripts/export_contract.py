"""Write the contract schema and fixtures: uv run --no-sync python scripts/export_contract.py."""

from pathlib import Path

from speech_delivery.contract.fixtures import write_all
from speech_delivery.contract.schema_export import write_bundle

ROOT = Path(__file__).resolve().parent.parent


def main() -> None:
    write_bundle(ROOT / "contract" / "schema" / "contract.schema.json")
    write_all(ROOT / "contract" / "fixtures")


if __name__ == "__main__":
    main()
