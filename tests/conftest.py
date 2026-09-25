import sys
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app import create_app  # noqa: E402


@pytest.fixture()
def app(tmp_path):
    application = create_app({
        "TESTING": True,
        "WTF_CSRF_ENABLED": False,
        "SECRET_KEY": "test-secret-key",
        "DATABASE": str(tmp_path / "test.db"),
        "ML_MODEL_PATH": str(tmp_path / "missing-ml.pkl"),
        "RL_MODEL_PATH": str(tmp_path / "missing-rl.pkl"),
    })
    yield application


@pytest.fixture()
def client(app):
    return app.test_client()
