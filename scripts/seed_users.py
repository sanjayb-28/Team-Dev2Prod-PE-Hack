import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from app.services import import_users_csv


def main() -> int:
    if len(sys.argv) != 2:
        print("Usage: uv run python scripts/seed_users.py <path-to-users.csv>")
        return 1

    create_app()
    summary = import_users_csv(sys.argv[1])
    print(
        f"Imported users from {sys.argv[1]}: "
        f"{summary['created']} created, {summary['updated']} updated."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
