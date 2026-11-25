"""Gün 1 ölçümü: 13 doğrulanmış soruyu asistana sorar, sonucu referans SQL'in sonucuyla karşılaştırır.

Çalıştırma (ai/ klasöründen):  python -m eval.run_day1
Çıktı: eval/results_day1.csv ve ekranda özet.

Not: 5 soru few-shot örneği olarak prompt'ta bulunur (prompts.FEWSHOT_IDX). Rapora iki rakam yazın:
  - 8 "held-out" soruda doğruluk (asıl ölçüm)
  - 13 sorunun tamamı (few-shot dahil, daha iyimser)
"""
import csv
import json
import sys

from app import config, prompts, sql_tools
from app.assistant import answer_question
from eval.compare import compare_results


def main():
    with open(config.DATA_DIR / "verified_examples.json", encoding="utf-8") as f:
        queries = json.load(f)["verified_queries"]

    rows_out = []
    for i, q in enumerate(queries):
        fewshot = i in prompts.FEWSHOT_IDX
        print(f"[{i + 1}/{len(queries)}] {q['question']}")
        expected = sql_tools.execute_readonly_sql(q["sql"])
        got = answer_question(q["question"])

        if expected["status"] != "ok":
            status, note = "REFERANS_HATASI", f"Referans SQL çalışmadı: {expected.get('debug') or expected.get('message')}"
        elif got["status"] != "ok":
            status, note = "FAIL", f"Asistan sonuç üretemedi ({got['status']}): {got['message']}"
        else:
            status, note = compare_results(expected["rows"], got["rows"])
        print(f"      -> {status} {note}")
        rows_out.append({
            "no": i + 1, "soru": q["question"], "few_shot": "evet" if fewshot else "hayır",
            "durum": status, "not": note, "uretilen_sql": got["sql"].replace("\n", " "),
        })

    out_path = config.BASE_DIR / "eval" / "results_day1.csv"
    with open(out_path, "w", newline="", encoding="utf-8-sig") as f:
        w = csv.DictWriter(f, fieldnames=list(rows_out[0].keys()))
        w.writeheader()
        w.writerows(rows_out)

    def rate(subset):
        good = sum(1 for r in subset if r["durum"] in ("OK", "OK_EK_KOLON"))
        empty = sum(1 for r in subset if r["durum"] == "BOS_ESLESME")
        return good, empty, len(subset)

    held = [r for r in rows_out if r["few_shot"] == "hayır"]
    for name, subset in (("Held-out (few-shot olmayan)", held), ("Tümü", rows_out)):
        good, empty, n = rate(subset)
        print(f"\n{name}: {good}/{n} doğru (%{100 * good / n:.0f}); {empty} soruda iki sonuç da boş (kanıt değeri yok).")
    print(f"\nAyrıntı: {out_path}")
    if any(r["durum"] == "REFERANS_HATASI" for r in rows_out):
        print("UYARI: Bazı referans SQL'ler çalışmadı; veritabanı yüklemesini kontrol edin.", file=sys.stderr)


if __name__ == "__main__":
    main()
