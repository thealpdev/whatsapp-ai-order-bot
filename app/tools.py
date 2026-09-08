"""The tools the model can call. Plain functions — no LLM types leak in here."""

from __future__ import annotations

from app.db import Database
from app.llm.base import ToolSpec
from app.menu import find_item, load_menu

TOOL_SPECS: list[ToolSpec] = [
    ToolSpec(
        name="get_menu",
        description="Restoranın güncel menüsünü ve fiyatlarını döndürür.",
        parameters={"type": "object", "properties": {}},
    ),
    ToolSpec(
        name="create_order",
        description=(
            "Siparişi kaydeder. SADECE ürünler, adres ve telefon netleştikten ve "
            "müşteri onay verdikten sonra çağrılır."
        ),
        parameters={
            "type": "object",
            "properties": {
                "items": {
                    "type": "array",
                    "description": "Sipariş edilen ürünler.",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "Menüdeki ürün adı."},
                            "qty": {"type": "integer", "description": "Adet."},
                        },
                        "required": ["name", "qty"],
                    },
                },
                "address": {"type": "string", "description": "Teslimat adresi."},
                "phone": {"type": "string", "description": "Müşterinin telefon numarası."},
            },
            "required": ["items", "address", "phone"],
        },
    ),
]


def get_menu() -> dict:
    return load_menu()


def create_order(db: Database, items: list[dict], address: str, phone: str) -> dict:
    if not items:
        return {"ok": False, "error": "Sipariş boş, en az bir ürün gerekli."}
    if not address or not address.strip():
        return {"ok": False, "error": "Teslimat adresi eksik."}
    if not phone or not phone.strip():
        return {"ok": False, "error": "Telefon numarası eksik."}

    resolved: list[dict] = []
    total = 0.0
    for raw in items:
        item = find_item(str(raw.get("name", "")))
        if item is None:
            return {"ok": False, "error": f"Menüde bulunamadı: {raw.get('name')}"}
        try:
            qty = int(raw.get("qty", 1))
        except (TypeError, ValueError):
            return {"ok": False, "error": f"Geçersiz adet: {raw.get('qty')}"}
        if qty < 1:
            return {"ok": False, "error": f"Adet en az 1 olmalı: {item['name']}"}
        line = item["price"] * qty
        total += line
        resolved.append(
            {"name": item["name"], "qty": qty, "price": item["price"], "line_total": line}
        )

    order = db.create_order(
        phone=phone.strip(), address=address.strip(), items=resolved, total=total
    )
    return {"ok": True, "order": order}


def run_tool(name: str, args: dict, db: Database) -> dict:
    """Dispatch a tool call coming from any provider."""
    if name == "get_menu":
        return get_menu()
    if name == "create_order":
        return create_order(
            db,
            items=args.get("items") or [],
            address=args.get("address") or "",
            phone=args.get("phone") or "",
        )
    return {"ok": False, "error": f"Bilinmeyen tool: {name}"}
