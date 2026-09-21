"""轻量 diff 辅助：纯 stdlib PNG 指纹比对（不要求像素一致）。

原则（任务卡 B-04）：
- 基线对比是"结构/布局是否大体一致"的辅助信号，**不做像素级要求**；
- 无 PIL/numpy 依赖：自带最小 PNG 解码（8-bit、非隔行、灰度/RGB/RGBA/调色板），
  降采样为 N×N 灰度网格指纹，报归一化平均绝对差（0.0=同图，1.0=全反相）；
- 解码不支持的 PNG（16-bit/隔行/损坏）→ 回退 metadata 级对比（尺寸/字节/sha256），
  并在结果中如实标注 ``fingerprint="unavailable"``。
"""

from __future__ import annotations

import hashlib
import struct
import zlib
from pathlib import Path

_PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"
_FINGERPRINT_GRID = 16
_DEFAULT_SIMILAR_THRESHOLD = 0.08


class PngUnsupportedError(ValueError):
    """当前解码器不支持的 PNG 形态。"""


def _read_chunks(data: bytes):
    offset = len(_PNG_SIGNATURE)
    while offset + 8 <= len(data):
        (length,) = struct.unpack(">I", data[offset : offset + 4])
        ctype = data[offset + 4 : offset + 8]
        cdata = data[offset + 8 : offset + 8 + length]
        yield ctype, cdata
        offset += 12 + length  # length + type + data + crc
        if ctype == b"IEND":
            break


def _paeth(a: int, b: int, c: int) -> int:
    p = a + b - c
    pa, pb, pc = abs(p - a), abs(p - b), abs(p - c)
    if pa <= pb and pa <= pc:
        return a
    if pb <= pc:
        return b
    return c


def decode_png_gray(path: str | Path) -> tuple[int, int, list[int]]:
    """解码 PNG 为 (width, height, 灰度行优先数组)。

    支持：bit depth 8、非隔行、color type 0/2/3/4/6。Alpha 按白底合成。
    """
    data = Path(path).read_bytes()
    if not data.startswith(_PNG_SIGNATURE):
        raise PngUnsupportedError("not a PNG file")

    width = height = 0
    bit_depth = color_type = interlace = 0
    palette: list[tuple[int, int, int]] = []
    idat = bytearray()

    for ctype, cdata in _read_chunks(data):
        if ctype == b"IHDR":
            width, height, bit_depth, color_type, _, _, interlace = struct.unpack(
                ">IIBBBBB", cdata
            )
        elif ctype == b"PLTE":
            palette = [
                (cdata[i], cdata[i + 1], cdata[i + 2]) for i in range(0, len(cdata), 3)
            ]
        elif ctype == b"IDAT":
            idat.extend(cdata)
        elif ctype == b"IEND":
            break

    if bit_depth != 8:
        raise PngUnsupportedError(f"bit depth {bit_depth} unsupported (only 8)")
    if interlace != 0:
        raise PngUnsupportedError("interlaced PNG unsupported")
    if color_type == 1 or color_type > 6 or color_type in (5,):
        raise PngUnsupportedError(f"color type {color_type} unsupported")
    channels = {0: 1, 2: 3, 3: 1, 4: 2, 6: 4}[color_type]
    if color_type == 3 and not palette:
        raise PngUnsupportedError("palette PNG without PLTE chunk")

    raw = zlib.decompress(bytes(idat))
    stride = width * channels
    expected = (stride + 1) * height
    if len(raw) < expected:
        raise PngUnsupportedError("truncated PNG pixel stream")

    # 反滤波（每行首字节为 filter type）。
    out = bytearray(stride * height)
    prev_start = -1  # 相对 out 的上一行起点
    for row in range(height):
        src = row * (stride + 1)
        ftype = raw[src]
        line = raw[src + 1 : src + 1 + stride]
        row_start = row * stride
        if ftype == 0:
            out[row_start : row_start + stride] = line
        elif ftype == 1:  # Sub
            for i in range(stride):
                left = out[row_start + i - channels] if i >= channels else 0
                out[row_start + i] = (line[i] + left) & 0xFF
        elif ftype == 2:  # Up
            for i in range(stride):
                up = out[prev_start + i] if prev_start >= 0 else 0
                out[row_start + i] = (line[i] + up) & 0xFF
        elif ftype == 3:  # Average
            for i in range(stride):
                left = out[row_start + i - channels] if i >= channels else 0
                up = out[prev_start + i] if prev_start >= 0 else 0
                out[row_start + i] = (line[i] + ((left + up) >> 1)) & 0xFF
        elif ftype == 4:  # Paeth
            for i in range(stride):
                left = out[row_start + i - channels] if i >= channels else 0
                up = out[prev_start + i] if prev_start >= 0 else 0
                ul = out[prev_start + i - channels] if prev_start >= 0 and i >= channels else 0
                out[row_start + i] = (line[i] + _paeth(left, up, ul)) & 0xFF
        else:
            raise PngUnsupportedError(f"unknown filter type {ftype}")
        prev_start = row_start

    # 转 8-bit 灰度（alpha 白底合成）。
    gray = [0] * (width * height)
    for idx in range(width * height):
        base = idx * channels
        if color_type == 0:
            g = out[base]
        elif color_type == 4:
            a = out[base + 1]
            g = (out[base] * a + 255 * (255 - a)) // 255
        elif color_type == 2:
            r, g_, b = out[base], out[base + 1], out[base + 2]
            g = (r * 299 + g_ * 587 + b * 114) // 1000
        elif color_type == 6:
            r, g_, b = out[base], out[base + 1], out[base + 2]
            a = out[base + 3]
            k = 255 - a
            r = (r * a + 255 * k) // 255
            g_ = (g_ * a + 255 * k) // 255
            b = (b * a + 255 * k) // 255
            g = (r * 299 + g_ * 587 + b * 114) // 1000
        else:  # palette
            r, g_, b = palette[out[base]]
            g = (r * 299 + g_ * 587 + b * 114) // 1000
        gray[idx] = g
    return width, height, gray


def fingerprint(path: str | Path, grid: int = _FINGERPRINT_GRID) -> list[float] | None:
    """计算 N×N 网格平均灰度指纹（0.0–1.0）；解码失败返回 None。"""
    try:
        width, height, gray = decode_png_gray(path)
    except (PngUnsupportedError, zlib.error, struct.error, OSError, IndexError):
        return None
    if width == 0 or height == 0:
        return None
    n = grid * grid
    acc = [0] * n
    counts = [0] * n
    for y in range(height):
        gy = min(grid - 1, y * grid // height)
        row_base = y * width
        for x in range(width):
            gx = min(grid - 1, x * grid // width)
            cell = gy * grid + gx
            acc[cell] += gray[row_base + x]
            counts[cell] += 1
    return [a / c / 255.0 for a, c in zip(acc, counts)]


def fingerprint_distance(fp_a: list[float], fp_b: list[float]) -> float:
    """归一化平均绝对差（0.0–1.0）。"""
    if len(fp_a) != len(fp_b) or not fp_a:
        raise ValueError("fingerprints must be same non-empty length")
    return sum(abs(a - b) for a, b in zip(fp_a, fp_b)) / len(fp_a)


def _meta(path: Path) -> dict:
    data = path.read_bytes()
    return {
        "bytes": len(data),
        "sha256": hashlib.sha256(data).hexdigest(),
    }


def compare(
    path_a: str | Path,
    path_b: str | Path,
    similar_threshold: float = _DEFAULT_SIMILAR_THRESHOLD,
) -> dict:
    """对比两张截图。

    返回::

        {"verdict": "identical" | "similar" | "different" | "unknown",
         "distance": float | None,
         "fingerprint": "grid16" | "unavailable",
         "same_bytes": bool, "meta_a": {...}, "meta_b": {...}}
    """
    a, b = Path(path_a), Path(path_b)
    meta_a, meta_b = _meta(a), _meta(b)
    result: dict = {
        "verdict": "unknown",
        "distance": None,
        "fingerprint": "grid16",
        "same_bytes": meta_a["sha256"] == meta_b["sha256"],
        "meta_a": meta_a,
        "meta_b": meta_b,
    }
    if result["same_bytes"]:
        result["verdict"] = "identical"
        result["distance"] = 0.0
        return result

    fp_a, fp_b = fingerprint(a), fingerprint(b)
    if fp_a is None or fp_b is None or len(fp_a) != len(fp_b):
        result["fingerprint"] = "unavailable"
        return result

    dist = fingerprint_distance(fp_a, fp_b)
    result["distance"] = round(dist, 6)
    result["verdict"] = "similar" if dist <= similar_threshold else "different"
    return result


def diff_manifests(manifest_a: dict, manifest_b: dict) -> dict:
    """按 canonical 名（去 sha8 前缀差异）对齐两张 manifest，输出变化清单。

    对齐键：surface/state/persona/platform/viewport（即排除 build_sha8 段），
    适配"同一状态、新构建 SHA"的基线滚动；键相同但 sha256 变化即 ``changed``。
    """
    def key(entry: dict) -> str:
        return "__".join(
            (
                entry["surface"],
                entry["state"],
                entry["persona"],
                entry["platform"],
                entry["viewport"],
            )
        )

    def key_remove_sha8(raw: str) -> str:
        # 键不含 sha8；兼容直接传文件名的情况。
        return raw.split("__sha8_")[0]

    a_by_key = {key(e): e for e in manifest_a["entries"]}
    b_by_key = {key(e): e for e in manifest_b["entries"]}

    added = sorted(set(b_by_key) - set(a_by_key))
    removed = sorted(set(a_by_key) - set(b_by_key))
    changed = sorted(
        k
        for k in set(a_by_key) & set(b_by_key)
        if a_by_key[k]["sha256"] != b_by_key[k]["sha256"]
    )
    unchanged = sorted(
        k
        for k in set(a_by_key) & set(b_by_key)
        if a_by_key[k]["sha256"] == b_by_key[k]["sha256"]
    )
    return {
        "added": added,
        "removed": removed,
        "changed": changed,
        "unchanged": unchanged,
    }
