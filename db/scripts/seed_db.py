"""Sentetik veriyi yükler.  Kullanım:
    python -m scripts.seed_db                  # veri varsa hiçbir şey yapmaz
    python -m scripts.seed_db --reset --yes    # TÜM VERİYİ SİLİP yeniden üretir (onay bayrağı zorunlu)
"""
import argparse
import sys

from app.db.seed import seed_database
from app.db.session import get_app_engine


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--reset", action="store_true", help="Tüm tabloları boşaltır (SİLME riski!)")
    ap.add_argument("--yes", action="store_true", help="--reset için açık onay")
    args = ap.parse_args()
    if args.reset and not args.yes:
        print("HATA: --reset tüm verileri siler. Emin iseniz --reset --yes kullanın.", file=sys.stderr)
        return 2
    added = seed_database(get_app_engine(), reset=args.reset)
    print("Sentetik veri eklendi." if added else "Veri zaten mevcut; hiçbir şey değiştirilmedi.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
