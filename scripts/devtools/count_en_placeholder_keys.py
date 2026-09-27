#!/usr/bin/env python3
"""EN placeholder-debt counter — canonical counting criterion for V3-FIX-362.

Ruling (wt685, 2026-09-25; supersedes the unreproducible 136-vs-217 dispute):

  Scope   : live keys = identifier-set method — a key is live iff its name
            appears as a token in any .dart file under mobile/lib or
            mobile/test, excluding mobile/lib/l10n and mobile/lib/gen
            (gen products are outputs, not consumers).
  EN-DRAFT (canonical meter): en value consists solely of Title-Case words
            (every whitespace-separated word starts uppercase) AND ends with
            one of the nine developer-descriptor suffix words
            {Title, Desc, Label, Subtitle, Hint, Message, Failed, Success,
            Error} (case-sensitive).
    - multi-word subset  = the published "136" (wt672 U-10) — exact match.
    - single-token tail  = 19 at audit time ('Title' / 'Failed' / ...);
      several are faithful short labels, tracked as a review tail, not the
      meter.
  EN-DRAFT-EXACT (sub-signature): en value equals splitCamelCase(key)
    case-insensitively — the pure "dev typed the key name as the value"
    signature. NOT the meter: alone it over-matches (503 at audit time)
    because many legitimate short labels ('Dark Mode', 'View Details') share
    the shape.
  ZH-VARIANT: en values containing CJK — all *Zh-suffixed deliberate variants
    (code selects them via zh?xZh:xEn branches; en locale never renders them).
    Not translation debt. (wt677 verify4 exact-reproduced = 22.)

Published counts, for the record:
  - wt672 (V3-FIX-362 filing): 136 = multi-word EN-DRAFT. Reproduced exactly.
  - wt677 verify4: 217 under the prose heuristic; not reproducible here
    (natural variants span 19..155, wider unions up to 303). Treated as
    method-sensitive approximation — the filing number to quote is the
    multi-word EN-DRAFT count this script prints.

Usage: python3 scripts/devtools/count_en_placeholder_keys.py [repo_root]
Exit 0 always (measurement tool, not a guard).
"""
from __future__ import annotations

import json
import re
import sys
from pathlib import Path

SUFFIXES = ("Title", "Desc", "Label", "Subtitle", "Hint", "Message", "Failed", "Success", "Error")
CJK = re.compile(r"[\u4e00-\u9fff]")


def live_keys(mobile: Path) -> set[str]:
    arb = json.loads((mobile / "lib/l10n/app_en.arb").read_text(encoding="utf-8"))
    keys = {k for k in arb if not k.startswith("@") and isinstance(arb[k], str)}
    blob: list[str] = []
    for root in ("lib", "test"):
        for p in sorted((mobile / root).rglob("*")):
            if not p.is_file() or p.suffix != ".dart":
                continue
            parts = set(p.parent.parts)
            if "l10n" in parts or "gen" in parts:
                continue
            blob.append(p.read_text(encoding="utf-8", errors="ignore"))
    hay = "\n".join(blob)
    return {k for k in keys if k in hay}


def split_camel(key: str) -> list[str]:
    return re.sub(r"([A-Z]+)", r" \1", key).replace("_", " ").split()


def main() -> int:
    repo = Path(sys.argv[1]) if len(sys.argv) > 1 else Path.cwd()
    mobile = repo / "mobile" if (repo / "mobile").exists() else repo
    en = json.loads((mobile / "lib/l10n/app_en.arb").read_text(encoding="utf-8"))
    zh = json.loads((mobile / "lib/l10n/app_zh.arb").read_text(encoding="utf-8"))
    live = live_keys(mobile)

    def ends_suffix(v: str) -> bool:
        return any(v.endswith(s) for s in SUFFIXES)

    def title_case_words(v: str) -> bool:
        words = v.split()
        return bool(words) and all(w[:1].isupper() for w in words)

    draft = {k for k in live if title_case_words(en[k]) and ends_suffix(en[k])}
    multi = {k for k in draft if " " in en[k]}
    single = draft - multi
    exact = {
        k
        for k in live
        if " ".join(w.lower() for w in split_camel(k))
        == " ".join(w.lower() for w in en[k].split())
    }
    zh_variants = {k for k in live if CJK.search(en[k])}
    zh_variants_bad_shape = {k for k in zh_variants if not k.endswith("Zh")}

    print(f"live keys (lib+test identifier-set): {len(live)}")
    print(f"EN-DRAFT total (canonical set):       {len(draft)}")
    print(f"EN-DRAFT multi-word (THE meter=136):  {len(multi)}")
    print(f"EN-DRAFT single-token (review tail):  {len(single)}")
    print(f"EN-DRAFT-EXACT (==splitCamel(key)):   {len(exact)}")
    print(f"ZH-VARIANT (en value has CJK):        {len(zh_variants)}")
    print(f"ZH-VARIANT without *Zh suffix (bad):  {len(zh_variants_bad_shape)}")
    if zh_variants_bad_shape:
        for k in sorted(zh_variants_bad_shape):
            print(f"  BAD-SHAPE {k} => {en[k]!r}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
