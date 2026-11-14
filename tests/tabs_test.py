# Test cu Supabase și Gemini simulate — rulează prin tests/run_tests.py
"""Opțiunile salvate pe conversație (sessions.setari), redeschiderea din listă, tab nou cu ?new=1&opt=,
Pas cu Pas / Strategie exclusive, modificarea ultimului mesaj și retrimiterea unui mesaj fără răspuns."""
import json, time, supabase, fake_sb, warnings, logging
logging.disable(logging.WARNING); warnings.filterwarnings("ignore")
supabase.create_client = fake_sb.create_client
import google.genai as genai
SEEN = []
class Chunk:
    def __init__(s, t): s.text = t; s.usage_metadata = None
class Models:
    def generate_content_stream(s, model, contents, config):
        last = contents[-1].parts[-1].text
        SEEN.append((config.system_instruction or "", last))
        return iter([Chunk("Răspuns la: " + last)])
class Caches:
    def create(s, **k): raise Exception("caching not supported")
class C:
    def __init__(s, api_key=None): s.models = Models(); s.caches = Caches(); s.files = None
genai.Client = C
from streamlit.testing.v1 import AppTest
ok = lambda c, m: print(("PASS " if c else "FAIL ") + m)
def chk(a): assert not a.exception, [e.value for e in a.exception]
def tog(a, label): return next(t for t in a.toggle if t.label == label)
def row(sid): return next(r for r in fake_sb.DB["sessions"] if r["session_id"] == sid)

A, B = "a1" * 32, "b2" * 32
a = AppTest.from_file("app_under_test.py", default_timeout=90)
a.query_params["sid"] = A; a.session_state["_browser_storage"] = {}
a.session_state["materie_selectata"] = "bazele electrotehnicii"
a.run(); chk(a)

# ── Pas cu Pas și Strategie: doar unul activ ──
tog(a, "🔢 Explicație Pas cu Pas").set_value(True).run(); chk(a)
tog(a, "🧠 Explică-mi Strategia").set_value(True).run(); chk(a)
ok(a.session_state["mod_strategie"] and not a.session_state["pas_cu_pas"]
   and not tog(a, "🔢 Explicație Pas cu Pas").value, "Strategie activată → Pas cu Pas se dezactivează singur")
tog(a, "🔢 Explicație Pas cu Pas").set_value(True).run(); chk(a)
ok(a.session_state["pas_cu_pas"] and not a.session_state["mod_strategie"]
   and not tog(a, "🧠 Explică-mi Strategia").value, "Pas cu Pas activat → Strategia se dezactivează singură")
tog(a, "🇬🇧 Conversație în Engleză").set_value(True).run(); chk(a)
a.chat_input[0].set_value("Cum aplic teorema lui Thévenin?").run(); chk(a)
st_a = row(A).get("setari") or {}
ok(st_a.get("pas_cu_pas") and st_a.get("mod_engleza") and st_a.get("materie_selectata") == "bazele electrotehnicii",
   "opțiunile conversației sunt salvate în sessions.setari")

# ── O altă conversație, cu alte opțiuni ──
b = AppTest.from_file("app_under_test.py", default_timeout=90)
b.query_params["sid"] = B; b.session_state["_browser_storage"] = {}
b.session_state["materie_selectata"] = "baze de date"
b.session_state["_my_session_ids"] = [A, B]   # ambele conversații sunt ale acestui browser
b.run(); chk(b)
tog(b, "⚡ Mod Avansat").set_value(True).run(); chk(b)
b.chat_input[0].set_value("Ce este un INNER JOIN?").run(); chk(b)
ok((row(B).get("setari") or {}).get("mod_avansat"), "a doua conversație își salvează propriile opțiuni")

# ── Din conversația B, click pe A în „Conversații anterioare” ──
b.button(key=f"sess_{A}").click().run(); chk(b)
ok(b.session_state["session_id"] == A and b.query_params.get("sid") in (A, [A]),
   "click pe conversație: se deschide efectiv (sid + URL)")
ok(any("Thévenin" in m["content"] for m in b.session_state["messages"]), "mesajele conversației se încarcă")
ok(b.session_state["pas_cu_pas"] and b.session_state["mod_engleza"] and not b.session_state["mod_avansat"]
   and b.session_state["materie_selectata"] == "bazele electrotehnicii",
   "opțiunile și materia conversației se reselectează automat")
ok(tog(b, "🔢 Explicație Pas cu Pas").value and not tog(b, "⚡ Mod Avansat").value, "comutatoarele din bară arată opțiunile")
n = len(SEEN)
b.chat_input[0].set_value("Și cu Norton?").run(); chk(b)
ok(len(SEEN) == n + 1 and "PAS CU PAS" in SEEN[-1][0].upper() and "BAZELE ELECTROTEHNICII" in SEEN[-1][0].upper(),
   "următorul mesaj pleacă la AI cu opțiunile restaurate")

# ── Refresh / alt dispozitiv: conversația B își redeschide opțiunile ──
c = AppTest.from_file("app_under_test.py", default_timeout=90)
c.query_params["sid"] = B; c.session_state["_browser_storage"] = {}
c.run(); chk(c)
ok(c.session_state["mod_avansat"] and c.session_state["materie_selectata"] == "baze de date"
   and not c.session_state["pas_cu_pas"], "la redeschidere (refresh, alt dispozitiv) opțiunile revin")

# ── Tab nou: ?new=1&opt=... (ce trimite butonul „Conversație nouă”) ──
t = AppTest.from_file("app_under_test.py", default_timeout=90)
t.query_params["new"] = "1"
t.query_params["opt"] = json.dumps({"mod_strategie": True, "mod_engleza": True, "materie_selectata": "baze de date"})
t.session_state["_browser_storage"] = {"sid": A, "tabSid": A}
t.run(); chk(t)
nsid = t.session_state["session_id"]
ok(nsid not in (A, B), "tabul nou pornește o conversație nouă (nu preia conversația altui tab)")
ok(t.session_state["mod_strategie"] and t.session_state["mod_engleza"]
   and t.session_state["materie_selectata"] == "baze de date", "tabul nou are opțiunile tabului din care a fost deschis")
ok((row(nsid).get("setari") or {}).get("mod_strategie"), "opțiunile tabului nou sunt salvate pe conversația lui")

# ── Refresh într-un tab: conversația tabului (sessionStorage), nu ultima a browserului ──
r = AppTest.from_file("app_under_test.py", default_timeout=90)
r.session_state["_browser_storage"] = {"sid": nsid, "tabSid": B}
r.run(); chk(r)
ok(r.session_state["session_id"] == B, "refresh: fiecare tab își redeschide propria conversație")

# ── Modifică ultimul mesaj ──
e = AppTest.from_file("app_under_test.py", default_timeout=90)
E = "e3" * 32
e.query_params["sid"] = E; e.session_state["_browser_storage"] = {}
e.session_state["materie_selectata"] = "bazele electrotehnicii"
e.run(); chk(e)
e.chat_input[0].set_value("Cât e curentul prin R1?").run(); chk(e)
e.button(key="_edit_last_user").click().run(); chk(e)
ok(any(x.key == "_edit_text" for x in e.text_area), "„📝 Modifică” deschide mesajul pentru editare")
e.text_area(key="_edit_text").set_value("Cât e curentul prin R1 dacă R1 = 10 Ω și U = 5 V?")
n = len(SEEN)
e.button(key="_edit_send").click().run(); chk(e)
msgs = e.session_state["messages"]
ok([m["role"] for m in msgs] == ["user", "assistant"] and "10 Ω" in msgs[0]["content"] and "10 Ω" in msgs[1]["content"],
   "mesajul modificat înlocuiește mesajul vechi și răspunsul lui")
ok(len(SEEN) == n + 1 and "10 Ω" in SEEN[-1][1], "profesorul răspunde la mesajul modificat")
hist = [h for h in fake_sb.DB["history"] if h["session_id"] == E and h["role"] in ("user", "assistant")]
ok(len(hist) == 2 and not any(h["content"] == "Cât e curentul prin R1?" for h in hist),
   "în baza de date rămâne doar varianta nouă")

# ── Mesaj fără răspuns (Stop / eroare) → „Trimite din nou” / „Modifică mesajul” ──
F = "f4" * 32
fake_sb.DB["sessions"].append({"session_id": F, "app_id": "test_local", "created_at": time.time(),
                               "last_active": time.time()})
fake_sb.DB["history"].append({"session_id": F, "role": "user", "content": "Explică legea lui Ohm",
                              "timestamp": time.time(), "app_id": "test_local"})
f = AppTest.from_file("app_under_test.py", default_timeout=90)
f.query_params["sid"] = F; f.session_state["_browser_storage"] = {}
f.session_state["materie_selectata"] = "bazele electrotehnicii"
f.run(); chk(f)
ok(any(x.key == "_resend_last" for x in f.button) and any(x.key == "_edit_unanswered" for x in f.button)
   and any("nu a terminat" in x.value for x in f.caption), "mesajul fără răspuns arată „oprit” + Trimite din nou / Modifică")
n = len(SEEN)
f.button(key="_resend_last").click().run(); chk(f)
msgs = f.session_state["messages"]
ok(len(SEEN) == n + 1 and [m["role"] for m in msgs] == ["user", "assistant"],
   "„Trimite din nou”: același mesaj, o singură dată, cu răspuns")
