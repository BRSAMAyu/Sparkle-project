#!/usr/bin/env python3
"""程序生成最小像素占位资源（V4-S04）。

零外部素材：占位 PNG 全部由本脚本程序生成（最小像素方块 + 边角标识色），
并按 nearest-neighbor 整数倍导出 DPR 变体（2.0x / 3.0x）。

产出（默认）：
  mobile/assets/placeholders/placeholder_pixel_block.png      (8x8, 1.0x 主资源)
  mobile/assets/placeholders/2.0x/placeholder_pixel_block.png (16x16, NN 整数倍)
  mobile/assets/placeholders/3.0x/placeholder_pixel_block.png (24x24, NN 整数倍)

规约：
- 主资源与变体像素数据严格整数倍最近邻复制（不插值、不平滑），
  保证 Flutter 按 devicePixelRatio 选variant后像素边界不糊。
- 输出字节确定（固定 zlib level、无时间戳），同参数重跑逐字节一致，
  便于账本 sha256 冻结。
"""
from __future__ import annotations

import argparse
import struct
import sys
import zlib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
DEFAULT_OUT = REPO_ROOT / "mobile" / "assets" / "placeholders"

# 占位方块规格：8x8，中心 4x4 主色 + 1px 深色描边 + 四角透明，
# 是"最小像素方块"约定形，供 AssetCatalog PROPOSED 资源回退显示。
BASE_SIZE = 8
OUTLINE = (96, 96, 110, 255)
FILL = (178, 178, 196, 255)
DIAG = (140, 140, 158, 255)
CLEAR = (0, 0, 0, 0)
DPR_VARIANTS = (2.0, 3.0)


def placeholder_rgba() -> list[list[tuple[int, int, int, int]]]:
    px: list[list[tuple[int, int, int, int]]] = []
    for y in range(BASE_SIZE):
        row: list[tuple[int, int, int, int]] = []
        for x in range(BASE_SIZE):
            edge = x in (0, BASE_SIZE - 1) or y in (0, BASE_SIZE - 1)
            corner = (x in (0, BASE_SIZE - 1)) and (y in (0, BASE_SIZE - 1))
            diag = (x == y) or (x + y == BASE_SIZE - 1)
            if corner:
                row.append(CLEAR)
            elif edge or diag:
                row.append(OUTLINE)
            else:
                row.append(FILL)
        px.append(row)
    # 中心点缀对角色块（星芒提示，纯装饰无语义）
    cx = BASE_SIZE // 2
    px[cx - 1][cx - 1] = DIAG
    px[cx - 1][cx] = DIAG
    return px


def nearest_neighbor_scale(
    px: list[list[tuple[int, int, int, int]]], factor: int
) -> list[list[tuple[int, int, int, int]]]:
    scaled: list[list[tuple[int, int, int, int]]] = []
    for row in px:
        scaled_row: list[tuple[int, int, int, int]] = []
        for color in row:
            scaled_row.extend([color] * factor)
        for _ in range(factor):
            scaled.append(list(scaled_row))
    return scaled


def write_png(path: Path, px: list[list[tuple[int, int, int, int]]]) -> bytes:
    height = len(px)
    width = len(px[0])
    raw = b"".join(
        b"\x00" + b"".join(struct.pack("4B", *color) for color in row) for row in px
    )

    def chunk(tag: bytes, data: bytes) -> bytes:
        return (
            struct.pack(">I", len(data))
            + tag
            + data
            + struct.pack(">I", zlib.crc32(tag + data) & 0xFFFFFFFF)
        )

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 6, 0, 0, 0)
    png = (
        b"\x89PNG\r\n\x1a\n"
        + chunk(b"IHDR", ihdr)
        + chunk(b"IDAT", zlib.compress(raw, 9))
        + chunk(b"IEND", b"")
    )
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(png)
    return png


def read_png_size(data: bytes) -> tuple[int, int]:
    if not data.startswith(b"\x89PNG\r\n\x1a\n"):
        raise ValueError("not a png")
    width, height = struct.unpack(">II", data[16:24])
    return width, height


def generate(out_dir: Path = DEFAULT_OUT) -> list[dict[str, object]]:
    base = placeholder_rgba()
    written: list[dict[str, object]] = []
    main_path = out_dir / "placeholder_pixel_block.png"
    write_png(main_path, base)

    def rel_or_abs(path: Path) -> str:
        try:
            return path.resolve().relative_to(REPO_ROOT).as_posix()
        except ValueError:
            return path.resolve().as_posix()

    def bundle_rel(path: Path) -> str:
        try:
            return path.resolve().relative_to((REPO_ROOT / "mobile" / "assets").resolve()).as_posix()
        except ValueError:
            return path.name

    written.append(
        {
            "path": rel_or_abs(main_path),
            "bundle_path": bundle_rel(main_path),
            "width": BASE_SIZE,
            "height": BASE_SIZE,
            "dpr": "1.0",
        }
    )
    for dpr in DPR_VARIANTS:
        factor = int(dpr)
        scaled = nearest_neighbor_scale(base, factor)
        variant_path = out_dir / f"{dpr:.1f}x" / "placeholder_pixel_block.png"
        write_png(variant_path, scaled)
        written.append(
            {
                "path": rel_or_abs(variant_path),
                "bundle_path": bundle_rel(variant_path),
                "width": BASE_SIZE * factor,
                "height": BASE_SIZE * factor,
                "dpr": f"{dpr:.1f}",
            }
        )
    return written


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args()
    written = generate(args.out)
    for item in written:
        data = Path(REPO_ROOT / str(item["path"])).read_bytes()
        width, height = read_png_size(data)
        expect = (int(item["width"]), int(item["height"]))
        if (width, height) != expect:
            print(f"FAIL {item['path']}: size {width}x{height} != {expect}")
            return 1
        print(f"OK {item['path']} {width}x{height} sha256={zlib.crc32(data):08x}(crc)")
    print(f"generated {len(written)} placeholder png(s) under {args.out}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
