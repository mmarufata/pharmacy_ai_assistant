"""Ana akış: soru -> (LLM) SQL -> çalıştır -> (LLM) özet.

Gün 1 kapsamı: tek soruluk akış. Henüz YOK (sonraki günlerde eklenecek):
  - hata düzeltme / yeniden deneme döngüsü (rejected kodlarına göre)
  - sohbet hafızası (history parametresi şimdilik kullanılmıyor)
  - gerçek MCP çağrısı (şimdilik sql_tools.execute_readonly_sql stub'ı)
"""
import datetime
import json
import re

from . import llm, prompts, sql_tools

_system_prompt_cache = {}


def _system_prompt():
    today = datetime.date.today()
    if today not in _system_prompt_cache:
        _system_prompt_cache.clear()
        _system_prompt_cache[today] = prompts.build_system_prompt(today, sql_tools.get_data_range())
    return _system_prompt_cache[today]


def parse_llm_json(text):
    """Modelin JSON yanıtını ayrıştırır. Bozuksa SQL olarak yorumlamayı dener."""
    s = (text or "").strip()
    candidates = [s]  # önce olduğu gibi dene (sql alanının içinde ``` olabilir)
    m = re.search(r"```(?:json)?\s*(.*?)```", s, re.S | re.I)
    if m:
        candidates.append(m.group(1).strip())
    for cand in candidates:
        try:
            data = json.loads(cand)
        except json.JSONDecodeError:
            continue
        if isinstance(data, dict) and data.get("action") in ("answer", "refuse", "clarify"):
            return {
                "action": data["action"],
                "sql": (data.get("sql") or "").strip(),
                "message": (data.get("message") or "").strip(),
            }
    # JSON değilse: düz SQL gelmiş olabilir
    sql = sql_tools.clean_sql(text)
    if re.match(r"\s*(select|with)\b", sql, re.I):
        return {"action": "answer", "sql": sql, "message": ""}
    return {"action": "clarify", "sql": "", "message": "Soruyu anlayamadım, biraz daha açık yazar mısınız?"}


def _summarize(question, sql, result):
    rows = result["rows"][:30]
    payload = {
        "soru": question,
        "sql": sql,
        "kolonlar": result["columns"],
        "satirlar": rows,
        "toplam_satir": result["row_count"],
        "kirpildi": result.get("truncated", False),
    }
    text = json.dumps(payload, ensure_ascii=False)
    return llm.generate(prompts.SUMMARY_SYSTEM, [{"role": "user", "text": text}]).strip()


def answer_question(question, history=None):
    """Bir kullanıcı sorusunu yanıtlar. Web/Flask tarafı yalnızca bu fonksiyonu çağıracak.

    Dönüş (her zaman bir sözlük):
      status : "ok" | "refused" | "clarify" | "rejected" | "error"
      sql, columns, rows, row_count, truncated, summary, message, code, debug
    """
    out = {"question": question, "status": "error", "sql": "", "columns": [], "rows": [],
           "row_count": 0, "truncated": False, "summary": "", "message": "", "code": None}
    try:
        raw = llm.generate(_system_prompt(), [{"role": "user", "text": question}], json_mode=True)
    except llm.LLMError as e:
        out["message"] = f"Yapay zekâ servisine ulaşılamadı: {e}"
        return out

    plan = parse_llm_json(raw)
    if plan["action"] == "refuse":
        out.update(status="refused", message=plan["message"] or "Bu istek yerine getirilemez.")
        return out
    if plan["action"] == "clarify":
        out.update(status="clarify", message=plan["message"])
        return out

    sql = sql_tools.clean_sql(plan["sql"])
    out["sql"] = sql
    result = sql_tools.execute_readonly_sql(sql)

    if result["status"] == "rejected":
        out.update(status="rejected", code=result.get("code"), message=result["message"])
        return out
    if result["status"] == "error":
        out.update(status="error", message=result["message"], debug=result.get("debug"))
        return out

    out.update(status="ok", sql=result.get("executed_sql", sql), columns=result["columns"],
               rows=result["rows"], row_count=result["row_count"], truncated=result["truncated"])
    try:
        out["summary"] = _summarize(question, sql, result)
    except llm.LLMError as e:
        out["summary"] = f"(Özet üretilemedi: {e})"
    return out
