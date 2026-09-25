from pathlib import Path

import joblib
import numpy as np
import pandas as pd

from services.feature_engineering import build_features


PROBABILITY_EPSILON = 1e-6


class PredictionError(Exception):
    pass


def probability_logit(probabilities):
    probabilities = np.asarray(probabilities, dtype="float64")
    probabilities = np.clip(
        probabilities,
        PROBABILITY_EPSILON,
        1 - PROBABILITY_EPSILON,
    )
    return np.log(probabilities / (1 - probabilities)).reshape(-1, 1)


def risk_level(probability):
    if probability < 0.10:
        return "Very Low"
    if probability < 0.30:
        return "Low"
    if probability < 0.50:
        return "Medium"
    if probability < 0.80:
        return "High"
    return "Very High"


class MLPredictionService:
    def __init__(self, model_path):
        self.model_path = Path(model_path)
        self.package = None
        self.model = None
        self.calibrator = None
        self.threshold = None
        self.model_name = None
        self.ready = False
        self.load_error = None
        self.load()

    def load(self):
        self.ready = False
        self.load_error = None

        if not self.model_path.exists():
            self.load_error = (
                f"Missing ML model: {self.model_path.name}. "
                "Copy it into the model_artifacts folder."
            )
            return

        try:
            package = joblib.load(self.model_path)
            if not isinstance(package, dict):
                raise PredictionError("The ML model file does not contain a model package.")
            if "model" not in package or "threshold" not in package:
                raise PredictionError("The ML model package is missing model or threshold.")
            if not hasattr(package["model"], "predict_proba"):
                raise PredictionError("The saved ML model does not support predict_proba().")

            self.package = package
            self.model = package["model"]
            self.calibrator = package.get("calibrator")
            self.threshold = float(package["threshold"])
            self.model_name = str(package.get("model_name", "Fraud Detection Model"))
            self.ready = True
        except Exception as error:
            self.load_error = f"Could not load {self.model_path.name}: {error}"

    def predict(self, transaction):
        if not self.ready:
            raise PredictionError(self.load_error or "The ML model is not ready.")

        try:
            raw_frame = pd.DataFrame([transaction])
            features = build_features(raw_frame)
            raw_score = float(self.model.predict_proba(features)[0, 1])

            if self.calibrator is not None:
                calibrated_probability = float(
                    self.calibrator.predict_proba(
                        probability_logit([raw_score])
                    )[0, 1]
                )
            else:
                calibrated_probability = raw_score

            calibrated_probability = float(
                np.clip(calibrated_probability, 0.0, 1.0)
            )
            prediction = int(calibrated_probability >= self.threshold)

            return {
                "model_name": self.model_name,
                "raw_model_score": raw_score,
                "calibrated_fraud_risk": calibrated_probability,
                "decision_threshold": self.threshold,
                "ml_prediction": "FRAUD" if prediction else "GENUINE",
                "risk_level": risk_level(calibrated_probability),
                "hour": int(features.iloc[0]["hour"]),
                "day": int(features.iloc[0]["day"]),
            }
        except PredictionError:
            raise
        except Exception as error:
            raise PredictionError(f"The ML model could not process this transaction: {error}") from error
