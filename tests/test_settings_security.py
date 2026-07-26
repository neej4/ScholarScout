from preview_server import app


def test_settings_test_rejects_custom_http_non_localhost_url():
    app.config["TESTING"] = True
    with app.test_client() as client:
        response = client.post(
            "/api/settings/test",
            json={
                "provider": "custom",
                "base_url": "http://169.254.169.254/latest/meta-data",
            },
        )

    assert response.status_code == 400
    assert "Invalid base_url" in response.get_json()["error"]


def test_settings_test_accepts_localhost_custom_url():
    app.config["TESTING"] = True
    with app.test_client() as client:
        response = client.post(
            "/api/settings/test",
            json={
                "provider": "custom",
                "base_url": "http://localhost:11434/v1",
            },
        )

    assert response.status_code == 200
    assert response.get_json()["success"] is False
