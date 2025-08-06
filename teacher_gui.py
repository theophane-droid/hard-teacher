#!/usr/bin/env python3
"""
Web spaced‑repetition trainer (NiceGUI ≥2.2) – sync dialogs & submit button.
Run: python3 nicegui_trainer.py   → http://127.0.0.1:8080
Dependencies: pip install nicegui pyyaml
"""
import os, json, yaml, random, hashlib, sys, webbrowser
from datetime import date, timedelta
from pathlib import Path
from nicegui import ui

# ─── Config ───────────────────────────────────────────────────────────────────
CFG_PATH = Path("config.json")
DEFAULT_CFG = {
    "CARDS_DIR": "cards",
    "DATA_FILE": "data.json",
    "UNITS_PER_THEME": 10,
    "REVIEW_VALIDATED": 3,
    "VALID_STREAK_DAYS": 3,
}
CFG = {**DEFAULT_CFG, **(json.loads(CFG_PATH.read_text()) if CFG_PATH.exists() else {})}
CFG_PATH.write_text(json.dumps(CFG, indent=2))
CARDS_DIR, DATA_FILE = CFG["CARDS_DIR"], CFG["DATA_FILE"]
U_PER_THEME, REVIEW_VALID, VALID_STREAK = CFG["UNITS_PER_THEME"], CFG["REVIEW_VALIDATED"], CFG["VALID_STREAK_DAYS"]

# ─── Data I/O ─────────────────────────────────────────────────────────────────

def load_cards():
    cards = {}
    for root, _, files in os.walk(CARDS_DIR):
        for fn in files:
            if fn.endswith((".yml", ".yaml")):
                with open(Path(root)/fn, encoding="utf-8") as fh:
                    for u in yaml.safe_load(fh) or []:
                        theme=u.get("meta",{}).get("theme","misc")
                        q=u["question"].strip()
                        uid=hashlib.sha1((theme+q).encode()).hexdigest()
                        cards[uid]={
                            "question":q,"answer":u["answer"],
                            "context":u.get("context",""),"theme":theme,
                            "hints":[h for h in (u.get("hint1"),u.get("hint2")) if h],
                            "link":u.get("link",""),
                        }
    if not cards:
        sys.exit("No YAML cards found in ./cards")
    return cards


def init_unit():
    return {"consec_days":0,"last_date":"","validated":False,"correct":0,"wrong":0}


def load_data(cards):
    if Path(DATA_FILE).exists():
        data=json.loads(Path(DATA_FILE).read_text())
    else:
        data={"units":{},"theme_stats":{},"daily_pools":{}}
    for uid in cards:
        data["units"].setdefault(uid,init_unit())
    return data


def save():
    Path(DATA_FILE).write_text(json.dumps(DATA,indent=2))

# ─── Core logic ───────────────────────────────────────────────────────────────

def get_pool(theme):
    today=date.today().isoformat()
    pools=DATA.setdefault("daily_pools",{}).setdefault(today,{})
    if theme in pools:
        return pools[theme]
    pending=[u for u,c in CARDS.items() if c["theme"]==theme and not DATA["units"][u]["validated"]]
    validated=[u for u,c in CARDS.items() if c["theme"]==theme and DATA["units"][u]["validated"]]
    random.seed(today+theme)
    pool=random.sample(pending,min(len(pending),U_PER_THEME))
    if len(pool)<U_PER_THEME and validated:
        pool+=random.sample(validated,min(len(validated),REVIEW_VALID,U_PER_THEME-len(pool)))
    if len(pool)<U_PER_THEME:
        others=[u for u,c in CARDS.items() if c["theme"]==theme and u not in pool]
        pool+=random.sample(others,min(len(others),U_PER_THEME-len(pool)))
    pools[theme]=pool
    return pool


def is_correct(ans,user):
    user=user.strip().lower()
    if isinstance(ans,list):
        return user in [str(a).lower() for a in ans]
    return user==str(ans).strip().lower()


def update_unit(unit, ok):
    today=date.today(); last=date.fromisoformat(unit["last_date"]) if unit["last_date"] else None
    unit["correct" if ok else "wrong"]+=1
    unit["consec_days"]=(unit["consec_days"]+1 if last==today-timedelta(days=1) else 1) if ok else 0
    unit["validated"]=unit["consec_days"]>=VALID_STREAK
    unit["last_date"]=today.isoformat()

# ─── Helpers ──────────────────────────────────────────────────────────────────

def theme_counts():
    out={}
    for c in CARDS.values():
        out[c["theme"]]=out.get(c["theme"],0)+1
    return out


def theme_progress(t):
    total=sum(1 for u,c in CARDS.items() if c["theme"]==t)
    done=sum(1 for u,c in CARDS.items() if c["theme"]==t and DATA["units"][u]["validated"])
    return done,total,int(done/total*100)

# ─── UI state ────────────────────────────────────────────────────────────────
SESSION={}

# ─── Pages ────────────────────────────────────────────────────────────────────
@ui.page("/")
def home():
    ui.label("Spaced‑Repetition Trainer").classes("text-2xl font-bold m-4")
    ui.button("Study ✏️", on_click=lambda: ui.navigate.to("/study"), color="primary")
    ui.button("Stats 📊",  on_click=lambda: ui.navigate.to("/stats"), color="secondary")

@ui.page("/study")
def choose_theme():
    ui.button("⬅ Back", on_click=lambda: ui.navigate.to("/"))
    ui.label("Choose Theme").classes("text-xl mt-4")
    for t in sorted(theme_counts()):
        d,tot,pct=theme_progress(t)
        ui.button(f"{t}  {d}/{tot} ({pct}%)", color="primary", on_click=lambda t=t: start_session(t)).classes("w-full justify-start m-1")

# ─── Session ─────────────────────────────────────────────────────────────────-

def start_session(theme):
    SESSION.update({"theme":theme,"pool":get_pool(theme),"idx":0,"hints":{}})
    ui.navigate.to("/question")

@ui.page("/question")
def question_page():
    if "theme" not in SESSION:
        ui.navigate.to("/"); return
    pool,idx=SESSION["pool"],SESSION["idx"]
    if idx>=len(pool):
        finish();return
    uid=pool[idx]; card=CARDS[uid]
    hints=SESSION["hints"].get(uid,0)

    ui.label(f"{SESSION['theme']}  [{idx+1}/{len(pool)}]").classes("text-lg font-bold mb-2")
    ui.markdown(card["question"]).classes("text-xl mb-2")
    for h in card["hints"][:hints]:
        ui.label("Hint: "+h).classes("text-blue-600")

    answer = ui.input(label="Your answer").props("autofocus")
    ui.button("Submit", color="primary", on_click=lambda: check_answer(answer.value, card, uid))
    ui.button("Show hint", on_click=lambda: reveal_hint(uid))
    ui.button("Quit", color="negative", on_click=lambda: (save(), ui.navigate.to("/")))


def reveal_hint(uid: str) -> None:
    card = CARDS[uid]
    shown = SESSION["hints"].get(uid, 0)
    if shown >= len(card["hints"]):
        ui.notify("No more hints", color="warning")
        return
    SESSION["hints"][uid] = shown + 1
    hint_text = card["hints"][shown]

    dlg = ui.dialog()
    with dlg, ui.card():
        ui.label("💡 Hint").classes("text-lg font-bold")
        ui.label(hint_text).classes("m-2")
        ui.button("OK", on_click=dlg.close)
    dlg.open()


def check_answer(text, card, uid):
    ok=is_correct(card["answer"], text)
    update_unit(DATA["units"][uid], ok)
    dlg=ui.dialog()
    with dlg, ui.card():
        ui.label("✅ Correct" if ok else f"❌ Wrong. Answer: {card['answer']}").classes("text-lg")
        if card["context"]:
            ui.label("ℹ️ "+card["context"]).classes("text-blue-600")
        if card["link"]:
            ui.link(card["link"], card["link"], new_tab=True).classes("text-gray-500")
        ui.button("Next", on_click=lambda: (dlg.close(), next_question()))
    dlg.open()

def next_question():
    SESSION["idx"]+=1
    # ui.navigate.to(f"/question?step={SESSION['idx']}")
    ui.run_javascript("window.location.assign('/question');")


def finish():
    theme=SESSION["theme"]; pool=SESSION["pool"]
    correct_all=all(DATA["units"][u]["last_date"]==date.today().isoformat() and DATA["units"][u]["consec_days"] for u in pool)
    st=DATA.setdefault("theme_stats",{}).setdefault(theme,{"flames":0,"attempts":0,"correct":0})
    st["attempts"]+=len(pool)
    st["correct"] += sum(1 for u in pool if DATA["units"][u]["last_date"]==date.today().isoformat() and DATA["units"][u]["consec_days"])
    st["flames"]   = st["flames"]+1 if correct_all else 0
    save()
    ui.label("Session complete!").classes("text-2xl m-4")
    ui.button("Back to home", on_click=lambda: ui.navigate.to("/"))

# ─── Stats ────────────────────────────────────────────────────────────────────
@ui.page("/stats")
def stats_page():
    ui.button("⬅ Back", on_click=lambda: ui.navigate.to("/"))
    total=len(CARDS); validated=sum(u["validated"] for u in DATA["units"].values())
    ui.label(f"Overall: {validated}/{total} ({int(validated/total*100)}%)").classes("text-lg m-2")
    for t in sorted(theme_counts()):
        d,tot,pct=theme_progress(t)
        fl=DATA.get("theme_stats",{}).get(t,{"flames":0})["flames"]
        ui.label(f"{t}: {d}/{tot} ({pct}%)  🔥{fl}")

# ─── Run ──────────────────────────────────────────────────────────────────────
CARDS=load_cards()
DATA =load_data(CARDS)
ui.run(reload=False)

