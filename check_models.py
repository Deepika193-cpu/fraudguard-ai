from config import Config
from services.ml_prediction_service import MLPredictionService
from services.rl_decision_service import RLDecisionService


def main():
    ml_service = MLPredictionService(Config.ML_MODEL_PATH)
    rl_service = RLDecisionService(Config.RL_MODEL_PATH)

    print("FraudGuard AI model check")
    print("-" * 42)
    print("ML model:", "READY" if ml_service.ready else "NOT READY")
    if ml_service.load_error:
        print("  ", ml_service.load_error)
    else:
        print("   Selected model:", ml_service.model_name)
        print("   Threshold:", ml_service.threshold)

    print("RL policy:", "READY" if rl_service.ready else "NOT READY")
    if rl_service.load_error:
        print("  ", rl_service.load_error)
    else:
        print("   Q-table shape:", rl_service.package["q_table"].shape)
        print("   Minimum state samples:", rl_service.package["minimum_state_samples"])

    if not (ml_service.ready and rl_service.ready):
        raise SystemExit(1)

    print("\nBoth model packages are compatible with the application.")


if __name__ == "__main__":
    main()
