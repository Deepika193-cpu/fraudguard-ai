def register(client, email="student@example.com", password="StrongPass123"):
    return client.post(
        "/register",
        data={
            "full_name": "Test Student",
            "email": email,
            "password": password,
            "confirm_password": password,
        },
        follow_redirects=True,
    )


def login(client, email="student@example.com", password="StrongPass123"):
    return client.post(
        "/login",
        data={"email": email, "password": password},
        follow_redirects=True,
    )


def test_public_pages_load(client):
    assert client.get("/login").status_code == 200
    assert client.get("/register").status_code == 200
    assert client.get("/about").status_code == 200


def test_prediction_requires_login(client):
    response = client.get("/prediction", follow_redirects=False)
    assert response.status_code == 302
    assert "/login" in response.headers["Location"]


def test_registration_login_and_private_pages(client):
    response = register(client)
    assert response.status_code == 200
    assert b"Registration successful" in response.data

    response = login(client)
    assert response.status_code == 200
    assert b"Fraud-risk prediction" in response.data
    assert b"Model setup required" in response.data

    logs_response = client.get("/logs")
    assert logs_response.status_code == 200
    assert b"No predictions saved yet" in logs_response.data


def test_duplicate_registration_is_rejected(client):
    register(client)
    response = register(client)
    assert b"already exists" in response.data


def test_incorrect_login_is_rejected(client):
    register(client)
    response = login(client, password="incorrect-password")
    assert b"Incorrect email or password" in response.data


def test_prediction_disabled_when_models_are_missing(client):
    register(client)
    login(client)

    response = client.post(
        "/prediction",
        data={
            "step": "1",
            "type": "TRANSFER",
            "amount": "181",
            "oldbalanceOrig": "181",
            "oldbalanceDest": "0",
        },
        follow_redirects=True,
    )
    assert response.status_code == 200
    assert b"Prediction models are not ready" in response.data
