"""Coba asisten di terminal: python chat_cli.py"""
from app.assistant.service import chat

ctx = {}
print("Ketik pesan (kosong untuk keluar)")
while msg := input("\nKamu: ").strip():
    r = chat(msg, ctx)
    ctx = r["context"]
    print(f"\nAsisten [{r['intent']}]:\n{r['answer']}")
    if r["handoff"] and r["handoff"]["url"]:
        print(r["handoff"]["url"])
