import argparse
import os
import sys

from anef_client import fetch_date_statut


def main():
    parser = argparse.ArgumentParser(description="ANEF single-user check")
    parser.add_argument("--username", help="ANEF username (or ANEF_USERNAME env)")
    parser.add_argument("--password", help="ANEF password (or ANEF_PASSWORD env)")
    args = parser.parse_args()

    username = args.username or os.getenv("ANEF_USERNAME")
    password = args.password or os.getenv("ANEF_PASSWORD")

    if not username or not password:
        print("Missing credentials. Use --username/--password or ANEF_USERNAME/ANEF_PASSWORD.")
        return 2

    date_statut = fetch_date_statut(username, password)
    print(f"date_statut: {date_statut}")

    github_output = os.environ.get("GITHUB_OUTPUT")
    if github_output:
        with open(github_output, "a", encoding="utf-8") as f:
            f.write(f"date_statut={date_statut}\n")

    return 0


if __name__ == "__main__":
    sys.exit(main())
