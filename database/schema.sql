PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    full_name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE COLLATE NOCASE,
    password_hash TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS prediction_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    step INTEGER NOT NULL,
    transaction_type TEXT NOT NULL,
    amount REAL NOT NULL,
    oldbalance_orig REAL NOT NULL,
    oldbalance_dest REAL NOT NULL,
    raw_model_score REAL NOT NULL,
    fraud_probability REAL NOT NULL,
    decision_threshold REAL NOT NULL,
    ml_prediction TEXT NOT NULL,
    risk_level TEXT NOT NULL,
    rl_state TEXT NOT NULL,
    state_sample_count INTEGER NOT NULL,
    learned_rl_action TEXT NOT NULL,
    final_rl_action TEXT NOT NULL,
    decision_source TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_prediction_logs_user_created
ON prediction_logs (user_id, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_prediction_logs_action
ON prediction_logs (final_rl_action);
