#!/usr/bin/env python3
from __future__ import annotations

import math
import subprocess
import tempfile
import wave
from dataclasses import dataclass
from pathlib import Path

import numpy as np


SAMPLE_RATE = 44_100
UI_DIR = Path(
    "/Users/brsama/code/GitHub/Sparkle-project/mobile/assets/audio/ui"
)
AMBIENT_DIR = Path(
    "/Users/brsama/code/GitHub/Sparkle-project/mobile/assets/audio/ambient"
)


@dataclass(frozen=True)
class SoundRecipe:
    path: Path
    duration: float
    kind: str


def main() -> None:
    UI_DIR.mkdir(parents=True, exist_ok=True)
    AMBIENT_DIR.mkdir(parents=True, exist_ok=True)

    recipes = [
        SoundRecipe(UI_DIR / "tap.ogg", 0.06, "tap"),
        SoundRecipe(UI_DIR / "toggle.ogg", 0.08, "toggle"),
        SoundRecipe(UI_DIR / "select.ogg", 0.09, "select"),
        SoundRecipe(UI_DIR / "nav.ogg", 0.18, "nav"),
        SoundRecipe(UI_DIR / "sheet_open.ogg", 0.22, "sheet_open"),
        SoundRecipe(UI_DIR / "dialog_open.ogg", 0.20, "dialog_open"),
        SoundRecipe(UI_DIR / "confirm.ogg", 0.18, "confirm"),
        SoundRecipe(UI_DIR / "success.ogg", 0.32, "success"),
        SoundRecipe(UI_DIR / "warning.ogg", 0.26, "warning"),
        SoundRecipe(UI_DIR / "error.ogg", 0.26, "error"),
        SoundRecipe(UI_DIR / "achievement_common.ogg", 0.28, "achievement_common"),
        SoundRecipe(UI_DIR / "achievement_rare.ogg", 0.36, "achievement_rare"),
        SoundRecipe(UI_DIR / "achievement_epic.ogg", 0.48, "achievement_epic"),
        SoundRecipe(
            UI_DIR / "achievement_legendary.ogg",
            0.68,
            "achievement_legendary",
        ),
        SoundRecipe(UI_DIR / "star_unlock.ogg", 0.52, "star_unlock"),
        SoundRecipe(UI_DIR / "focus_complete.ogg", 0.44, "focus_complete"),
        SoundRecipe(UI_DIR / "streak.ogg", 0.40, "streak"),
        SoundRecipe(UI_DIR / "checkin.ogg", 0.30, "checkin"),
        SoundRecipe(UI_DIR / "message_send.ogg", 0.08, "message_send"),
        SoundRecipe(UI_DIR / "ai_start.ogg", 0.16, "ai_start"),
        SoundRecipe(UI_DIR / "card_flip.ogg", 0.12, "card_flip"),
        SoundRecipe(UI_DIR / "drag_start.ogg", 0.09, "drag_start"),
        SoundRecipe(UI_DIR / "drag_drop.ogg", 0.11, "drag_drop"),
        SoundRecipe(UI_DIR / "button1.ogg", 0.07, "tap"),
        SoundRecipe(UI_DIR / "button2.ogg", 0.09, "confirm"),
        SoundRecipe(UI_DIR / "on.ogg", 0.08, "toggle"),
        SoundRecipe(UI_DIR / "off.ogg", 0.08, "select"),
        SoundRecipe(UI_DIR / "complete.ogg", 0.32, "success"),
        SoundRecipe(AMBIENT_DIR / "rain.ogg", 32.0, "ambient_rain"),
        SoundRecipe(AMBIENT_DIR / "white_noise.ogg", 32.0, "ambient_white_noise"),
        SoundRecipe(AMBIENT_DIR / "cafe.ogg", 32.0, "ambient_cafe"),
        SoundRecipe(AMBIENT_DIR / "piano.ogg", 32.0, "ambient_piano"),
    ]

    for recipe in recipes:
        audio = synthesize(recipe.kind, recipe.duration)
        write_ogg(recipe.path, audio)

    print(f"Generated {len(recipes)} audio assets.")


def synthesize(kind: str, duration: float) -> np.ndarray:
    return normalize(
        {
            "tap": ui_tap(duration),
            "toggle": ui_toggle(duration),
            "select": ui_select(duration),
            "nav": ui_nav(duration),
            "sheet_open": ui_sheet_open(duration),
            "dialog_open": ui_dialog_open(duration),
            "confirm": ui_confirm(duration),
            "success": ui_success(duration),
            "warning": ui_warning(duration),
            "error": ui_error(duration),
            "achievement_common": ui_achievement(duration, 0),
            "achievement_rare": ui_achievement(duration, 1),
            "achievement_epic": ui_achievement(duration, 2),
            "achievement_legendary": ui_achievement(duration, 3),
            "star_unlock": ui_star_unlock(duration),
            "focus_complete": ui_focus_complete(duration),
            "streak": ui_streak(duration),
            "checkin": ui_checkin(duration),
            "message_send": ui_message_send(duration),
            "ai_start": ui_ai_start(duration),
            "card_flip": ui_card_flip(duration),
            "drag_start": ui_drag_start(duration),
            "drag_drop": ui_drag_drop(duration),
            "ambient_rain": ambient_rain(duration),
            "ambient_white_noise": ambient_white_noise(duration),
            "ambient_cafe": ambient_cafe(duration),
            "ambient_piano": ambient_piano(duration),
        }[kind]
    )


def normalize(signal: np.ndarray, peak: float = 0.92) -> np.ndarray:
    maximum = np.max(np.abs(signal))
    if maximum <= 1e-6:
        return signal
    return signal / maximum * peak


def seconds(value: float) -> int:
    return max(1, int(SAMPLE_RATE * value))


def time_axis(duration: float) -> np.ndarray:
    return np.linspace(0, duration, seconds(duration), endpoint=False)


def envelope(duration: float, attack: float, decay: float) -> np.ndarray:
    t = time_axis(duration)
    env = np.ones_like(t)
    attack_samples = min(len(t), max(1, seconds(attack)))
    decay_samples = min(len(t), max(1, seconds(decay)))
    env[:attack_samples] = np.linspace(0, 1, attack_samples, endpoint=False)
    env *= np.exp(-np.linspace(0, 6, len(t)) * max(duration / max(decay, 1e-3), 0.25))
    env[-decay_samples:] *= np.linspace(1, 0, decay_samples)
    return env


def sine(freq: float | np.ndarray, duration: float, phase: float = 0.0) -> np.ndarray:
    t = time_axis(duration)
    if np.isscalar(freq):
      return np.sin(2 * np.pi * float(freq) * t + phase)
    phase_curve = np.cumsum(freq) / SAMPLE_RATE
    return np.sin(2 * np.pi * phase_curve + phase)


def chirp(start: float, end: float, duration: float) -> np.ndarray:
    t = time_axis(duration)
    freqs = np.linspace(start, end, len(t))
    return sine(freqs, duration)


def bell(freq: float, duration: float, decay: float = 4.0) -> np.ndarray:
    t = time_axis(duration)
    base = np.sin(2 * np.pi * freq * t)
    overtone = 0.45 * np.sin(2 * np.pi * freq * 2.01 * t)
    shimmer = 0.22 * np.sin(2 * np.pi * freq * 3.97 * t)
    env = np.exp(-np.linspace(0, decay, len(t)))
    env[: max(1, seconds(0.01))] = np.linspace(0, 1, max(1, seconds(0.01)))
    return (base + overtone + shimmer) * env


def periodic_noise(duration: float, slope: float, seed: int) -> np.ndarray:
    rng = np.random.default_rng(seed)
    count = seconds(duration)
    freqs = np.fft.rfftfreq(count, 1 / SAMPLE_RATE)
    spectrum = np.zeros(len(freqs), dtype=np.complex128)
    nonzero = freqs > 0
    scale = np.ones_like(freqs)
    scale[nonzero] = 1 / np.power(freqs[nonzero], slope)
    phases = rng.uniform(0, 2 * np.pi, len(freqs))
    magnitudes = rng.uniform(0.6, 1.0, len(freqs)) * scale
    spectrum[nonzero] = magnitudes[nonzero] * np.exp(1j * phases[nonzero])
    result = np.fft.irfft(spectrum, n=count)
    return normalize(result, peak=1.0)


def add_tone(signal: np.ndarray, start: float, tone_signal: np.ndarray, gain: float) -> None:
    offset = seconds(start)
    end = min(len(signal), offset + len(tone_signal))
    if end <= offset:
        return
    signal[offset:end] += tone_signal[: end - offset] * gain


def mix(duration: float, *layers: tuple[np.ndarray, float]) -> np.ndarray:
    signal = np.zeros(seconds(duration))
    for tone_signal, gain in layers:
        signal[: min(len(signal), len(tone_signal))] += tone_signal[: len(signal)] * gain
    return signal


def make_loopable(signal: np.ndarray, fade_seconds: float = 1.2) -> np.ndarray:
    fade_samples = min(len(signal) // 4, seconds(fade_seconds))
    if fade_samples <= 0:
        return signal
    fade_in = np.linspace(0, 1, fade_samples)
    fade_out = np.linspace(1, 0, fade_samples)
    blended = signal[-fade_samples:] * fade_out + signal[:fade_samples] * fade_in
    signal = signal.copy()
    signal[:fade_samples] = blended
    signal[-fade_samples:] = blended
    return signal


def ui_tap(duration: float) -> np.ndarray:
    hit = bell(1820, duration, decay=10)
    return hit * envelope(duration, 0.002, 0.05)


def ui_toggle(duration: float) -> np.ndarray:
    pulse_a = bell(760, duration * 0.6, decay=8)
    pulse_b = bell(1020, duration * 0.5, decay=8)
    signal = np.zeros(seconds(duration))
    add_tone(signal, 0.0, pulse_a, 0.85)
    add_tone(signal, duration * 0.25, pulse_b, 0.75)
    return signal


def ui_select(duration: float) -> np.ndarray:
    return mix(
        duration,
        (bell(980, duration, decay=8), 0.7),
        (bell(1480, duration * 0.8, decay=9), 0.35),
    ) * envelope(duration, 0.003, 0.08)


def ui_nav(duration: float) -> np.ndarray:
    sweep = chirp(420, 980, duration) * envelope(duration, 0.005, duration)
    airy = periodic_noise(duration, 0.2, 3) * envelope(duration, 0.01, duration)
    return 0.62 * sweep + 0.12 * airy


def ui_sheet_open(duration: float) -> np.ndarray:
    lift = chirp(260, 840, duration) * envelope(duration, 0.01, duration)
    glow = bell(620, duration * 0.9, decay=6)
    return mix(duration, (lift, 0.55), (glow, 0.22))


def ui_dialog_open(duration: float) -> np.ndarray:
    return 0.55 * chirp(540, 1040, duration) * envelope(duration, 0.006, duration)


def ui_confirm(duration: float) -> np.ndarray:
    signal = np.zeros(seconds(duration))
    add_tone(signal, 0.0, bell(720, duration * 0.75, decay=7), 0.85)
    add_tone(signal, duration * 0.12, bell(1080, duration * 0.62, decay=7), 0.72)
    return signal


def ui_success(duration: float) -> np.ndarray:
    signal = np.zeros(seconds(duration))
    notes = [640, 960, 1280]
    for idx, note in enumerate(notes):
        add_tone(signal, idx * duration * 0.14, bell(note, duration * 0.52, decay=6), 0.85)
    return signal


def ui_warning(duration: float) -> np.ndarray:
    signal = np.zeros(seconds(duration))
    add_tone(signal, 0.0, bell(320, duration * 0.8, decay=7), 0.9)
    add_tone(signal, duration * 0.16, bell(280, duration * 0.7, decay=8), 0.78)
    return signal


def ui_error(duration: float) -> np.ndarray:
    signal = np.zeros(seconds(duration))
    for idx, note in enumerate([540, 430, 330]):
        add_tone(signal, idx * duration * 0.16, bell(note, duration * 0.46, decay=8), 0.82)
    return signal


def ui_achievement(duration: float, tier: int) -> np.ndarray:
    tiers = [
        [740, 980],
        [720, 940, 1240],
        [720, 980, 1320, 1620],
        [660, 920, 1240, 1560, 1860],
    ]
    signal = np.zeros(seconds(duration))
    notes = tiers[tier]
    spacing = duration / max(len(notes) + 1, 2)
    for idx, note in enumerate(notes):
        add_tone(
            signal,
            idx * spacing * 0.78,
            bell(note, duration * (0.45 if tier < 2 else 0.5), decay=5.2 - tier * 0.4),
            0.75 + tier * 0.05,
        )
    if tier == 3:
        add_tone(signal, duration * 0.36, bell(2200, duration * 0.45, decay=6), 0.35)
    return signal


def ui_star_unlock(duration: float) -> np.ndarray:
    signal = np.zeros(seconds(duration))
    for idx, note in enumerate([820, 1240, 1640]):
        add_tone(signal, idx * duration * 0.12, bell(note, duration * 0.6, decay=5), 0.82)
    return signal + 0.08 * periodic_noise(duration, 0.4, 9) * envelope(duration, 0.01, duration)


def ui_focus_complete(duration: float) -> np.ndarray:
    pad = bell(540, duration, decay=4.5)
    rise = bell(810, duration * 0.72, decay=4.0)
    return mix(duration, (pad, 0.75), (rise, 0.35))


def ui_streak(duration: float) -> np.ndarray:
    signal = np.zeros(seconds(duration))
    for idx, note in enumerate([540, 720, 1080]):
        add_tone(signal, idx * duration * 0.14, bell(note, duration * 0.55, decay=5.5), 0.88)
    return signal


def ui_checkin(duration: float) -> np.ndarray:
    return mix(
        duration,
        (bell(900, duration * 0.9, decay=6), 0.85),
        (bell(1320, duration * 0.65, decay=6), 0.3),
    )


def ui_message_send(duration: float) -> np.ndarray:
    return 0.85 * bell(1280, duration, decay=11)


def ui_ai_start(duration: float) -> np.ndarray:
    sweep = chirp(460, 1260, duration)
    air = periodic_noise(duration, 0.35, 14)
    return (0.52 * sweep + 0.08 * air) * envelope(duration, 0.01, duration)


def ui_card_flip(duration: float) -> np.ndarray:
    return (
        0.38 * chirp(980, 420, duration)
        + 0.22 * periodic_noise(duration, 0.1, 15)
    ) * envelope(duration, 0.004, duration)


def ui_drag_start(duration: float) -> np.ndarray:
    return 0.72 * bell(560, duration, decay=10)


def ui_drag_drop(duration: float) -> np.ndarray:
    return mix(
        duration,
        (bell(720, duration, decay=9), 0.74),
        (bell(1120, duration * 0.7, decay=9), 0.24),
    )


def ambient_rain(duration: float) -> np.ndarray:
    base = periodic_noise(duration, 0.65, 101)
    mist = periodic_noise(duration, 0.25, 102)
    drops = np.maximum(periodic_noise(duration, 0.05, 103), 0) ** 3
    return make_loopable(0.34 * base + 0.12 * mist + 0.08 * drops)


def ambient_white_noise(duration: float) -> np.ndarray:
    wide = periodic_noise(duration, 0.0, 201)
    warm = periodic_noise(duration, 0.3, 202)
    return make_loopable(0.16 * wide + 0.18 * warm)


def ambient_cafe(duration: float) -> np.ndarray:
    room = periodic_noise(duration, 0.7, 301)
    murmur = periodic_noise(duration, 0.45, 302)
    murmur = np.tanh(murmur * 1.6) * 0.16
    signal = 0.24 * room + murmur
    for start, freq in [(4.2, 1200), (11.7, 980), (18.3, 1320), (26.4, 860)]:
        add_tone(signal, start, bell(freq, 0.22, decay=10), 0.14)
    return make_loopable(signal)


def ambient_piano(duration: float) -> np.ndarray:
    pad = periodic_noise(duration, 0.9, 401) * 0.12
    signal = pad.copy()
    notes = [
        (1.0, 392),
        (4.5, 440),
        (8.0, 523.25),
        (12.0, 659.25),
        (16.0, 523.25),
        (20.0, 440),
        (24.0, 392),
        (28.0, 349.23),
    ]
    for start, note in notes:
        add_tone(signal, start, bell(note, 3.4, decay=3.0), 0.32)
        add_tone(signal, start + 0.4, bell(note * 1.5, 2.8, decay=3.2), 0.12)
    return make_loopable(signal, fade_seconds=1.6)


def write_ogg(path: Path, signal: np.ndarray) -> None:
    signal = np.clip(signal, -1.0, 1.0)
    stereo = np.column_stack([signal, signal])
    pcm = (stereo * 32767).astype(np.int16)
    with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as tmp:
        tmp_path = Path(tmp.name)
    try:
        with wave.open(str(tmp_path), "wb") as wav_file:
            wav_file.setnchannels(2)
            wav_file.setsampwidth(2)
            wav_file.setframerate(SAMPLE_RATE)
            wav_file.writeframes(pcm.tobytes())
        subprocess.run(
            [
                "ffmpeg",
                "-y",
                "-loglevel",
                "error",
                "-i",
                str(tmp_path),
                "-ar",
                str(SAMPLE_RATE),
                "-ac",
                "2",
                "-c:a",
                "vorbis",
                "-strict",
                "-2",
                "-b:a",
                "128k",
                str(path),
            ],
            check=True,
        )
    finally:
        tmp_path.unlink(missing_ok=True)


if __name__ == "__main__":
    main()
