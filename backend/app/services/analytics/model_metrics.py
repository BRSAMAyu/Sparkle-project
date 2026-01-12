from app.core.metrics import get_or_create_metric
from prometheus_client import Gauge

BKT_AUC = get_or_create_metric(
    Gauge,
    "sparkle_bkt_auc",
    "BKT AUC by cohort",
    ["age_bucket", "device_tier", "subject_id"]
)

IRT_RMSE = get_or_create_metric(
    Gauge,
    "sparkle_irt_rmse",
    "IRT RMSE by cohort",
    ["age_bucket", "device_tier", "subject_id"]
)


def record_bkt_auc(value: float, age_bucket: str, device_tier: str, subject_id: str) -> None:
    BKT_AUC.labels(age_bucket=age_bucket, device_tier=device_tier, subject_id=subject_id).set(value)


def record_irt_rmse(value: float, age_bucket: str, device_tier: str, subject_id: str) -> None:
    IRT_RMSE.labels(age_bucket=age_bucket, device_tier=device_tier, subject_id=subject_id).set(value)
