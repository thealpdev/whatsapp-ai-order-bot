from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

WEBHOOK_PAYLOAD = {
    "entry": [
        {
            "changes": [
                {
                    "value": {
                        "messages": [
                            {
                                "from": "905551112233",
                                "type": "text",
                                "text": {"body": "1 lahmacun, adres: Kızılay No:5"},
                            }
                        ]
                    }
                }
            ]
        }
    ]
}


def test_webhook_verification():
    ok = client.get(
        "/webhook",
        params={
            "hub.mode": "subscribe",
            "hub.verify_token": "test-verify-token",
            "hub.challenge": "12345",
        },
    )
    assert ok.status_code == 200 and ok.text == "12345"

    bad = client.get(
        "/webhook",
        params={"hub.mode": "subscribe", "hub.verify_token": "wrong", "hub.challenge": "12345"},
    )
    assert bad.status_code == 403


def test_incoming_message_creates_an_order_visible_on_orders_endpoint():
    assert client.get("/health").json()["provider"] == "mock"

    posted = client.post("/webhook", json=WEBHOOK_PAYLOAD)
    assert posted.status_code == 200

    orders = client.get("/orders").json()["orders"]
    assert len(orders) == 1
    assert orders[0]["total"] == 90
    assert orders[0]["address"] == "Kızılay No:5"
