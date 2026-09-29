#!/usr/bin/env python3
"""V4-Q01 录像合成：引擎帧 PNG 按真实墙钟合成 mp4（出处披露制）。

背景（j02/macos 先例 + V4-Q01 probe 实证）：flutter_test 宿主进程锁住 macOS
控制台输出，物理录屏得到黑帧；故验收录像 = 集成测试内真实引擎
RepaintBoundary 抓帧（topmost full-viewport，V3-FIX-543 承接），按每帧的
文件 mtime（真实墙钟）推算停留时长后用 ffmpeg 合成。本脚本不做任何
帧内容加工；时间轴即真实操作时间轴。

用法：
  python3 scripts/devtools/q01_synth_video.py <shots_dir> <out_mp4>

输出：<out_mp4> + <out_mp4>.manifest.json（每帧文件名/真实时刻/停留时长，
sha256 汇总），披露出处写入五件套 run_manifest。
"""
from __future__ import annotations

import datetime as dt
import hashlib
import json
import subprocess
import sys
from pathlib import Path


def main() -> int:
    if len(sys.argv) != 3:
        print(__doc__)
        return 2
    shots_dir = Path(sys.argv[1])
    out_mp4 = Path(sys.argv[2])
    frames = sorted(shots_dir.rglob("*.png"))
    if not frames:
        print(f"no png frames under {shots_dir}")
        return 1
    entries = []
    for f in frames:
        mtime = dt.datetime.fromtimestamp(f.stat().st_mtime).astimezone()
        entries.append({"file": str(f.relative_to(shots_dir)), "mtime": mtime.isoformat(), "bytes": f.stat().st_size})
    entries.sort(key=lambda e: e["mtime"])
    # 停留时长 = 下一帧 mtime - 本帧 mtime；末帧给 2s 收尾。上限 30s 防
    # 长等待段（真实等待存在，披露保留），下限 0.5s。
    timeline = []
    for i, e in enumerate(entries):
        if i + 1 < len(entries):
            delta = (dt.datetime.fromisoformat(entries[i + 1]["mtime"]) - dt.datetime.fromisoformat(e["mtime"])).total_seconds()
            dur = max(0.5, min(30.0, delta))
        else:
            dur = 2.0
        e["hold_seconds"] = dur
        timeline.append(e)

    concat_list = out_mp4.with_suffix(".concat.txt")
    with concat_list.open("w") as fh:
        for e in timeline:
            fh.write(f"file '{(shots_dir / e['file']).resolve()}'\n")
            fh.write(f"duration {e['hold_seconds']:.3f}\n")
        # ffmpeg concat 需要末帧重复一次以固化最后 duration
        fh.write(f"file '{(shots_dir / timeline[-1]['file']).resolve()}'\n")

    out_mp4.parent.mkdir(parents=True, exist_ok=True)
    cmd = [
        "ffmpeg", "-y", "-f", "concat", "-safe", "0",
        "-i", str(concat_list.resolve()),
        "-vf", "scale=1280:-2:flags=lanczos,fps=2,format=yuv420p",
        "-c:v", "libx264", "-preset", "veryfast", "-crf", "26",
        str(out_mp4.resolve()),
    ]
    proc = subprocess.run(cmd, capture_output=True, text=True, cwd=str(shots_dir))
    if proc.returncode != 0:
        print(proc.stderr[-2000:])
        return proc.returncode

    manifest = {
        "provenance": (
            "video synthesized from real-engine RepaintBoundary frames captured "
            "inside integration_test driver (physical screen recording shows black "
            "frames under flutter_test host lock — probe-verified); timeline = real "
            "wall-clock from file mtimes; no frame content edited"
        ),
        "shots_dir": str(shots_dir),
        "out": str(out_mp4),
        "frame_count": len(timeline),
        "wall_start": timeline[0]["mtime"],
        "wall_end": timeline[-1]["mtime"],
        "frames": timeline,
        "frames_sha256": {
            e["file"]: hashlib.sha256((shots_dir / e["file"]).read_bytes()).hexdigest()
            for e in timeline
        },
    }
    out_mp4.with_suffix(".mp4.manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2)
    )
    concat_list.unlink(missing_ok=True)
    print(f"ok {out_mp4} frames={len(timeline)} span={timeline[0]['mtime']}..{timeline[-1]['mtime']}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
