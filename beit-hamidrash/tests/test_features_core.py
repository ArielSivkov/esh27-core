def test_features_endpoint(client):
    r = client.get("/api/features")
    assert r.status_code == 200 and isinstance(r.json(), list)


def test_new_kinds(client):
    pk = client.get("/api/users").json()[1]["pubkey"]
    assert client.post("/api/events", json={"user": "reuven", "kind": "follow", "body": {"subject": pk}}).status_code == 200
    assert client.post("/api/events", json={"user": "reuven", "kind": "sheet", "body": {"title": "x", "items": []}}).status_code == 400
