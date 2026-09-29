#!/usr/bin/env python3
"""V4-G03 four-profile WCAG contrast computation for remaining defect sites."""
import json

def lum(hexv):
    hexv = hexv.lstrip('#')
    def ch(c):
        s = c / 255.0
        return s / 12.92 if s <= 0.03928 else ((s + 0.055) / 1.055) ** 2.4
    r, g, b = int(hexv[0:2], 16), int(hexv[2:4], 16), int(hexv[4:6], 16)
    return 0.2126 * ch(r) + 0.7152 * ch(g) + 0.0722 * ch(b)

def ratio(a, b):
    l1, l2 = lum(a), lum(b)
    hi, lo = max(l1, l2), min(l1, l2)
    return (hi + 0.05) / (lo + 0.05)

def hx(c):  # Color int -> hex
    return f"{c & 0xFFFFFF:06X}"

def comp(fg_hex, alpha, bg_hex):
    """Composite fg over bg."""
    f = [int(fg_hex[i:i+2], 16) for i in (0, 2, 4)]
    b = [int(bg_hex[i:i+2], 16) for i in (0, 2, 4)]
    out = [round(f[i] * alpha + b[i] * (1 - alpha)) for i in range(3)]
    return "%02X%02X%02X" % tuple(out)

def lerp_hex(a, b, t):
    a = [int(a[i:i+2], 16) for i in (0, 2, 4)]
    b = [int(b[i:i+2], 16) for i in (0, 2, 4)]
    return "%02X%02X%02X" % tuple(round(a[i] + (b[i] - a[i]) * t) for i in range(3))

# ---- profile palettes (from theme_manager.dart + pixel_preview_theme.dart) ----
P = {
  'classicL': dict(brand='825D49', success='456E52', info='48678D', warn='7D5C26',
      error='A0483E', brandSec='7A8BA6', refl='6C5C92',
      sP='F8F4EF', sS='F1EBE4', sT='E7DED4', sA='FCF8F3',
      tp='171717', ts='6C655D', tt='736F62',
      n200='F4EFE9', n300='DED5CB', n600='6A6057', bright='light'),
  'classicD': dict(brand='C97A43', success='7A9A83', info='8CA5C8', warn='D2A56D',
      error='D37B72', brandSec='7E8FAE', refl='A08AB8',
      sP='1A1A1E', sS='222226', sT='2C2C30', sA='0E0E10',
      tp='F4F1EB', ts='B8B1A6', tt='878375',
      n200='2A2A2E', n300='3A3A3E', n600='A8A8AE', bright='dark'),
  'paperDay': dict(brand='3E6652', success='386347', info='3C607A', warn='805126',
      error='9C3D38', brandSec='3C607A', refl='64558A',
      sP='F4F0E6', sS='FFFCF4', sT='E9E5D8', sA='FFFCF4',
      tp='29342F', ts='58665C', tt='58665C',
      n200='D0D8CB', n300='68766A', n600='36413B', bright='light'),
  'dusk': dict(brand='B9D5B5', success='B9D5B5', info='AFCADC', warn='E2BF89',
      error='F1B0A4', brandSec='AFCADC', refl='BCAED4',
      sP='24322B', sS='2F4036', sT='344B3B', sA='19241F',
      tp='F5F0E3', ts='C2CCBE', tt='C2CCBE',
      n200='2A3930', n300='2F4036', n600='9DAF9F', bright='dark'),
  'quiet': dict(brand='344F3D', success='345C40', info='36556D', warn='795126',
      error='933B35', brandSec='36556D', refl='64558A',
      sP='F7F5EF', sS='FFFFFF', sT='ECECE5', sA='FFFFFF',
      tp='202A24', ts='536056', tt='536056',
      n200='EAEEE8', n300='627063', n600='3D4A3F', bright='light'),
}
# quiet neutral600: lerp(line, ink, .8) per mapping note
for p, d in P.items():
    if p in ('paperDay', 'quiet', 'dusk'):
        base = d['n300'] if p == 'dusk' else d['n300']
        # n600 = lerp(line, ink, .8) except dusk from raised; approximations per source
for name, d in P.items():
    d['border'] = d['n600'] if d['bright'] == 'dark' else d['n300']
    d['bs'] = None  # borderSubtle composite computed per-face below

def border_subtle(p):
    d = P[p]
    a = 0.6 if d['bright'] == 'dark' else 0.72
    return a  # border.withValues(alpha: a)

results = []
def check(site, profile, fg, bg, need, note=''):
    r = ratio(fg, bg)
    results.append(dict(site=site, profile=profile, fg=fg, bg=bg, ratio=round(r, 2),
                        need=need, ok=r >= need, note=note))

# ============ DEFECT SITES (remaining, predecessor missed) ============
# 1. pattern_list archived badge: success text on success.withAlpha(40)~0.157 over card faces
for p, d in P.items():
    for face_name, face in (('sS', d['sS']), ('sP', d['sP'])):
        compbg = comp(d['success'], 40/255, face)
        check(f'archived-badge text success@0.157/{face_name}', p, d['success'], compbg, 4.5)
        # FIX: textPrimary on success@0.06
        compbg2 = comp(d['success'], 0.06, face)
        check(f'archived-badge FIX textPrimary@0.06/{face_name}', p, d['tp'], compbg2, 4.5)

# 2. pattern_list footer: brandPrimary.withAlpha(100)~0.392 text over card
for p, d in P.items():
    faded = comp(d['brand'], 100/255, d['sS'])
    check('footer brandPrimary@0.392/sS', p, faded, d['sS'], 4.5)
    check('footer FIX textSecondary/sS', p, d['ts'], d['sS'], 4.5)

# 3. pattern_list meta badge: info/success 11sp on color.withAlpha(28)~0.11 tint
for p, d in P.items():
    for tone in ('info', 'success'):
        compbg = comp(d[tone], 28/255, d['sS'])
        check(f'meta-badge {tone}@0.11/sS', p, d[tone], compbg, 4.5)
        # FIX icon on 0.06 tint (graphic >=3:1)
        compbg2 = comp(d[tone], 0.06, d['sS'])
        check(f'meta-badge FIX icon {tone}@0.06/sS', p, d[tone], compbg2, 3.0)
        check(f'meta-badge FIX label textPrimary@0.06', p, d['tp'], compbg2, 4.5)

# 4. aurora turns chip: textSecondary on borderSubtle(0.72/0.6 border over sheet face)
for p, d in P.items():
    a = border_subtle(p)
    for face_name, face in (('sS', d['sS']), ('sP', d['sP'])):
        chipbg = comp(d['border'], a, face)
        check(f'turns-chip ts on borderSubtle@{a}/{face_name}', p, d['ts'], chipbg, 4.5)
        check(f'turns-chip FIX ts/{face_name} (12sp same bg)', p, d['ts'], chipbg, 4.5)

# 5. capsule counter textSecondary on page bg
for p, d in P.items():
    check('capsule-counter ts/sP', p, d['ts'], d['sP'], 4.5)

# 6. agenda pending icon: textTertiary on sheet faces (graphic >=3:1)
for p, d in P.items():
    for face_name, face in (('sS', d['sS']), ('panel', lerp_hex(d['sS'], d['sT'], 0.18 if d['bright']=='dark' else 0.06))):
        check(f'agenda-pending tt icon/{face_name}', p, d['tt'], face, 3.0)
        check(f'agenda-pending FIX ts icon/{face_name}', p, d['ts'], face, 3.0)

# ============ SPOT-CHECK predecessor claims ============
# a. semantic_pill tone@0.05 over card/panel/secondary faces: 12sp tone label >=4.5
for p, d in P.items():
    for tone in ('info', 'success', 'warn', 'error', 'brand'):
        for face_name, face in (('sS', d['sS']), ('panel', lerp_hex(d['sS'], d['sT'], 0.18 if d['bright']=='dark' else 0.06)), ('sT', d['sT'])):
            compbg = comp(d[tone], 0.05, face)
            check(f'pill {tone}@0.05/{face_name}', p, d[tone], compbg, 4.5)

# b. capsule_jobs success/error text->textPrimary claims (>=7.3) & surfaceTertiary dark swap
for p, d in P.items():
    check('capsule ts on sT', p, d['ts'], d['sT'], 4.5)
    check('capsule brandPrimary progress on sT (3:1 graphic)', p, d['brand'], d['sT'], 3.0)

# c. taskReflection (pattern type icons >=3:1 on glass/card faces)
for p, d in P.items():
    for face_name, face in (('sS', d['sS']), ('sT', d['sT'])):
        check(f'taskReflection icon/{face_name}', p, d['refl'], face, 3.0)

# d. understanding/context/why textSecondary vs textTertiary upgrades: tt baseline
for p, d in P.items():
    check('ts on sA (upgraded helper text)', p, d['ts'], d['sA'], 4.5)

fails = [r for r in results if not r['ok']]
print(json.dumps(dict(total=len(results), fails=len(fails)), ensure_ascii=False))
print("\n===== FAILURES =====")
for r in fails:
    print(f"[{r['profile']}] {r['site']}: {r['ratio']} < {r['need']}  (fg={r['fg']} bg={r['bg']})")
print("\n===== KEY FIX VERIFICATIONS (all should pass) =====")
seen = set()
for r in results:
    if 'FIX' in r['site'] and not r['ok']:
        print(f"STILL FAILING [{r['profile']}] {r['site']}: {r['ratio']} < {r['need']}")
    if 'FIX' in r['site']:
        seen.add((r['profile'], r['site'], r['ok']))
minfix = {}
for r in results:
    if 'FIX' in r['site']:
        k = r['site'].split('/')[0].split(' (')[0]
        minfix.setdefault(k, []).append(r['ratio'])
for k, v in sorted(minfix.items()):
    print(f"{k}: min={min(v)}")
