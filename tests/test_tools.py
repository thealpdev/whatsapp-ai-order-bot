from app.tools import create_order, get_menu


def test_get_menu_returns_the_four_products():
    menu = get_menu()
    names = {item["name"] for item in menu["items"]}
    assert names == {"Kıymalı Pide", "Kaşarlı Pide", "Lahmacun", "Ayran"}
    assert menu["items"][0]["price"] == 180


def test_create_order_computes_total_and_persists(db):
    result = create_order(
        db,
        items=[{"name": "Kıymalı Pide", "qty": 1}, {"name": "ayran", "qty": 2}],
        address="Bahçelievler 7. Cadde No:12",
        phone="+905550000000",
    )

    assert result["ok"] is True
    assert result["order"]["total"] == 180 + 2 * 30
    assert db.list_orders()[0]["address"] == "Bahçelievler 7. Cadde No:12"


def test_create_order_rejects_unknown_item_and_missing_address(db):
    unknown = create_order(db, [{"name": "sushi", "qty": 1}], "Adres", "+905550000000")
    assert unknown["ok"] is False and "sushi" in unknown["error"]

    no_address = create_order(db, [{"name": "Lahmacun", "qty": 1}], "  ", "+905550000000")
    assert no_address["ok"] is False

    assert db.list_orders() == []
