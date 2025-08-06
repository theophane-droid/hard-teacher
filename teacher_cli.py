#!/usr/bin/env python3
"""
CLI spaced‑repetition trainer – hints + doc links.
Cards (YAML) may add optional fields:
  hint1, hint2  → two progressive hints
  link          → reference URL (e.g., Wikipedia)
Commands during answer:
  /h  reveal next hint (max 2)
  /q  save & quit current session
Configurable via config.json.
Run: python3 cli_learning_tool.py
"""
import os, json, yaml, random, hashlib, sys, webbrowser
from datetime import date, timedelta
from pathlib import Path

try:
    from colorama import init as _cinit, Fore, Style
    _cinit()
except ImportError:  # fallback silently
    class _Dummy:
        def __getattr__(self, _):
            return ""
    Fore = Style = _Dummy()

# ─── Config ───────────────────────────────────────────────────────────────────
CFG_PATH = Path("config.json")
DEFAULT_CFG = {
    "CARDS_DIR": "cards",
    "DATA_FILE": "data.json",
    "UNITS_PER_THEME": 10,
    "REVIEW_VALIDATED": 3,
    "VALID_STREAK_DAYS": 3,
}
CFG = {**DEFAULT_CFG, **json.loads(CFG_PATH.read_text())} if CFG_PATH.exists() else DEFAULT_CFG
CFG_PATH.write_text(json.dumps(CFG, indent=2))  # ensure file exists / updated keys

CARDS_DIR = CFG["CARDS_DIR"]
DATA_FILE = CFG["DATA_FILE"]
U_PER_THEME = CFG["UNITS_PER_THEME"]
REVIEW_VALIDATED = CFG["REVIEW_VALIDATED"]
VALID_STREAK = CFG["VALID_STREAK_DAYS"]

# ─── Storage ──────────────────────────────────────────────────────────────────

def _load_cards():
    cards = {}
    for root, _, files in os.walk(CARDS_DIR):
        for fname in files:
            if fname.endswith((".yml", ".yaml")):
                with open(Path(root)/fname, "r", encoding="utf-8") as fh:
                    for unit in yaml.safe_load(fh) or []:
                        theme = unit.get("meta", {}).get("theme", "misc")
                        q = unit["question"].strip()
                        uid = hashlib.sha1((theme+q).encode()).hexdigest()
                        cards[uid] = {
                            "question": q,
                            "answer": unit["answer"],
                            "context": unit.get("context", ""),
                            "theme": theme,
                            "hints": [h for h in (unit.get("hint1"), unit.get("hint2")) if h],
                            "link": unit.get("link", ""),
                        }
    if not cards:
        sys.exit("No cards found. Put YAML in ./cards or update config.json.")
    return cards


def _init_unit():
    return {"consec_days": 0, "last_date": "", "validated": False, "correct": 0, "wrong": 0}


def _load_data(cards):
    if Path(DATA_FILE).exists():
        data = json.loads(Path(DATA_FILE).read_text())
    else:
        data = {"units": {}, "theme_stats": {}, "daily_pools": {}}
    for uid in cards:
        data["units"].setdefault(uid, _init_unit())
    return data


def _save(data):
    Path(DATA_FILE).write_text(json.dumps(data, indent=2))

# ─── Pool ─────────────────────────────────────────────────────────────────────

def _get_pool(theme, cards, data):
    today = date.today().isoformat()
    pools = data.setdefault("daily_pools", {}).setdefault(today, {})
    if theme in pools:
        return pools[theme]

    pending = [u for u, c in cards.items() if c["theme"] == theme and not data["units"][u]["validated"]]
    validated = [u for u, c in cards.items() if c["theme"] == theme and data["units"][u]["validated"]]

    random.seed(today + theme)
    pool = []
    random.shuffle(pending)
    pool.extend(pending[:U_PER_THEME])

    if len(pool) < U_PER_THEME and validated:
        random.shuffle(validated)
        pool.extend(validated[:min(REVIEW_VALIDATED, U_PER_THEME-len(pool))])

    if len(pool) < U_PER_THEME:
        others = [u for u, c in cards.items() if c["theme"] == theme and u not in pool]
        random.shuffle(others)
        pool.extend(others[:U_PER_THEME-len(pool)])

    pools[theme] = pool
    return pool

# ─── Logic ────────────────────────────────────────────────────────────────────

def _is_correct(ans, user):
    user = user.strip().lower()
    if isinstance(ans, list):
        return user in [str(a).lower() for a in ans]
    return user == str(ans).strip().lower()


def _update_unit(unit, ok):
    today = date.today()
    last = date.fromisoformat(unit["last_date"]) if unit["last_date"] else None
    unit["correct" if ok else "wrong"] += 1
    unit["consec_days"] = (unit["consec_days"] + 1 if last == today - timedelta(days=1) else 1) if ok else 0
    unit["validated"] = unit["consec_days"] >= VALID_STREAK
    unit["last_date"] = today.isoformat()

# ─── CLI helpers ──────────────────────────────────────────────────────────────

def _clear():
    os.system("cls" if os.name == "nt" else "clear")


def _input(msg=""):
    try:
        return input(msg)
    except (EOFError, KeyboardInterrupt):
        _save(DATA)
        sys.exit("\nSaved. Bye!")


def _header(title):
    print(Fore.CYAN + "═"*70 + Style.RESET_ALL)
    print(Fore.YELLOW + f"{title:^70}" + Style.RESET_ALL)
    print(Fore.CYAN + "═"*70 + Style.RESET_ALL)


def _press_enter():
    _input(Fore.BLACK+"[enter]"+Style.RESET_ALL)

# ─── Menus ────────────────────────────────────────────────────────────────────

def _themes(cards):
    counts = {}
    for c in cards.values():
        counts[c["theme"]] = counts.get(c["theme"], 0) + 1
    return counts


def _theme_progress(theme):
    total = sum(1 for u, c in CARDS.items() if c["theme"] == theme)
    done = sum(1 for u, c in CARDS.items() if c["theme"] == theme and DATA["units"][u]["validated"])
    return done, total, int(done/total*100)


def _main_menu():
    while True:
        _clear(); _header("Spaced‑Repetition CLI")
        print("1) Study ✏️")
        print("2) Stats 📊")
        print("3) Save & Exit 💾")
        ch = _input("Choice: ").strip()
        if ch == "1":
            _study_menu()
        elif ch == "2":
            _stats_menu()
        elif ch == "3":
            _save(DATA); sys.exit("Saved. Bye!")


def _study_menu():
    while True:
        _clear(); _header("Choose Theme")
        themes = sorted(_themes(CARDS))
        for i, t in enumerate(themes,1):
            d, tot, pct = _theme_progress(t)
            fl = DATA.get("theme_stats", {}).get(t, {}).get("flames",0)
            print(f"{i}) {t:<20} {d}/{tot} ({pct}%) {'🔥'*fl}")
        print("b) Back")
        sel = _input("Theme: ").strip().lower()
        if sel == "b":
            return
        if sel.isdigit() and 1<=int(sel)<=len(themes):
            _run_session(themes[int(sel)-1])


def _run_session(theme):
    units = _get_pool(theme,CARDS,DATA)
    correct_all = True
    for idx, uid in enumerate(units,1):
        card = CARDS[uid]
        hints_shown = 0
        while True:
            _clear(); _header(f"{theme} [{idx}/{len(units)}]")
            print(card["question"])
            if hints_shown:
                for h in card["hints"][:hints_shown]:
                    print(Fore.BLUE+"Hint: "+h+Style.RESET_ALL)
            print(Style.DIM+"( /h: hint  •  /q: save & quit )"+Style.RESET_ALL)
            cmd = _input(Fore.GREEN+"> "+Style.RESET_ALL).strip().lower()
            if cmd == "/q":
                _save(DATA); return
            if cmd == "/h":
                if hints_shown < len(card["hints"]):
                    hints_shown += 1
                    continue
                else:
                    print(Fore.MAGENTA+"No more hints."+Style.RESET_ALL); _press_enter(); continue
            ok = _is_correct(card["answer"], cmd)
            _update_unit(DATA["units"][uid], ok)
            correct_all &= ok
            print((Fore.GREEN+"✅ Correct" if ok else Fore.RED+f"❌ Wrong. Ans: {card['answer']}")+Style.RESET_ALL)
            if card["context"]:
                print(Fore.BLUE+"ℹ️ "+card["context"]+Style.RESET_ALL)
            if card["link"]:
                print(Style.DIM+f"🔗 {card['link']}"+Style.RESET_ALL)
                if not ok and _input("Open link in browser? [y/N]: ").lower()=="y":
                    webbrowser.open(card["link"], new=2)
            _press_enter(); break
    ts = DATA.setdefault("theme_stats",{}).setdefault(theme,{"flames":0,"attempts":0,"correct":0})
    ts["attempts"] += len(units)
    ts["correct"] += sum(1 for uid in units if DATA["units"][uid]["last_date"]==date.today().isoformat() and DATA["units"][uid]["consec_days"])
    ts["flames"] = ts["flames"] + 1 if correct_all else 0
    _save(DATA); _press_enter()


def _stats_menu():
    _clear(); _header("Statistics")
    total=len(CARDS); validated=sum(u["validated"] for u in DATA["units"].values())
    print(f"Overall: {validated}/{total} ({int(validated/total*100)}%)\n")
    for t in sorted(_themes(CARDS)):
        d, tot, pct=_theme_progress(t)
        fl=DATA.get("theme_stats",{}).get(t,{"flames":0})["flames"]
        print(f"{t:<20} {d}/{tot} ({pct}%) 🔥{fl}")
    _press_enter()

# ─── Main ─────────────────────────────────────────────────────────────────────
if __name__ == "__main__":
    CARDS = _load_cards()
    DATA = _load_data(CARDS)
    _main_menu()

