"""DPO trainer — numpy-only preference optimization.

Implements the DPO loss from Rafailov et al. (2023):
  L_DPO = -E[ log σ(β · (s_θ(x, y_w) - s_θ(x, y_l))) ]

Uses a linear scoring model s_θ(x, y) = w_y · x (dot product of strategy
weight vector and context feature vector). Reference model is frozen initial
weights for uniform prior regularization.
"""
from __future__ import annotations

import json
import math
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import numpy as np

from ..sim.ai_behavior_classifier import AIBehaviorClass

_STRATEGY_ORDER = [e.value for e in AIBehaviorClass]
_N_STRATEGIES = len(_STRATEGY_ORDER)


@dataclass
class DPOTrainingConfig:
    """Hyperparameters for DPO training."""

    learning_rate: float = 0.01
    beta: float = 1.0               # DPO temperature (higher = more conservative)
    epochs: int = 20
    batch_size: int = 32
    l2_reg: float = 1e-4            # L2 regularization strength
    validation_split: float = 0.15  # fraction of data for validation
    early_stopping_patience: int = 5
    early_stopping_min_delta: float = 1e-4
    shuffle: bool = True
    seed: int = 42


@dataclass
class DPOTrainingResult:
    """Result of a DPO training run."""

    model: DPOModel
    train_loss_history: list[float]
    val_loss_history: list[float]
    best_epoch: int
    best_val_loss: float
    n_pairs_trained: int
    n_pairs_validated: int
    training_time_seconds: float
    converged: bool
    early_stopped: bool


# ── DPOModel ──────────────────────────────────────────

class DPOModel:
    """Linear scoring model: s(x, y) = W[y] · x.

    W is (n_strategies × feature_dim). Each row is a strategy's weight vector.
    The score for a (context, response) pair is the dot product of the context
    vector and the behavior strategy's weight row.
    """

    def __init__(self, feature_dim: int, weights: np.ndarray | None = None):
        self.feature_dim = feature_dim
        if weights is not None:
            self.W = weights.astype(np.float64)
        else:
            rng = np.random.RandomState(42)
            self.W = rng.randn(_N_STRATEGIES, feature_dim).astype(np.float64) * 0.01

    @property
    def n_strategies(self) -> int:
        return _N_STRATEGIES

    def score(self, context_vector: np.ndarray, strategy_idx: int) -> float:
        """Score a context vector under a specific strategy."""
        return float(np.dot(self.W[strategy_idx], context_vector))

    def score_all(self, context_vector: np.ndarray) -> np.ndarray:
        """Score a context vector under all strategies. Returns (n_strategies,)."""
        return self.W @ context_vector

    def best_strategy(self, context_vector: np.ndarray) -> tuple[int, float]:
        """Return (strategy_idx, score) of the highest-scoring strategy."""
        scores = self.score_all(context_vector)
        idx = int(np.argmax(scores))
        return idx, float(scores[idx])

    def strategy_scores(self, context_vector: np.ndarray) -> dict[str, float]:
        """Score all strategies, returned as {strategy_name: score}."""
        scores = self.score_all(context_vector)
        return {_STRATEGY_ORDER[i]: float(scores[i]) for i in range(_N_STRATEGIES)}

    def copy(self) -> DPOModel:
        """Deep copy."""
        return DPOModel(self.feature_dim, weights=self.W.copy())

    def save(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)
        np.savez_compressed(
            path,
            W=self.W,
            feature_dim=self.feature_dim,
            strategy_order=np.array(_STRATEGY_ORDER),
        )

    @classmethod
    def load(cls, path: Path) -> DPOModel:
        data = np.load(path)
        model = cls(feature_dim=int(data["feature_dim"]), weights=data["W"])
        return model

    def to_dict(self) -> dict[str, Any]:
        return {
            "feature_dim": self.feature_dim,
            "n_strategies": self.n_strategies,
            "strategies": _STRATEGY_ORDER,
        }


# ── DPOTrainer ────────────────────────────────────────

class DPOTrainer:
    """Trains a DPOModel from preference pairs using numpy SGD."""

    def __init__(self, config: DPOTrainingConfig | None = None):
        self.config = config or DPOTrainingConfig()

    def train(self, pairs: list[dict[str, Any]]) -> DPOTrainingResult:
        """Train a DPO model from preference pairs.

        Each pair dict must have:
          - context_vector: list[float]
          - chosen_behavior: str (AIBehaviorClass value)
          - rejected_behavior: str (AIBehaviorClass value)
        """
        t0 = time.time()
        cfg = self.config

        if not pairs:
            return self._empty_result(t0)

        # Determine feature dim from first pair
        feature_dim = len(pairs[0].get("context_vector", []))
        if feature_dim == 0:
            return self._empty_result(t0)

        # Build training arrays
        X, yw_beh, yl_beh = self._build_arrays(pairs, feature_dim)

        # Train/val split
        n = len(X)
        n_val = max(1, int(n * cfg.validation_split))
        indices = np.arange(n)
        rng = np.random.RandomState(cfg.seed)
        rng.shuffle(indices)

        val_idx = indices[:n_val]
        train_idx = indices[n_val:]

        X_train, yw_train, yl_train = X[train_idx], yw_beh[train_idx], yl_beh[train_idx]
        X_val, yw_val, yl_val = X[val_idx], yw_beh[val_idx], yl_beh[val_idx]

        # Initialize model + reference (frozen)
        model = DPOModel(feature_dim)
        ref_model = model.copy()

        train_losses: list[float] = []
        val_losses: list[float] = []
        best_val_loss = float("inf")
        best_epoch = 0
        best_W = model.W.copy()
        patience_counter = 0

        for epoch in range(cfg.epochs):
            # Shuffle training data
            if cfg.shuffle:
                perm = rng.permutation(len(X_train))
                X_train = X_train[perm]
                yw_train = yw_train[perm]
                yl_train = yl_train[perm]

            # Mini-batch SGD
            epoch_loss = 0.0
            n_batches = 0
            for b_start in range(0, len(X_train), cfg.batch_size):
                b_end = min(b_start + cfg.batch_size, len(X_train))
                Xb = X_train[b_start:b_end]
                ywb = yw_train[b_start:b_end]
                ylb = yl_train[b_start:b_end]

                loss, grad = self._dpo_loss_grad(model, ref_model, Xb, ywb, ylb, cfg.beta, cfg.l2_reg)
                model.W -= cfg.learning_rate * grad
                epoch_loss += loss
                n_batches += 1

            avg_train_loss = epoch_loss / max(n_batches, 1)
            train_losses.append(avg_train_loss)

            # Validation
            val_loss, _ = self._dpo_loss_grad(model, ref_model, X_val, yw_val, yl_val, cfg.beta, 0.0)
            val_losses.append(val_loss)

            # Early stopping check
            if val_loss < best_val_loss - cfg.early_stopping_min_delta:
                best_val_loss = val_loss
                best_epoch = epoch
                best_W = model.W.copy()
                patience_counter = 0
            else:
                patience_counter += 1

            if patience_counter >= cfg.early_stopping_patience:
                model.W = best_W
                return DPOTrainingResult(
                    model=model,
                    train_loss_history=train_losses,
                    val_loss_history=val_losses,
                    best_epoch=best_epoch,
                    best_val_loss=best_val_loss,
                    n_pairs_trained=len(train_idx),
                    n_pairs_validated=len(val_idx),
                    training_time_seconds=round(time.time() - t0, 3),
                    converged=True,
                    early_stopped=True,
                )

        # Restore best weights
        model.W = best_W
        return DPOTrainingResult(
            model=model,
            train_loss_history=train_losses,
            val_loss_history=val_losses,
            best_epoch=best_epoch,
            best_val_loss=best_val_loss,
            n_pairs_trained=len(train_idx),
            n_pairs_validated=len(val_idx),
            training_time_seconds=round(time.time() - t0, 3),
            converged=patience_counter < cfg.early_stopping_patience,
            early_stopped=False,
        )

    # ── Internals ──────────────────────────────────────

    def _build_arrays(
        self, pairs: list[dict[str, Any]], feature_dim: int
    ) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
        """Convert pair dicts to numpy arrays. Returns (X, yw_idx, yl_idx)."""
        n = len(pairs)
        X = np.zeros((n, feature_dim), dtype=np.float64)
        yw_idx = np.zeros(n, dtype=np.int64)
        yl_idx = np.zeros(n, dtype=np.int64)

        for i, pair in enumerate(pairs):
            cv = pair.get("context_vector", [])
            if isinstance(cv, str):
                cv = json.loads(cv)
            for j, v in enumerate(cv[:feature_dim]):
                X[i, j] = float(v)

            chosen_beh = pair.get("chosen_behavior", "neutral")
            rejected_beh = pair.get("rejected_behavior", "neutral")
            yw_idx[i] = self._behavior_to_idx(chosen_beh)
            yl_idx[i] = self._behavior_to_idx(rejected_beh)

        return X, yw_idx, yl_idx

    @staticmethod
    def _behavior_to_idx(behavior: str) -> int:
        try:
            return _STRATEGY_ORDER.index(behavior)
        except ValueError:
            return _STRATEGY_ORDER.index("neutral")

    def _dpo_loss_grad(
        self,
        model: DPOModel,
        ref_model: DPOModel,
        X: np.ndarray,
        yw_idx: np.ndarray,
        yl_idx: np.ndarray,
        beta: float,
        l2_reg: float,
    ) -> tuple[float, np.ndarray]:
        """Compute DPO loss and gradient for a batch.

        Returns (loss, gradient_wrt_W).
        """
        n = X.shape[0]
        feature_dim = X.shape[1]
        grad = np.zeros_like(model.W)

        # Scores under current model
        # s_w[b] = W[yw_idx[b]] · X[b]
        s_w = np.sum(model.W[yw_idx] * X, axis=1)  # (n,)
        s_l = np.sum(model.W[yl_idx] * X, axis=1)  # (n,)

        # Scores under reference model
        s_w_ref = np.sum(ref_model.W[yw_idx] * X, axis=1)
        s_l_ref = np.sum(ref_model.W[yl_idx] * X, axis=1)

        # DPO implicit reward difference
        # Δ = β * ((s_w - s_l) - (s_w_ref - s_l_ref))
        diff = beta * ((s_w - s_l) - (s_w_ref - s_l_ref))

        # For numerical stability
        diff = np.clip(diff, -50.0, 50.0)

        # Loss = -log σ(diff) = log(1 + exp(-diff))
        # stable: where diff > 0, use log(1+exp(-diff)); else use -diff + log(1+exp(diff))
        pos_mask = diff > 0
        neg_mask = ~pos_mask

        losses = np.zeros(n)
        losses[pos_mask] = np.log(1.0 + np.exp(-diff[pos_mask]))
        losses[neg_mask] = -diff[neg_mask] + np.log(1.0 + np.exp(diff[neg_mask]))
        loss = float(np.mean(losses))

        # Gradient: -σ(-diff) * β * (∇s_w - ∇s_l)
        # ∇s_w wrt W[yw_idx[i]] = X[i], wrt W[yl_idx[i]] = 0
        # ∇s_l wrt W[yl_idx[i]] = X[i], wrt W[yw_idx[i]] = 0
        sigma_neg = 1.0 / (1.0 + np.exp(diff))  # σ(-diff), shape (n,)

        for i in range(n):
            coef = -sigma_neg[i] * beta / n
            grad[yw_idx[i]] += coef * X[i]
            grad[yl_idx[i]] -= coef * X[i]

        # L2 regularization
        if l2_reg > 0:
            loss += l2_reg * np.sum(model.W ** 2)
            grad += 2.0 * l2_reg * model.W

        return loss, grad

    def _empty_result(self, t0: float) -> DPOTrainingResult:
        return DPOTrainingResult(
            model=DPOModel(1),
            train_loss_history=[],
            val_loss_history=[],
            best_epoch=0,
            best_val_loss=float("inf"),
            n_pairs_trained=0,
            n_pairs_validated=0,
            training_time_seconds=round(time.time() - t0, 3),
            converged=False,
            early_stopped=False,
        )
