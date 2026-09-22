#!/usr/bin/env python3
"""Rule BN: prod/standalone compose DB images must share dev's pgvector+AGE build source.

Background (P0, D-AGE): the knowledge graph (星图/Apache AGE) requires the AGE
extension. The dev base compose (docker-compose.yml) builds ``sparkle_db`` from
``docker/pgvector-age.Dockerfile`` and runs ``sparkle_age_init`` (one-shot
``backend/scripts/init_age_extension.py``), but production used to ship a bare
``pgvector/pgvector:pg16`` image with no AGE and no init — breaking the galaxy
features in prod. This guard locks the parity in place:

1. Dev source of truth: ``docker-compose.yml`` ``sparkle_db`` builds from
   ``docker/pgvector-age.Dockerfile`` (single source of truth, never duplicated).
2. Prod: ``docker-compose.prod.yml`` ``db`` must use the same build
   (same dockerfile + same AGE_REF arg) and must NOT pin a bare pgvector image.
3. Prod AGE init: a ``db_age_init`` one-shot service must run
   ``init_age_extension.py`` on the same backend image as ``db_migrate``,
   chained after db health + migrations, and every AGE-consuming service
   (backend/agent/celery workers/beat) must wait for it.
4. Standalone celery stack: ``docker-compose.celery.yml`` ``sparkle_db`` must
   also derive from the same AGE build instead of a bare pgvector image.

Dependency-free: parses the (machine-formatted) compose files by indentation
instead of requiring PyYAML.
"""
from __future__ import annotations

import argparse
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]

DEV_COMPOSE = REPO_ROOT / "docker-compose.yml"
PROD_COMPOSE = REPO_ROOT / "docker-compose.prod.yml"
CELERY_COMPOSE = REPO_ROOT / "docker-compose.celery.yml"

AGE_DOCKERFILE = "docker/pgvector-age.Dockerfile"
AGE_INIT_SCRIPT = "init_age_extension.py"
BARE_PGVECTOR_PREFIX = "pgvector/pgvector:"
AGE_REF_KEY = "AGE_REF"

# Prod services that read/write the AGE graph and must start only after init.
PROD_AGE_CONSUMERS = (
    "backend",
    "agent",
    "celery_worker",
    "celery_glm_batch_worker",
    "celery_beat",
)


def _parse_compose_services(text: str) -> dict[str, dict]:
    """Extract per-service image/build/command/depends_on/restart from a compose file.

    Only understands the canonical formatting of this repo's compose files:
    services at indent 2, service keys at indent 4, mapping children at 6+.
    """
    services: dict[str, dict] = {}
    in_services = False
    current: dict | None = None
    section: str | None = None

    for raw in text.splitlines():
        stripped = raw.strip()
        if not stripped or stripped.startswith("#"):
            continue
        indent = len(raw) - len(raw.lstrip(" "))
        key, _, value = stripped.partition(":")
        value = value.strip()

        if indent == 0:
            in_services = key == "services" and not value
            current = None
            section = None
            continue
        if not in_services:
            continue

        if indent == 2:
            current = services.setdefault(key, {
                "image": None,
                "build": None,
                "command": "",
                "depends_on": {},
                "restart": None,
            })
            section = None
            continue
        if current is None:
            continue

        if indent == 4:
            section = None
            if key == "image":
                current["image"] = value
            elif key == "build" and not value:
                current["build"] = {"context": None, "dockerfile": None, "args": {}}
                section = "build"
            elif key == "depends_on" and not value:
                section = "depends_on"
            elif key == "command":
                current["command"] = value
            elif key == "restart":
                current["restart"] = value
            continue

        if current.get("build") is not None and section in ("build", "build_args"):
            if indent == 6 and section == "build":
                if key == "args" and not value:
                    section = "build_args"
                elif key in ("context", "dockerfile"):
                    current["build"][key] = value
            elif indent >= 8 and section == "build_args":
                current["build"]["args"][key] = value
        elif section == "depends_on":
            if indent == 6 and not value:
                current["depends_on"][key] = None
            elif indent >= 8 and key == "condition" and current["depends_on"]:
                last_dep = next(reversed(current["depends_on"]))
                current["depends_on"][last_dep] = value

    return services


def check_rule_bn(
    dev_services: dict[str, dict],
    prod_services: dict[str, dict],
    celery_services: dict[str, dict],
) -> list[str]:
    violations: list[str] = []

    # --- 1. Dev source of truth -------------------------------------------
    dev_db = dev_services.get("sparkle_db")
    dev_build = dev_db.get("build") if dev_db else None
    if not dev_build:
        violations.append(
            "BN001 dev base compose (docker-compose.yml) sparkle_db must build from "
            f"the pgvector+AGE source ({AGE_DOCKERFILE}); found no build section"
        )
        dev_dockerfile = dev_age_ref = None
    else:
        dev_dockerfile = dev_build.get("dockerfile")
        dev_age_ref = dev_build.get("args", {}).get(AGE_REF_KEY)
        if dev_dockerfile != AGE_DOCKERFILE:
            violations.append(
                f"BN002 dev sparkle_db build dockerfile drifted: expected "
                f"`{AGE_DOCKERFILE}`, found `{dev_dockerfile}`"
            )
        if not dev_age_ref:
            violations.append(
                f"BN003 dev sparkle_db build must pin the AGE ref via `{AGE_REF_KEY}` arg"
            )

    # --- 2. Prod db image/build parity ------------------------------------
    prod_db = prod_services.get("db")
    if prod_db is None:
        violations.append("BN004 prod compose (docker-compose.prod.yml) has no `db` service")
    else:
        prod_image = prod_db.get("image") or ""
        if prod_image.startswith(BARE_PGVECTOR_PREFIX):
            violations.append(
                f"BN010 prod db uses bare image `{prod_image}` which lacks Apache AGE — "
                f"星图/知识图谱 will be unavailable; build from `{AGE_DOCKERFILE}` instead"
            )
        prod_build = prod_db.get("build")
        if not prod_build:
            violations.append(
                "BN011 prod db must declare a build section sharing dev's "
                f"pgvector+AGE source ({AGE_DOCKERFILE})"
            )
        else:
            if prod_build.get("dockerfile") != (dev_dockerfile or AGE_DOCKERFILE):
                violations.append(
                    f"BN012 prod db build dockerfile `{prod_build.get('dockerfile')}` is not "
                    f"the dev source of truth `{dev_dockerfile or AGE_DOCKERFILE}`"
                )
            if dev_build and prod_build.get("context") != dev_build.get("context"):
                violations.append(
                    f"BN013 prod db build context `{prod_build.get('context')}` differs from "
                    f"dev `{dev_build.get('context')}` — build sources must be identical"
                )
            if dev_age_ref and prod_build.get("args", {}).get(AGE_REF_KEY) != dev_age_ref:
                violations.append(
                    f"BN014 prod db {AGE_REF_KEY} "
                    f"`{prod_build.get('args', {}).get(AGE_REF_KEY)}` differs from dev "
                    f"`{dev_age_ref}`"
                )

    # --- 3. Prod db_age_init one-shot -------------------------------------
    age_init = prod_services.get("db_age_init")
    if age_init is None:
        violations.append(
            "BN020 prod compose is missing the `db_age_init` one-shot service "
            f"(must run `{AGE_INIT_SCRIPT}` like dev's sparkle_age_init)"
        )
    else:
        if AGE_INIT_SCRIPT not in age_init.get("command", ""):
            violations.append(
                f"BN021 prod db_age_init command must run `{AGE_INIT_SCRIPT}`, found: "
                f"`{age_init.get('command')}`"
            )
        migrate_image = (prod_services.get("db_migrate") or {}).get("image")
        if migrate_image and age_init.get("image") != migrate_image:
            violations.append(
                "BN022 prod db_age_init image must be the same backend image as "
                f"db_migrate (`{migrate_image}`), found `{age_init.get('image')}`"
            )
        expected_deps = {
            "db": "service_healthy",
            "db_migrate": "service_completed_successfully",
        }
        for dep, condition in expected_deps.items():
            if age_init.get("depends_on", {}).get(dep) != condition:
                violations.append(
                    f"BN023 prod db_age_init must depend on `{dep}` with "
                    f"`{condition}` (migrations/schema first, then AGE init)"
                )
        if age_init.get("restart") != '"no"' and age_init.get("restart") != "no":
            violations.append(
                "BN024 prod db_age_init must be a one-shot (`restart: \"no\"`), found "
                f"`{age_init.get('restart')}`"
            )

    # --- 4. AGE consumers wait for init -----------------------------------
    for svc_name in PROD_AGE_CONSUMERS:
        svc = prod_services.get(svc_name)
        if svc is None:
            violations.append(f"BN030 prod compose is missing expected service `{svc_name}`")
            continue
        actual = svc.get("depends_on", {}).get("db_age_init")
        if actual != "service_completed_successfully":
            violations.append(
                f"BN031 prod `{svc_name}` must depend on `db_age_init` with "
                f"`service_completed_successfully` (found `{actual}`) — AGE graph must "
                "exist before galaxy reads/writes"
            )

    # --- 5. Standalone celery stack ----------------------------------------
    celery_db = celery_services.get("sparkle_db")
    if celery_db is None:
        violations.append(
            "BN040 celery compose (docker-compose.celery.yml) has no `sparkle_db` service"
        )
    else:
        celery_image = celery_db.get("image") or ""
        if celery_image.startswith(BARE_PGVECTOR_PREFIX):
            violations.append(
                f"BN041 celery stack sparkle_db uses bare image `{celery_image}` without "
                f"AGE; build from `{AGE_DOCKERFILE}` like the main stack"
            )
        celery_build = celery_db.get("build")
        if not celery_build or celery_build.get("dockerfile") != AGE_DOCKERFILE:
            found = (celery_build or {}).get("dockerfile")
            violations.append(
                f"BN042 celery stack sparkle_db must build from `{AGE_DOCKERFILE}`, "
                f"found `{found}`"
            )

    return violations


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dev", type=Path, default=DEV_COMPOSE, help="dev base compose path")
    parser.add_argument("--prod", type=Path, default=PROD_COMPOSE, help="prod compose path")
    parser.add_argument("--celery", type=Path, default=CELERY_COMPOSE, help="celery compose path")
    args = parser.parse_args()

    for path in (args.dev, args.prod, args.celery):
        if not path.is_file():
            print(f"RULE BN FAILED: compose file not found: {path}")
            return 1

    violations = check_rule_bn(
        dev_services=_parse_compose_services(args.dev.read_text(encoding="utf-8")),
        prod_services=_parse_compose_services(args.prod.read_text(encoding="utf-8")),
        celery_services=_parse_compose_services(args.celery.read_text(encoding="utf-8")),
    )
    if violations:
        print("RULE BN FAILED: prod/standalone DB images must share dev's pgvector+AGE source")
        for violation in violations:
            print(f"  - {violation}")
        return 1
    print("RULE BN OK: prod/celery DB builds share dev's pgvector+AGE source and AGE init is wired in")
    return 0


if __name__ == "__main__":
    sys.exit(main())
