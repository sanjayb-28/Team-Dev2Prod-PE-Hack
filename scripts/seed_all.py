import sys
from argparse import ArgumentParser
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from app.database import db
from app.services import import_events_csv, import_urls_csv, import_users_csv


def main() -> int:
    parser = ArgumentParser(description="Seed the workload database from a seed directory.")
    parser.add_argument("seed_directory", help="Directory containing users.csv, urls.csv, and events.csv")
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Clear existing users, urls, and events before importing the seed data.",
    )
    args = parser.parse_args()

    seed_dir = Path(args.seed_directory)
    users_path = seed_dir / "users.csv"
    urls_path = seed_dir / "urls.csv"
    events_path = seed_dir / "events.csv"

    create_app()

    if args.reset:
        db.connect(reuse_if_open=True)
        try:
            db.execute_sql('TRUNCATE TABLE event, link, "user" RESTART IDENTITY CASCADE')
        finally:
            if not db.is_closed():
                db.close()

    user_summary = import_users_csv(users_path)
    url_summary = import_urls_csv(urls_path)
    event_summary = import_events_csv(events_path)

    print(
        "Seeded data set: "
        f"users={user_summary['total']} "
        f"urls={url_summary['total']} "
        f"events={event_summary['total']}"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
