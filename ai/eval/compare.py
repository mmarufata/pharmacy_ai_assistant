"""İki sonucu SQL metniyle değil DEĞERLERLE karşılaştırır."""
import datetime
import decimal


def _norm(v):
    if isinstance(v, (int, float, decimal.Decimal)) and not isinstance(v, bool):
        return round(float(v), 2)
    if isinstance(v, (datetime.date, datetime.datetime)):
        return v.isoformat()
    return v if v is not None else None


def _row(r):
    return tuple(_norm(v) for v in r)


def _key(r):
    return tuple((type(v).__name__ != "float", str(v)) for v in r)


def compare_results(expected_rows, got_rows):
    """Dönüş: (durum, açıklama)
    durum: "OK"          -> aynı satırlar (sıra ve kolon adı önemsiz)
           "OK_EK_KOLON" -> beklenen değerler var, modelin fazladan kolonu var
           "BOS_ESLESME" -> ikisi de boş (tarih verinin dışında olabilir; kanıt değeri YOK)
           "FAIL"        -> farklı
    """
    exp = [_row(r) for r in expected_rows]
    got = [_row(r) for r in got_rows]
    if not exp and not got:
        return "BOS_ESLESME", "İki sonuç da boş. Sorgu tarihe bağlıysa veri aralığının dışında olabilir."
    if sorted(exp, key=_key) == sorted(got, key=_key):
        return "OK", ""
    if len(exp) == len(got) and exp:
        remaining = list(got)
        ok = True
        for e in exp:
            for g in remaining:
                pool = list(g)
                if all(_take(pool, v) for v in e):
                    remaining.remove(g)
                    break
            else:
                ok = False
                break
        if ok:
            return "OK_EK_KOLON", "Beklenen değerlerin hepsi var; model fazladan kolon döndürdü."
    return "FAIL", f"Beklenen {len(exp)} satır, model {len(got)} satır döndürdü ve değerler uyuşmuyor."


def _take(pool, v):
    if v in pool:
        pool.remove(v)
        return True
    return False
