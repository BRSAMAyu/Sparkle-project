#!/usr/bin/env python3
import os
import sys


def check_shadowing(root: str) -> int:
    app_dir = os.path.join(root, "app")
    config_module = os.path.join(app_dir, "config.py")
    config_pkg = os.path.join(app_dir, "config", "__init__.py")

    if os.path.exists(config_module) and os.path.exists(config_pkg):
        print(
            "Shadowing detected: both app/config.py and app/config/__init__.py exist.",
            file=sys.stderr,
        )
        print(
            "Remove one of them to avoid import ambiguity for app.config.",
            file=sys.stderr,
        )
        return 1
    return 0


if __name__ == "__main__":
    backend_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
    raise SystemExit(check_shadowing(backend_root))
