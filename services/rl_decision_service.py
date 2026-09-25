from pathlib import Path

import joblib
import numpy as np


class RLDecisionError(Exception):
    pass


def time_state(hour):
    hour = int(hour)
    if not 0 <= hour <= 23:
        raise RLDecisionError("Transaction hour must be between 0 and 23.")
    if hour < 6:
        return 0
    if hour < 12:
        return 1
    if hour < 18:
        return 2
    return 3


class RLDecisionService:
    def __init__(self, model_path):
        self.model_path = Path(model_path)
        self.package = None
        self.ready = False
        self.load_error = None
        self.load()

    def load(self):
        self.ready = False
        self.load_error = None

        if not self.model_path.exists():
            self.load_error = (
                f"Missing RL policy: {self.model_path.name}. "
                "Copy it into the model_artifacts folder."
            )
            return

        try:
            package = joblib.load(self.model_path)
            required_keys = {
                "q_table",
                "state_sample_counts",
                "actions",
                "fraud_risk_bins",
                "amount_bins",
                "minimum_state_samples",
            }
            if not isinstance(package, dict) or not required_keys.issubset(package):
                missing = sorted(required_keys - set(package if isinstance(package, dict) else {}))
                raise RLDecisionError(f"RL package is missing required values: {missing}")

            q_table = np.asarray(package["q_table"])
            if q_table.shape != (5, 5, 4, 4):
                raise RLDecisionError(
                    f"Unexpected Q-table shape {q_table.shape}; expected (5, 5, 4, 4)."
                )

            self.package = package
            self.ready = True
        except Exception as error:
            self.load_error = f"Could not load {self.model_path.name}: {error}"

    @staticmethod
    def _normalise_actions(actions):
        return {int(key): str(value) for key, value in actions.items()}

    @staticmethod
    def _fallback_action(probability, action_to_id):
        if probability < 0.10:
            return action_to_id["APPROVE"]
        if probability < 0.30:
            return action_to_id["ADDITIONAL_AUTH"]
        if probability < 0.70:
            return action_to_id["MANUAL_REVIEW"]
        return action_to_id["BLOCK"]

    def decide(self, fraud_probability, amount, hour):
        if not self.ready:
            raise RLDecisionError(self.load_error or "The RL policy is not ready.")

        try:
            probability = float(np.clip(fraud_probability, 0.0, 1.0))
            amount = float(amount)

            q_table = np.asarray(self.package["q_table"], dtype="float64")
            state_counts = np.asarray(self.package["state_sample_counts"])
            risk_bins = np.asarray(self.package["fraud_risk_bins"], dtype="float64")
            amount_bins = np.asarray(self.package["amount_bins"], dtype="float64")
            actions = self._normalise_actions(self.package["actions"])
            action_to_id = {
                name: action_id for action_id, name in actions.items()
            }
            min_samples = int(self.package["minimum_state_samples"])

            state = (
                int(np.searchsorted(risk_bins, probability, side="right")),
                int(np.searchsorted(amount_bins, amount, side="right")),
                time_state(hour),
            )
            q_values = q_table[state]
            learned_action_id = int(np.argmax(q_values))
            state_sample_count = int(state_counts[state])

            if state_sample_count < min_samples:
                final_action_id = self._fallback_action(probability, action_to_id)
                decision_source = "SPARSE_STATE_FALLBACK"
            else:
                final_action_id = learned_action_id
                decision_source = "LEARNED_Q_POLICY"

            if probability >= 0.80 and final_action_id in {
                action_to_id["APPROVE"],
                action_to_id["ADDITIONAL_AUTH"],
            }:
                final_action_id = action_to_id["BLOCK"]
                decision_source += "+VERY_HIGH_RISK_GUARDRAIL"
            elif probability >= 0.50 and final_action_id == action_to_id["APPROVE"]:
                final_action_id = action_to_id["MANUAL_REVIEW"]
                decision_source += "+HIGH_RISK_GUARDRAIL"

            return {
                "state": state,
                "state_sample_count": state_sample_count,
                "q_values": {
                    actions[action_id]: float(q_values[action_id])
                    for action_id in range(len(actions))
                },
                "learned_action": actions[learned_action_id],
                "final_action": actions[final_action_id],
                "decision_source": decision_source,
            }
        except RLDecisionError:
            raise
        except Exception as error:
            raise RLDecisionError(f"The RL policy could not select an action: {error}") from error
