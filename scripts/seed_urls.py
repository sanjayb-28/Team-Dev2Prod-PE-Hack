from argparse import ArgumentParser
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from app import create_app
from app.services import import_urls_csv


def main():
    parser = ArgumentParser(description="Import URL seed data into the local database.")
    parser.add_argument("csv_path", help="Path to the urls.csv file")
    args = parser.parse_args()

    create_app()
    summary = import_urls_csv(args.csv_path)
    print(
        f"Imported {summary['total']} rows "
        f"({summary['created']} created, {summary['updated']} updated)."
    )


if __name__ == "__main__":
    main()
