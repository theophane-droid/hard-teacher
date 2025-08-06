# 🧠 Spaced Repetition Trainer (CLI + Web UI)

A minimal, theme-based spaced repetition tool to memorize facts through progressive hints, daily sessions, and performance tracking — all powered by YAML cards.

## ✨ Features

- 🗂️ Learn by **theme** (e.g. History, Politics)
- 📅 Daily sessions: repeat until you master each unit for 3 days in a row
- 📈 Stats and 🔥 streak tracking per theme
- 🤔 Two progressive **hints** per question
- 📚 Context + external link shown after each answer
- 💻 Fully functional in both:
  - Command-line interface (`teacher_cli.py`)
    - Web interface using [NiceGUI](https://nicegui.io) (`nicegui_trainer.py`)

    ## 📁 Card Format

    Knowledge units are defined in simple YAML files inside the `cards/` folder. Each file contains a list of questions:

    ```yaml
    - meta:
            theme: histoire_france
          question: "In which year did Clovis defeat Syagrius?"
            answer: 486
              hint1: "End of the 5th century."
                hint2: "Roughly 10 years after 476."
                  context: "Marked the beginning of the Merovingian kingdom."
                    link: "https://en.wikipedia.org/wiki/Clovis_I"
                    ````

Cards must include:

* `question`: the prompt shown to the user
* `answer`: expected answer (exact match, not case sensitive)

Optional fields:

* `hint1`, `hint2`: progressively revealed on request
* `context`: shown after the attempt
* `link`: external reference

> 📌 **Note**: The two sample decks (`histoire_france.yml` and `politique_france.yml`) are written in **French**.

## 🖥️ Usage

### CLI mode

```bash
python3 teacher_cli.py
```

### Web mode

```bash
python3 teacher_gui.py
# Then open http://localhost:8080
```

## 🗃️ Config

All settings are editable in `config.json`:

```json
{
      "CARDS_DIR": "cards",
  "DATA_FILE": "data.json",
  "UNITS_PER_THEME": 10,
  "REVIEW_VALIDATED": 3,
  "VALID_STREAK_DAYS": 3
}
    ```

## ⚙️ Requirements

Install with:

```bash
pip install nicegui pyyaml colorama
```

## 🧠 Designed for

* Self-learners
* Students preparing for exams
* Anyone memorizing structured factual knowledge (history, dates, laws, vocab...)

---

Made with ❤️ for discipline and memory.

