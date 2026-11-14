# Test cu Supabase și Gemini simulate — rulează prin tests/run_tests.py
"""Materiile din planul ETTI: fiecare are prompt, cuvinte cheie, indicatori și întrebări;
butoanele de pe pagina de start și selectarea unei materii noi ajung la AI cu promptul corect."""
import re, supabase, fake_sb, warnings, logging
logging.disable(logging.WARNING); warnings.filterwarnings("ignore")
supabase.create_client = fake_sb.create_client
import google.genai as genai
SEEN = []
class Chunk:
    def __init__(s, t): s.text = t; s.usage_metadata = None
class Models:
    def generate_content_stream(s, model, contents, config):
        SEEN.append(config.system_instruction or "")
        return iter([Chunk("Răspuns de test suficient de lung pentru verificare.")])
class Caches:
    def create(s, **k): raise Exception("caching not supported")
class C:
    def __init__(s, api_key=None): s.models = Models(); s.caches = Caches(); s.files = None
genai.Client = C
from streamlit.testing.v1 import AppTest
ok = lambda c, m: print(("PASS " if c else "FAIL ") + m)

src = open("app_under_test.py", encoding="utf-8").read()
def block(name):
    i = src.index(name + " = {") if name != "_PROMPT_SUBJECTS" else src.index("_PROMPT_SUBJECTS: dict[str, str] = {")
    j = src.index("\n}\n", i)
    return set(re.findall(r'^    "([^"]+)":', src[i:j], re.M))
i = src.index("MATERII = {"); j = src.index("\n}\n", i)
codes = set(re.findall(r'^    "[^"]+":\s+"([^"]+)",', src[i:j], re.M))
for name in ("_PROMPT_SUBJECTS", "SUBJECT_KEYWORDS", "_STRONG_INDICATORS", "INTREBARI_POOL"):
    missing = codes - block(name)
    ok(not missing, f"{name} are toate cele {len(codes)} materii (lipsă: {sorted(missing)})")
ok({"sisteme de operare", "electronică digitală", "modele spice", "programare orientată pe obiecte",
    "grafică asistată de calculator", "programare python și matlab",
    "tehnici cad pentru module electronice"} <= codes, "materiile noi (INF + opționale an II) sunt în MATERII")

at = AppTest.from_file("app_under_test.py", default_timeout=90)
at.query_params["sid"] = "c" * 64; at.session_state["_browser_storage"] = {}
at.run()
assert not at.exception, [e.value for e in at.exception]
labels = [b.label for b in at.button]
ok(any("Sisteme de Operare 1" in l for l in labels) and any("Modele SPICE" in l for l in labels),
   "pagina de start are butoane pentru materiile noi")
btn = at.button(key="pick_mat_sisteme de operare")
btn.click().run()
assert not at.exception, [e.value for e in at.exception]
at.chat_input[0].set_value("Cum dau drepturi de execuție unui fișier?").run()
assert not at.exception, [e.value for e in at.exception]
ok(SEEN and "SISTEME DE OPERARE 1" in SEEN[-1], "promptul trimis la AI conține blocul Sisteme de Operare 1")

# Detecția automată a materiei (mod „🤖 Automat”) — materii noi + regresii pe cele vechi
ns = {}
for name in ("SUBJECT_KEYWORDS", "_STRONG_INDICATORS"):
    i = src.index(name + " = {"); j = src.index("\n}\n", i); exec(src[i:j + 2], ns)
i = src.index("def detect_subject_from_text"); j = src.index("\ndef get_detected_subject", i)
exec(src[i:j], ns)
detect = ns["detect_subject_from_text"]
CASES = [
    ("Cum dau chmod 755 unui script bash în Ubuntu?", "sisteme de operare"),
    ("Cum descriu în Verilog un automat Moore care detectează 101?", "electronică digitală"),
    ("Cum fac o piesă cu Sheet Metal în Autodesk Inventor?", "grafică asistată de calculator"),
    ("Cum rezolv o ecuație diferențială cu ode45 în Matlab?", "programare python și matlab"),
    ("Explică modelul Ebers-Moll și efectul Early în SPICE", "modele spice"),
    ("Ce înseamnă design for manufacturing și management termic la PCB multistrat?", "tehnici cad pentru module electronice"),
    ("Explică moștenirea și polimorfismul în Java", "programare orientată pe obiecte"),
    ("Cum aplic teorema lui Thévenin la un circuit cu două surse?", "bazele electrotehnicii"),
    ("Cum simplific o funcție booleană cu harta Karnaugh?", "circuite integrate digitale"),
    ("Cum funcționează un amplificator operațional inversor?", "circuite electronice fundamentale"),
    ("Cum dimensionez stabilizatorul cu diodă Zener și oscilatorul Colpitts?", "circuite electronice fundamentale"),
    ("Cum folosesc un pointer în C și ce face #include?", "programarea calculatoarelor și limbaje de programare"),
    ("Ce este un INNER JOIN în SQL?", "baze de date"),
]
bad = [(q, e, detect(q)) for q, e in CASES if detect(q) != e]
ok(not bad, f"detecția automată recunoaște corect {len(CASES) - len(bad)}/{len(CASES)} întrebări {bad}")
