import sys
import os
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Dict, Any, Optional

# Add backend to path to allow importing app modules
sys.path.append(os.path.join(os.getcwd(), 'backend'))

from app.learning.persistent_bayesian_learner import PersistentBayesianLearner
from app.learning.ab_test_framework import ABTestFramework
from app.core.cache import cache_service

app = FastAPI(title="Sparkle Learning Service", version="1.0.0")

class UpdateBeliefRequest(BaseModel):
    user_id: str
    source: str
    target: str
    success: bool

class AssignmentRequest(BaseModel):
    user_id: str
    experiment_id: str
    variants: List[str]

class TrackMetricRequest(BaseModel):
    user_id: str
    experiment_id: str
    metric_name: str
    value: float

@app.on_event("startup")
async def startup_event():
    await cache_service.init_redis()

@app.get("/health")
async def health_check():
    return {"status": "healthy", "service": "learning"}

@app.post("/update_belief")
async def update_belief(req: UpdateBeliefRequest):
    try:
        learner = PersistentBayesianLearner(cache_service.redis, req.user_id)
        await learner.update(req.source, req.target, req.success)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/stats/{user_id}")
async def get_stats(user_id: str):
    try:
        learner = PersistentBayesianLearner(cache_service.redis, user_id)
        stats = await learner.get_stats()
        return stats
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ab/assign")
async def assign_variant(req: AssignmentRequest):
    try:
        ab = ABTestFramework(cache_service.redis)
        # Ensure experiment exists if not we might want to create it, 
        # but for now we assume it exists or we handle the logic. 
        # ABTestFramework.assign_variant takes user_id, exp_id.
        # But if we want to support dynamic creation we need to call create_experiment first.
        # Here we just match the signature.
        variant = await ab.assign_variant(req.user_id, req.experiment_id)
        return {"variant": variant}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/ab/track")
async def track_metric(req: TrackMetricRequest):
    try:
        ab = ABTestFramework(cache_service.redis)
        # record_outcome(self, exp_id: str, variant: str, user_id: str, metrics: Dict)
        # We need variant. If client doesn't send it, we re-assign/lookup.
        variant = await ab.assign_variant(req.user_id, req.experiment_id)
        
        metrics = {req.metric_name: req.value}
        await ab.record_outcome(req.experiment_id, variant, req.user_id, metrics)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
