from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TraitCalibrationSample:
    language: str
    style: str
    text: str
    expected_directions: dict[str, int]


CALIBRATION_SAMPLES: tuple[TraitCalibrationSample, ...] = (
    TraitCalibrationSample(
        language="zh-CN",
        style="structured_planner",
        text="我喜欢先把任务拆成步骤，再按清单逐个推进。临时变化太多会让我分心。",
        expected_directions={"conscientiousness": 1, "neuroticism": 0},
    ),
    TraitCalibrationSample(
        language="en-US",
        style="social_energized",
        text="Brainstorming with people gives me energy. I usually think better after talking ideas out loud.",
        expected_directions={"extraversion": 1, "agreeableness": 1},
    ),
    TraitCalibrationSample(
        language="ja-JP",
        style="quiet_reflective",
        text="私は一人で静かに考える時間が必要です。新しい考えを試すのは好きですが、急かされるのは苦手です。",
        expected_directions={"openness": 1, "extraversion": -1},
    ),
    TraitCalibrationSample(
        language="es-ES",
        style="steady_low_dramatic",
        text="Prefiero mantener un ritmo constante y no suelo alterarme cuando cambian los planes.",
        expected_directions={"conscientiousness": 1, "neuroticism": -1},
    ),
    TraitCalibrationSample(
        language="ar",
        style="warm_collaborative",
        text="أحب العمل مع الآخرين عندما يكون الهدف واضحا، وأحاول دائما الحفاظ على هدوء الفريق.",
        expected_directions={"agreeableness": 1, "conscientiousness": 1},
    ),
)
