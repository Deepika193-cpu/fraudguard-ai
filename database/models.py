import json
import re
import sqlite3

from database.init_db import get_db


EMAIL_PATTERN = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")


class DuplicateEmailError(Exception):
    pass


def is_valid_email(email):
    return bool(email and len(email) <= 254 and EMAIL_PATTERN.match(email))


def create_user(full_name, email, password_hash):
    database = get_db()
    try:
        cursor = database.execute(
            "INSERT INTO users (full_name, email, password_hash) VALUES (?, ?, ?)",
            (full_name, email, password_hash),
        )
        database.commit()
        return cursor.lastrowid
    except sqlite3.IntegrityError as error:
        database.rollback()
        raise DuplicateEmailError from error


def get_user_by_email(email):
    return get_db().execute(
        "SELECT * FROM users WHERE email = ?",
        (email,),
    ).fetchone()


def get_user_by_id(user_id):
    if user_id is None:
        return None
    return get_db().execute(
        "SELECT id, full_name, email, created_at FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()


def create_prediction_log(user_id, transaction, ml_result, rl_result):
    database = get_db()
    cursor = database.execute(
        """
        INSERT INTO prediction_logs (
            user_id, step, transaction_type, amount,
            oldbalance_orig, oldbalance_dest,
            raw_model_score, fraud_probability, decision_threshold,
            ml_prediction, risk_level, rl_state, state_sample_count,
            learned_rl_action, final_rl_action, decision_source
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user_id,
            transaction["step"],
            transaction["type"],
            transaction["amount"],
            transaction["oldbalanceOrig"],
            transaction["oldbalanceDest"],
            ml_result["raw_model_score"],
            ml_result["calibrated_fraud_risk"],
            ml_result["decision_threshold"],
            ml_result["ml_prediction"],
            ml_result["risk_level"],
            json.dumps(list(rl_result["state"])),
            rl_result["state_sample_count"],
            rl_result["learned_action"],
            rl_result["final_action"],
            rl_result["decision_source"],
        ),
    )
    database.commit()
    return cursor.lastrowid


def get_prediction_logs(user_id, page=1, per_page=12):
    offset = (page - 1) * per_page
    return get_db().execute(
        """
        SELECT *
        FROM prediction_logs
        WHERE user_id = ?
        ORDER BY datetime(created_at) DESC, id DESC
        LIMIT ? OFFSET ?
        """,
        (user_id, per_page, offset),
    ).fetchall()


def count_prediction_logs(user_id):
    row = get_db().execute(
        "SELECT COUNT(*) AS total FROM prediction_logs WHERE user_id = ?",
        (user_id,),
    ).fetchone()
    return int(row["total"])


def get_prediction_summary(user_id):
    row = get_db().execute(
        """
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN ml_prediction = 'FRAUD' THEN 1 ELSE 0 END) AS fraud_predictions,
            SUM(CASE WHEN final_rl_action = 'BLOCK' THEN 1 ELSE 0 END) AS blocked,
            SUM(CASE WHEN final_rl_action = 'MANUAL_REVIEW' THEN 1 ELSE 0 END) AS reviewed,
            AVG(fraud_probability) AS average_risk
        FROM prediction_logs
        WHERE user_id = ?
        """,
        (user_id,),
    ).fetchone()

    return {
        "total": int(row["total"] or 0),
        "fraud_predictions": int(row["fraud_predictions"] or 0),
        "blocked": int(row["blocked"] or 0),
        "reviewed": int(row["reviewed"] or 0),
        "average_risk": float(row["average_risk"] or 0.0),
    }
