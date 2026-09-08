from app.agent import handle_message

PHONE = "+905551112233"


def test_menu_question_goes_through_the_get_menu_tool(db, provider):
    reply = handle_message(PHONE, "menüde neler var?", db, provider)

    assert "Lahmacun" in reply and "90" in reply
    roles = [(m.role, m.tool_name) for m in db.get_history(PHONE)]
    assert ("tool_call", "get_menu") in roles


def test_full_order_flow_creates_exactly_one_order(db, provider):
    handle_message(PHONE, "menü", db, provider)

    asked = handle_message(PHONE, "1 kıymalı pide 2 ayran alayım", db, provider)
    assert "adres" in asked.lower()
    assert db.list_orders() == [], "sipariş adres alınmadan oluşturulmamalı"

    confirmed = handle_message(PHONE, "Bahçelievler 7. Cadde No:12", db, provider)
    orders = db.list_orders()
    assert len(orders) == 1
    assert orders[0]["total"] == 180 + 2 * 30
    assert orders[0]["phone"] == PHONE
    assert f"#{orders[0]['id']}" in confirmed


def test_history_is_isolated_per_phone_number(db, provider):
    handle_message(PHONE, "1 lahmacun", db, provider)
    handle_message("+905559998877", "merhaba", db, provider)

    assert all("lahmacun" not in m.content.lower() for m in db.get_history("+905559998877"))
    assert any("lahmacun" in m.content.lower() for m in db.get_history(PHONE))
