# moodle-qc – the question converter

Write Moodle questions as Markdown files in git, and turn them into a Moodle XML **import file** with one command. Moodle exports can be turned back into Markdown, so existing question banks and edits made in Moodle end up in git too.

```sh
moodle-qc generate questions/          # question sources → moodle-import.xml
moodle-qc check questions/             # validate, write nothing (good for CI)
moodle-qc preview questions/           # local HTML page to review questions
moodle-qc extract export.xml --into questions/   # Moodle export → question sources
```

Supported question types: `multichoice`, `sc`, `kprime`, `mtf` (the last three are ETH Zurich plugins) and `ddwtos` (drag and drop into text). Questions of any other type are kept as [raw question sources](#raw-question-sources).

The words used here (question source, question collection, category, …) are defined in [`CONTEXT.md`](CONTEXT.md).

## Installation

**With Docker** (no Python needed). Run it from the folder of your question collection:

```sh
docker run --rm --user "$(id -u):$(id -g)" -v "$PWD:/questions" \
  ghcr.io/peschmae/moodle-question-converter generate .
```

`--user` makes the written files belong to you; `/questions` is the working directory inside the container, so all paths are relative to the mounted folder.

**From this repo** (needs [uv](https://docs.astral.sh/uv/)):

```sh
git clone https://github.com/peschmae/moodle-question-converter
cd moodle-question-converter
uv sync
uv run moodle-qc --help
```

## The question collection

A question collection is a folder tree of question sources (`.md` files, one question each) with a **collection config** `moodle-qc.yaml` at its root. The converter finds the root by searching upwards from the folders you pass, so you can run it from anywhere inside the collection.

```text
questions/
├── moodle-qc.yaml
├── SW07_prometheus/
│   ├── datenmodell.md
│   └── pull-vs-push.md
└── SW09_alerting/
    ├── error-budget.md
    ├── dashboard.png
    └── burn_rate/
        └── fast-burn.md
```

**Folders become categories**, relative to the collection root: `_` becomes a space and the first letter of each word is capitalised; nothing else changes (dashes stay, `SW09` stays `SW09`). The example gives the categories `SW07 Prometheus`, `SW09 Alerting` and `SW09 Alerting/Burn Rate`, below the root category if one is set. A question always lands in the same category, however much of the collection you generate. Files named `README.md` and hidden folders are ignored.

**Question ID**: each question gets a stable ID from its path (`sw09-alerting-error-budget`), written to Moodle's ID number field. It links a question in Moodle back to its question source. Set `id:` in the front matter to keep the ID when you move or rename the file.

### Collection config (`moodle-qc.yaml`)

All settings are optional.

```yaml
root_category: 26hs              # all categories go below this one (--root-category overrides it)
allowed_types: [multichoice, sc, kprime, mtf, ddwtos, ddimageortext]   # the types your Moodle has
code_line_height: 1.2            # line height of code blocks in Moodle

defaults:                        # for every question; a question source can override each value
  points: 1
  penalty: 0.3333333             # deduction per wrong try (interactive mode); 0 for exams
  shuffle: true
  tags: [26hs]                   # tags are combined with the question's own tags
  feedback:                      # Moodle's combined feedback (multichoice, ddwtos)
    correct: Die Antwort ist richtig.
    partially: Die Antwort ist teilweise richtig.
    incorrect: Die Antwort ist falsch.

types:                           # defaults per question type
  kprime:
    scoring: kprime              # kprime | kprimeonezero | subpoints
    labels: [richtig, falsch]
  mtf:
    scoring: subpoints           # subpoints | mtfonezero | subpointdeduction
    labels: [richtig, falsch]
  sc:
    scoring: sconezero           # sconezero | aprime | subpoints
```

Settings are merged in this order: built-in defaults → `defaults` → `types.<type>` → the question source's front matter. Tags are combined at every level; every other value is replaced.

## Question sources

```markdown
---
type: sc
points: 2
---

# Error Budget

Was beschreibt ein **Error Budget**?

## Answers
- [ ] Das Budget für Monitoring-Infrastruktur.
  > Nein, es geht um Zuverlässigkeit.
- [x] Die erlaubte Unzuverlässigkeit gemäss SLO (1 − SLO).

## Solution

Error Budget = 1 − SLO. Shown to graders; hide it from students via the quiz's review options.

## Notes

Private remarks. Never sent to Moodle.
```

- **Front matter** (between `---`): `type` is required. Common keys: `id`, `name`, `category`, `lang`, `points`, `penalty`, `shuffle`, `tags`, `feedback`, plus the type-specific keys below.
- **Question name**: `name:` in the front matter, else the first `# heading`, else the file name. The first heading is never part of the question text, so you can give a file a readable title.
- **Question text**: everything after the first heading up to the first fixed section.
- **Fixed sections** (English headings, whatever the question's language): `## Answers`, `## Solution` (→ Moodle's general feedback), `## Notes` (stays in git).
- **Category**: from the folder; `category: Some/Path` in the front matter places the question elsewhere (used as written, without the root category).

### Markdown

Paragraphs, `#` headings, lists (`-` and `1.`, one level), `` `code` ``, `**bold**`, `*italic*`, `[links](https://…)` and images. Fenced code blocks become `<pre>` blocks styled with the configured line height; `<`, `>` and `&` inside code are escaped for you. Raw HTML is allowed: a block starting with `<` is passed through, and a ```` ```{=html} ```` block passes through anything (also blank lines).

**Images**: `![Panel](dashboard.png)` with a path relative to the question source (`../shared/logo.png` works too). Generate embeds the image in the import file.

### `sc` – single choice (ETH)

Exactly one `[x]`. Front matter: `scoring` (`sconezero` | `aprime` | `subpoints`), `numbering`.

### `multichoice`

`[x]` marks correct answers. One `[x]` gives radio buttons, several give checkboxes; `multiple: true` forces checkboxes even with one correct answer, so students can't tell how many are correct.

With checkboxes, the correct answers share 100 % and every wrong answer deducts the same share, so ticking everything scores zero. Override a single answer with `- [x] {50%} …` or `- [ ] {-25%} …` (at the start of the answer); the other correct answers share what is left of the 100 %; Moodle only accepts its own list of percentages (100, 90, 83.33333, 80, 75, 70, 66.66667, 60, 50, 40, 33.33333, 30, 25, 20, 16.66667, 14.28571, 12.5, 11.11111, 10, 5, 0), and check reports any other value. Front matter: `multiple`, `numbering` (`abc` | `ABCD` | `123` | `iii` | `IIII` | `none`), `show_instruction`, `feedback`, `show_num_correct`.

### `kprime` and `mtf` – true/false judgements (ETH)

`[x]` means the statement is true, `[ ]` false. `kprime` needs exactly four answers. Front matter: `scoring`, `labels` (the two judgement labels, e.g. `[richtig, falsch]`); `mtf` also `numbering` and `deduction`. These plugins ignore Moodle's combined feedback, so none is written.

### `ddwtos` – drag and drop into text

Write each gap with its correct word and gap group: `[[word|group]]`. Gaps work inside code blocks too. A gap only accepts words of its own gap group, and Moodle colours each group differently. List the distractors per gap group in the front matter:

````markdown
---
type: ddwtos
points: 4
penalty: 0
distractors:
  suffix: [sum, total]
  bound: ['5', '5000']
  function: [absent_over_time, count]
---

# Latenz-SLI und fehlendes Target

```
rate(chatbot_reply_duration_seconds_[[bucket|suffix]]{le="[[5.0|bound]]"}[5m])
rate(chatbot_reply_duration_seconds_[[count|suffix]][5m])
expr: [[absent|function]](up{service="chatbots-alan-llm"} == 1)
```

Ziehen Sie die passenden Begriffe in die Lücken.
````

- `[[word]]` without a group uses one shared group; its distractors can then be a plain list (`distractors: [a, b]`).
- A word may be correct in one group and a distractor in another (`count` above).
- Words are used once. `reusable: [suffix]` lets the words of a gap group fill several gaps.
- Quote numbers and words starting with special characters in YAML (`'5'`, `'> 1'`).
- check reports gap groups without a distractor, distractor groups no gap uses, and duplicate words in a group.

### Raw question sources

Questions of other types (`ddimageortext`, `stack`, `essay`, …) are extracted as raw question sources: `type: raw` and the original `<question>` element in one ```` ```xml ```` block. Generate writes it back unchanged (only the question ID is set). Edit them in Moodle, or carefully in the XML. `allowed_types` is checked against the question type inside the XML (`ddimageortext`, not `raw`).

## Commands

| Command | What it does |
|---|---|
| `moodle-qc generate PATHS… [-o FILE] [--root-category CAT]` | Validates the selected question sources (files or folders) and writes one import file (default `moodle-import.xml`). Writes nothing if anything is invalid. |
| `moodle-qc check PATHS…` | Validates without writing anything; exits non-zero on problems, each naming the question source. |
| `moodle-qc preview PATHS… [-o FILE]` | Writes an HTML page (default `moodle-preview.html`) showing the questions roughly as in Moodle, with correct answers, gaps and solutions. |
| `moodle-qc extract EXPORT [--into FOLDER]` | Turns a Moodle XML export into question sources inside the collection containing `FOLDER` (default: current folder). |

**Extract** overwrites a question source whose question ID matches, wherever it is, and refuses if that file (or an image it would replace) has uncommitted git changes. New questions get a folder from their category (spaces become `_`) and a file name from their question name; a question without ID gets the one of that path (category folder + name), written to its front matter. Embedded images are written next to the question source (`image-2.png` if the name is taken by a different image). Extract reads every question source of the collection first to find question IDs, so an unreadable one stops it: fix it, then extract again. Moodle HTML becomes Markdown only where converting it back gives the same HTML; anything else stays as raw HTML. Notes, and front matter Moodle can't know (`id`, `name`, `category`, `lang`), are kept.

## Importing into Moodle

1. `moodle-qc generate questions/ --output import.xml`
2. In the course: *Question bank → Import*, format **Moodle XML format**.
3. Tick **Get category from file** (otherwise all questions land in the category selected on the import page), and upload the import file.
4. Build the quiz from the imported categories.

Things to know:

- **Importing creates new questions; it never updates existing ones.** Importing the same question twice gives two copies (Moodle silently drops the duplicate question ID). To change a question that is already in a quiz, import it again and replace it in the quiz, or import into a fresh category (`--root-category import-2026-11-13`).
- **The Solution is Moodle's general feedback.** Students see it after an attempt unless the quiz's *Review options* hide *General feedback*; switch it off for exams. Graders always see it.
- **Renaming a folder creates a new category** on the next import, because Moodle matches categories by exact name.
- Question types from plugins (`kprime`, `mtf`, `sc`) must be installed on the target Moodle; list the types your Moodle has in `allowed_types` so check catches the rest.
- Edits made directly in Moodle don't flow back by themselves: export the questions and run `extract`, then review the git diff.

## Development

Requires [uv](https://docs.astral.sh/uv/). Design documents: [`docs/spec-moodle-qc-v1.md`](docs/spec-moodle-qc-v1.md), decisions in [`docs/adr/`](docs/adr/), Moodle XML facts in [`docs/moodle-format-notes.md`](docs/moodle-format-notes.md).

```sh
uv sync                    # install dependencies
uv run pytest              # run all tests
uv run mypy                # type-check
uv run ruff check .        # lint
uv run ruff format .       # format
uv run moodle-qc --help    # run the command
```

Tests run on two levels: unit tests at each module's interface (`tests/unit/`) and integration tests that run the commands on temporary question collections (`tests/integration/`). Real Moodle files in `tests/fixtures/moodle/` and the collections in `tests/fixtures/collections/` that reproduce them are the reference for both directions.
