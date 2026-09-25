import numpy as np
import pandas as pd


RAW_FEATURES = [
    "step",
    "type",
    "amount",
    "oldbalanceOrig",
    "oldbalanceDest",
]

NUMERIC_FEATURES = [
    "step",
    "amount",
    "oldbalanceOrig",
    "oldbalanceDest",
    "hour",
    "day",
    "log_amount",
    "orig_balance_to_amount_ratio",
    "dest_balance_to_amount_ratio",
    "insufficient_orig_balance",
    "orig_zero_balance",
    "dest_zero_balance",
]

CATEGORICAL_FEATURES = ["type"]
MODEL_FEATURES = NUMERIC_FEATURES + CATEGORICAL_FEATURES


def build_features(raw_frame):
    """Reproduce the feature engineering from the corrected training notebook."""
    missing = sorted(set(RAW_FEATURES) - set(raw_frame.columns))
    if missing:
        raise ValueError(f"Missing raw input columns: {missing}")

    features = raw_frame[RAW_FEATURES].copy()
    features["step"] = pd.to_numeric(features["step"], errors="raise").astype("int32")
    features["amount"] = pd.to_numeric(features["amount"], errors="raise").astype("float32")
    features["oldbalanceOrig"] = pd.to_numeric(
        features["oldbalanceOrig"], errors="raise"
    ).astype("float32")
    features["oldbalanceDest"] = pd.to_numeric(
        features["oldbalanceDest"], errors="raise"
    ).astype("float32")
    features["type"] = features["type"].astype("string")

    if (features["step"] < 1).any():
        raise ValueError("Step must be at least 1.")
    if (
        features[["amount", "oldbalanceOrig", "oldbalanceDest"]] < 0
    ).any().any():
        raise ValueError("Amount and balances must be non-negative.")

    features["hour"] = ((features["step"] - 1) % 24).astype("int8")
    features["day"] = (((features["step"] - 1) // 24) + 1).astype("int16")
    features["log_amount"] = np.log1p(features["amount"]).astype("float32")

    denominator = features["amount"] + np.float32(1.0)
    features["orig_balance_to_amount_ratio"] = (
        features["oldbalanceOrig"] / denominator
    ).clip(0, 1_000_000).astype("float32")
    features["dest_balance_to_amount_ratio"] = (
        features["oldbalanceDest"] / denominator
    ).clip(0, 1_000_000).astype("float32")

    features["insufficient_orig_balance"] = (
        features["oldbalanceOrig"] < features["amount"]
    ).astype("int8")
    features["orig_zero_balance"] = (
        features["oldbalanceOrig"] == 0
    ).astype("int8")
    features["dest_zero_balance"] = (
        features["oldbalanceDest"] == 0
    ).astype("int8")

    return features[MODEL_FEATURES]
