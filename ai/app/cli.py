"""Terminalden deneme: python -m app.cli  (rapora ekran görüntüsü için ideal)"""
import sys

from .assistant import answer_question


def show(r):
    print("\n--- SQL ---")
    print(r["sql"] or "(yok)")
    if r["status"] == "ok":
        print("\n--- SONUÇ ---")
        print(" | ".join(r["columns"]))
        for row in r["rows"][:15]:
            print(" | ".join(str(v) for v in row))
        if r["row_count"] > 15:
            print(f"... ({r['row_count']} satır, ilk 15 gösteriliyor)")
        print("\n--- ÖZET ---")
        print(r["summary"])
    else:
        print(f"\n[{r['status']}] {r['message']}")
        if r.get("debug"):
            print("debug:", r["debug"])


def main():
    if len(sys.argv) > 1:
        show(answer_question(" ".join(sys.argv[1:])))
        return
    print("Eczane asistanı (çıkmak için boş satır)")
    while True:
        q = input("\nSoru> ").strip()
        if not q:
            break
        show(answer_question(q))


if __name__ == "__main__":
    main()
