"""测试辅助：纯 stdlib 生成最小合法 PNG（8-bit RGB，非隔行）。

仅供 visual_baseline 单测使用（不依赖 PIL）。
"""

from __future__ import annotations

import struct
import zlib
from pathlib import Path


def _chunk(ctype: bytes, data: bytes) -> bytes:
    return (
        struct.pack(">I", len(data))
        + ctype
        + data
        + struct.pack(">I", zlib.crc32(ctype + data) & 0xFFFFFFFF)
    )


def make_png(path, width: int, height: int, pixel) -> None:
    """写一张 WxH PNG；``pixel(x, y)`` 返回 (r, g, b) 元组。"""
    raw = bytearray()
    for y in range(height):
        raw.append(0)  # filter type 0 (None)
        for x in range(width):
            r, g, b = pixel(x, y)
            raw.extend((r, g, b))
    ihdr = struct.pack(">IIBBBBB", width, height, 8, 2, 0, 0, 0)
    png = b"\x89PNG\r\n\x1a\n"
    png += _chunk(b"IHDR", ihdr)
    png += _chunk(b"IDAT", zlib.compress(bytes(raw)))
    png += _chunk(b"IEND", b"")
    Path(path).write_bytes(png)


def solid(w: int, h: int, gray: int):
    """返回恒色 pixel 函数（灰度写入 RGB 三通道）。"""
    return lambda x, y: (gray, gray, gray)


def vertical_gradient(w: int, h: int, top: int, bottom: int):
    """返回垂直渐变 pixel 函数。"""

    def pixel(x: int, y: int):
        v = top + ((bottom - top) * y) // max(1, h - 1)
        return (v, v, v)

    return pixel
