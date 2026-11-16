# Test cu Supabase și Gemini simulate — rulează prin tests/run_tests.py
"""Butonul „🧭 Orientare Specializare”: ghidul actualizat ajunge la AI, conversația de orientare
se redeschide tot în modul orientare (chiar dacă înainte era selectată o materie)."""
import supabase, fake_sb, warnings, logging
logging.disable(logging.WARNING); warnings.filterwarnings("ignore")
supabase.create_client = fake_sb.create_client
import google.genai as genai
SEEN = []
class Chunk:
    def __init__(s, t): s.text = t; s.usage_metadata = None
class Models:
    def generate_content_stream(s, model, contents, config):
        SEEN.append(config.system_instruction or "")
        return iter([Chunk("Răspuns de orientare suficient de lung pentru test.")])
class Caches:
    def create(s, **k): raise Exception("caching not supported")
class C:
    def __init__(s, api_key=None): s.models = Models(); s.caches = Caches(); s.files = None
genai.Client = C
from streamlit.testing.v1 import AppTest
ok = lambda c, m: print(("PASS " if c else "FAIL ") + m)
def chk(a): assert not a.exception, [e.value for e in a.exception]

a = AppTest.from_file("app_under_test.py", default_timeout=90)
a.query_params["sid"] = "c7" * 32; a.session_state["_browser_storage"] = {}
a.session_state["materie_selectata"] = "bazele electrotehnicii"
a.run(); chk(a)
next(t for t in a.toggle if t.label == "🧭 Orientare Specializare").set_value(True).run(); chk(a)
osid = a.session_state["session_id"]
ok(a.session_state["orientare_mode"] and osid != "c7" * 32, "Orientare: pornește o conversație nouă, dedicată")
a.chat_input[0].set_value("Ce specializare mi se potrivește dacă îmi place programarea?").run(); chk(a)
p = SEEN[-1] if SEEN else ""
ok("consilier de carieră" in p and "GHID DE SPECIALIZĂRI" in p, "promptul de orientare ajunge la AI")
ok("CTI" in p and "repartizați automat la INF" in p and "etti.pub.ro/specializari" in p,
   "ghidul explică: INF = domeniul CTI (fără alegere), opțiunile IETTI se dau online")
ok("Celestica (Oradea/Borș" in p and "Jabil" not in p and "Kromberg" not in p,
   "angajatorii corectați (Celestica la Oradea; scoase Jabil/Kromberg, neverificate)")
b = AppTest.from_file("app_under_test.py", default_timeout=90)
b.query_params["sid"] = osid; b.session_state["_browser_storage"] = {}
b.run(); chk(b)
n = len(SEEN)
b.chat_input[0].set_value("Și ce discipline are MON în anul IV?").run(); chk(b)
ok(b.session_state.get("orientare_mode") and len(SEEN) == n + 1 and "GHID DE SPECIALIZĂRI" in SEEN[-1],
   "conversația de orientare redeschisă rămâne în modul orientare (nu revine la materia de dinainte)")
