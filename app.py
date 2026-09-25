from functools import wraps
from pathlib import Path

from flask import (
    Flask,
    flash,
    g,
    redirect,
    render_template,
    request,
    session,
    url_for,
)
from flask_wtf import CSRFProtect
from flask_wtf.csrf import CSRFError
from werkzeug.security import check_password_hash, generate_password_hash

from config import Config
from database import models as db_models
from database.init_db import init_app as init_database
from database.init_db import init_db
from services.ml_prediction_service import MLPredictionService, PredictionError
from services.rl_decision_service import RLDecisionService, RLDecisionError


csrf = CSRFProtect()


def login_required(view):
    @wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login"))
        return view(**kwargs)

    return wrapped_view


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_object(Config)

    if test_config:
        app.config.update(test_config)

    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    csrf.init_app(app)
    init_database(app)

    with app.app_context():
        init_db()

    app.extensions["ml_service"] = MLPredictionService(
        app.config["ML_MODEL_PATH"]
    )
    app.extensions["rl_service"] = RLDecisionService(
        app.config["RL_MODEL_PATH"]
    )

    @app.before_request
    def load_logged_in_user():
        user_id = session.get("user_id")
        g.user = db_models.get_user_by_id(user_id) if user_id else None

    @app.context_processor
    def inject_application_data():
        return {
            "app_name": app.config["APP_NAME"],
            "transaction_types": app.config["TRANSACTION_TYPES"],
        }

    @app.route("/")
    def index():
        if g.user:
            return redirect(url_for("prediction"))
        return redirect(url_for("login"))

    @app.route("/register", methods=["GET", "POST"])
    def register():
        if g.user:
            return redirect(url_for("prediction"))

        form_values = {
            "full_name": request.form.get("full_name", "").strip(),
            "email": request.form.get("email", "").strip().lower(),
        }

        if request.method == "POST":
            password = request.form.get("password", "")
            confirm_password = request.form.get("confirm_password", "")
            errors = []

            if len(form_values["full_name"]) < 2 or len(form_values["full_name"]) > 80:
                errors.append("Full name must contain between 2 and 80 characters.")
            if not db_models.is_valid_email(form_values["email"]):
                errors.append("Enter a valid email address.")
            if len(password) < 8:
                errors.append("Password must contain at least 8 characters.")
            if len(password) > 128:
                errors.append("Password is too long.")
            if password != confirm_password:
                errors.append("Password and confirmation do not match.")
            if db_models.get_user_by_email(form_values["email"]):
                errors.append("An account with this email already exists.")

            if errors:
                for error in errors:
                    flash(error, "danger")
            else:
                try:
                    db_models.create_user(
                        full_name=form_values["full_name"],
                        email=form_values["email"],
                        password_hash=generate_password_hash(password),
                    )
                except db_models.DuplicateEmailError:
                    flash("An account with this email already exists.", "danger")
                else:
                    flash("Registration successful. You can now log in.", "success")
                    return redirect(url_for("login"))

        return render_template("register.html", form_values=form_values)

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if g.user:
            return redirect(url_for("prediction"))

        email = request.form.get("email", "").strip().lower()

        if request.method == "POST":
            password = request.form.get("password", "")
            user = db_models.get_user_by_email(email)

            if user is None or not check_password_hash(user["password_hash"], password):
                flash("Incorrect email or password.", "danger")
            else:
                session.clear()
                session["user_id"] = user["id"]
                session.permanent = True
                flash(f"Welcome back, {user['full_name']}!", "success")
                return redirect(url_for("prediction"))

        return render_template("login.html", email=email)

    @app.route("/logout", methods=["POST"])
    @login_required
    def logout():
        session.clear()
        flash("You have been logged out safely.", "success")
        return redirect(url_for("login"))

    @app.route("/about")
    def about():
        return render_template("about.html")

    @app.route("/prediction", methods=["GET", "POST"])
    @login_required
    def prediction():
        ml_service = app.extensions["ml_service"]
        rl_service = app.extensions["rl_service"]
        model_ready = ml_service.ready and rl_service.ready
        model_errors = [
            message
            for message in (ml_service.load_error, rl_service.load_error)
            if message
        ]

        form_values = {
            "step": request.form.get("step", "1").strip(),
            "type": request.form.get("type", "TRANSFER").strip().upper(),
            "amount": request.form.get("amount", "").strip(),
            "oldbalanceOrig": request.form.get("oldbalanceOrig", "").strip(),
            "oldbalanceDest": request.form.get("oldbalanceDest", "").strip(),
        }
        result = None

        if request.method == "POST":
            if not model_ready:
                flash(
                    "Prediction models are not ready. Add both trained model files and restart Flask.",
                    "danger",
                )
                return render_template(
                    "prediction.html",
                    model_ready=model_ready,
                    model_errors=model_errors,
                    form_values=form_values,
                    result=None,
                )

            try:
                transaction = validate_transaction_form(
                    form_values,
                    allowed_types=app.config["TRANSACTION_TYPES"],
                )
                ml_result = ml_service.predict(transaction)
                rl_result = rl_service.decide(
                    fraud_probability=ml_result["calibrated_fraud_risk"],
                    amount=transaction["amount"],
                    hour=ml_result["hour"],
                )

                log_id = db_models.create_prediction_log(
                    user_id=g.user["id"],
                    transaction=transaction,
                    ml_result=ml_result,
                    rl_result=rl_result,
                )

                result = {
                    "log_id": log_id,
                    "transaction": transaction,
                    "ml": ml_result,
                    "rl": rl_result,
                }
            except (ValueError, PredictionError, RLDecisionError) as error:
                app.logger.warning("Prediction rejected: %s", error)
                flash(str(error), "danger")
            except Exception:
                app.logger.exception("Unexpected prediction failure")
                flash("Prediction failed unexpectedly. Please check the model files.", "danger")

        return render_template(
            "prediction.html",
            model_ready=model_ready,
            model_errors=model_errors,
            form_values=form_values,
            result=result,
        )

    @app.route("/logs")
    @login_required
    def logs():
        try:
            page = max(int(request.args.get("page", 1)), 1)
        except ValueError:
            page = 1

        per_page = app.config["LOGS_PER_PAGE"]
        total_logs = db_models.count_prediction_logs(g.user["id"])
        total_pages = max((total_logs + per_page - 1) // per_page, 1)
        page = min(page, total_pages)

        prediction_logs = db_models.get_prediction_logs(
            user_id=g.user["id"],
            page=page,
            per_page=per_page,
        )
        summary = db_models.get_prediction_summary(g.user["id"])

        return render_template(
            "logs.html",
            prediction_logs=prediction_logs,
            summary=summary,
            page=page,
            total_pages=total_pages,
            total_logs=total_logs,
        )

    @app.route("/health")
    def health():
        ml_service = app.extensions["ml_service"]
        rl_service = app.extensions["rl_service"]
        status_code = 200 if ml_service.ready and rl_service.ready else 503
        return {
            "application": "ok",
            "ml_model_ready": ml_service.ready,
            "rl_model_ready": rl_service.ready,
        }, status_code

    @app.errorhandler(CSRFError)
    def handle_csrf_error(error):
        flash("The form expired or was invalid. Please try again.", "danger")
        return render_template("400.html", message=error.description), 400

    @app.errorhandler(404)
    def page_not_found(_error):
        return render_template("404.html"), 404

    @app.errorhandler(500)
    def internal_error(_error):
        return render_template("500.html"), 500

    return app


def validate_transaction_form(values, allowed_types):
    try:
        step = int(values["step"])
    except (TypeError, ValueError) as error:
        raise ValueError("Step must be a whole number.") from error

    if step < 1 or step > 1_000_000:
        raise ValueError("Step must be between 1 and 1,000,000.")

    transaction_type = values["type"].upper()
    if transaction_type not in allowed_types:
        raise ValueError("Select a valid transaction type.")

    numeric_values = {}
    field_labels = {
        "amount": "Transaction amount",
        "oldbalanceOrig": "Old origin balance",
        "oldbalanceDest": "Old destination balance",
    }

    for field, label in field_labels.items():
        try:
            value = float(values[field])
        except (TypeError, ValueError) as error:
            raise ValueError(f"{label} must be a valid number.") from error
        if value < 0 or value > 1_000_000_000_000:
            raise ValueError(f"{label} must be between 0 and 1 trillion.")
        numeric_values[field] = value

    return {
        "step": step,
        "type": transaction_type,
        **numeric_values,
    }


app = create_app()


if __name__ == "__main__":
    app.run(
        host="127.0.0.1",
        port=int(app.config.get("PORT", 5000)),
        debug=app.config.get("DEBUG", False),
    )
