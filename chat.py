#!/usr/bin/env python3
"""Terminal chat — same agent, same tools, no WhatsApp needed.

python chat.py            # uses the phone number below
python chat.py +90555...  # pretend to be another customer
"""

from __future__ import annotations

import sys

from app.agent import handle_message
from app.deps import get_db
from app.llm.factory import get_provider

DEFAULT_PHONE = "+905550000000"


def main() -> None:
    phone = sys.argv[1] if len(sys.argv) > 1 else DEFAULT_PHONE
    db = get_db()
    provider = get_provider()

    print(f"Demo Pide sipariş botu — provider: {provider.name}, müşteri: {phone}")
    if provider.name == "mock":
        print("(GEMINI_API_KEY yok, kural tabanlı mock modda çalışıyor.)")
    print("Çıkmak için 'q'.\n")

    while True:
        try:
            text = input("sen > ").strip()
        except (EOFError, KeyboardInterrupt):
            print()
            break
        if text.lower() in {"q", "quit", "exit"}:
            break
        if not text:
            continue
        print(f"bot > {handle_message(phone, text, db, provider)}\n")


if __name__ == "__main__":
    main()
