def test_feature_flag_routes_are_registered(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    assert "/api/v1/feature-flags/ab-test" in paths
    assert "/api/v1/feature-flags/{name}" in paths


def test_api_routes_are_registered(client):
    response = client.get("/openapi.json")

    assert response.status_code == 200

    paths = response.json()["paths"]

    expected_routes = {
        "/api/v1/feature-flags/ab-test",
        "/api/v1/feature-flags/{name}",
    }

    assert expected_routes.issubset(paths.keys())
