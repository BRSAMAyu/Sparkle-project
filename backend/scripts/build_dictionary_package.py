from __future__ import annotations

import argparse

from app.services.dictionary_package_service import dictionary_package_service


def main() -> None:
    parser = argparse.ArgumentParser(description="Build offline dictionary package")
    parser.add_argument(
        "--package-id",
        default="oxford-oaldpe-starter",
        help="Dictionary package identifier",
    )
    args = parser.parse_args()

    package_path = dictionary_package_service.ensure_package(args.package_id)
    print(package_path)


if __name__ == "__main__":
    main()
