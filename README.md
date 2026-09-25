# FraudGuard AI — Flask ML + RL Application

FraudGuard AI is a complete Flask web application for the corrected credit-card/transaction fraud project. It combines:

- a calibrated machine-learning fraud-risk model;
- a Q-learning action policy;
- secure registration and login;
- an SQLite prediction history;
- responsive HTML, CSS, and JavaScript pages.

## Included pages

| Page | URL | Authentication |
|---|---|---|
| Register | `/register` | Public |
| Login | `/login` | Public |
| About | `/about` | Public |
| Prediction | `/prediction` | Login required |
| Logs | `/logs` | Login required |
| Logout | `/logout` | Login required, POST request |

## 1. Add the two trained files

Copy the files produced by `Credit_Card_Fraud_ML_RL_Updated.ipynb` into `model_artifacts/`:

```text
model_artifacts/
├── best_fraud_detection_model.pkl
└── fraud_q_learning_policy.pkl
```

Do not use demonstration or unrelated `.pkl` files. The application validates the expected package keys and Q-table shape.

## 2. Windows setup

### Quick method

Double-click:

```text
run_windows.bat
```

It creates `.venv`, installs packages, creates `.env` when missing, and starts Flask.

### Manual method

Open Command Prompt or the VS Code terminal in this project folder:

```bat
py -m venv .venv
.venv\Scripts\activate
python -m pip install --upgrade pip
pip install -r requirements.txt
copy .env.example .env
python check_models.py
python app.py
```

Open:

```text
http://127.0.0.1:5000
```

## 3. Linux/macOS setup

```bash
bash run_unix.sh
```

Or run manually:

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python check_models.py
python app.py
```

## 4. Configure the secret key

Open `.env` and replace the development value. One way to generate a key is:

```bash
python -c "import secrets; print(secrets.token_hex(32))"
```

Paste the output after `SECRET_KEY=`.

## 5. SQLite database

The database is created automatically at:

```text
instance/fraud_detection.db
```

Tables:

- `users`: name, unique email, password hash, creation time;
- `prediction_logs`: transaction inputs, ML result, RL state/action and timestamp.

No sample accounts or fake prediction rows are inserted.

To recreate the schema manually:

```bash
flask --app app init-db
```

## Prediction input fields

The form deliberately accepts only pre-transaction values:

- `step`
- `type`
- `amount`
- `oldbalanceOrig`
- `oldbalanceDest`

`newbalanceOrig` and `newbalanceDest` are not accepted because they are post-transaction information and would cause leakage in a real-time decision system.

## Application flow

```text
Transaction form
      ↓
Leakage-safe feature engineering
      ↓
Saved ML pipeline
      ↓
Raw score → probability calibration → ML result
      ↓
Fraud state + amount state + time state
      ↓
Q-table action + sparse-state fallback + safety guardrail
      ↓
Result page and private SQLite log
```

## Model compatibility

Pickled scikit-learn/XGBoost models are most reliable when the web application uses package versions compatible with the environment that trained them. If `python check_models.py` reports a version error, install the exact `scikit-learn`, `xgboost`, `numpy`, `pandas`, and `joblib` versions printed by the training notebook.

## Run tests

The included tests verify authentication protection, registration/login, SQLite logging helpers and the missing-model status page:

```bash
pytest -q
```

## Security already included

- password hashing using Werkzeug;
- parameterized SQLite queries;
- CSRF protection for forms;
- HTTP-only and SameSite session cookies;
- user-specific log queries;
- server-side numeric and transaction-type validation;
- POST-only logout;
- generic login errors that do not reveal whether an email exists.

For public deployment, use HTTPS, set `SESSION_COOKIE_SECURE=1`, disable debug mode, use a long random secret, and run behind a production WSGI server.
