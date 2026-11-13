# Moodle question tool – findings (2026-11-13)

Goal: write Moodle questions outside the Moodle UI (as files in git) and generate Moodle XML for import.
Target instance: `moodle.assessment.fhnw.ch` (no admin rights).

## Decision: generate Moodle XML, don't use the API

- Moodle core has **no web service to create or edit questions**. Writing our own needs a local PHP plugin installed by the admins.
- Community plugins (`local_qbankremotemanager`, `local_questions_importer_ws`) only upload **Moodle XML** too.
- So: questions live as question sources (Markdown + YAML front matter) in git → `moodle-qc generate` writes Moodle XML → import via *Question bank → Import → Moodle XML*.
- Caveat: import always **creates new questions**, it never updates existing ones. The source files are the single source of truth; fixes after students have attempted a question need care.

## Question types available on the instance

From the "Add a question" dialog. First column = value for `<question type="…">`.

| Type | Origin | Converter priority (v1 = first version; all others as raw question sources) |
|---|---|---|
| `multichoice` | core | v1 |
| `truefalse` | core | later |
| `shortanswer` | core | later |
| `numerical` | core | later |
| `match` | core | later |
| `ordering` | core since Moodle 4.4 (plugin before) | later |
| `gapselect` | core | next after v1 (same gap syntax as `ddwtos`) |
| `ddwtos` | core | v1 – import tested OK |
| `multianswer` (Cloze) | core | later |
| `essay` | core | – |
| `calculated`, `calculatedsimple`, `calculatedmulti` | core | – |
| `ddimageortext` | core | stretch goal (SVG → PNG + drop zones) |
| `ddmarker` | core | – |
| `randomsamatch` | core | – |
| `kprime` | ETH Zurich plugin | v1 – round trip tested OK |
| `mtf` | ETH Zurich plugin | v1 – round trip tested OK |
| `sc` | ETH Zurich plugin | v1 – round trip tested OK |
| `lti` (Externer Fragetyp) | ETH Zurich plugin | – |
| `multichoiceset` (all-or-nothing) | community plugin | – |
| `essayautograde` | community plugin (Gordon Bateson) | – |
| `recordrtc` | Open University plugin | – |
| `stack` | STACK project plugin | – |

How to check this without admin rights: the "Add a question" dialog (authoritative); optionally the mobile-app web service (`core_webservice_get_site_info`, `tool_mobile_get_plugins_supporting_mobile`) or probing `/question/type/<name>/pix/icon.svg`.

## Reference files (`tests/fixtures/moodle/`)

- `moodle-xml-reference.xml` – `multichoice`, `kprime`, `mtf`, `sc`, built from source code (Moodle core `public/question/format/xml/format.php`, `ethz-let/moodle-qtype_*/questiontype.php`) and **verified by import + re-export** on the instance. Only remaining difference to the export: `defaultgrade` `1` vs `1.0000000`.
- `sample-ddimageortext.xml` – real export of "Zuordnung Metrik-Typen" (background image replaced by a placeholder).
- `sample-ddwtos.xml` – the two SW09 alerting gap questions, hand-written import file that imported successfully.
- `sample-ddwtos-export.xml` – Moodle's export of G2 after import and after manual edits in Moodle (name shortened, `line-height` 1.2). Confirms the `ddwtos` structure 1:1.

## Format rules per type

### Common (all types, written by core)
`name`, `questiontext`, `generalfeedback`, `defaultgrade`, `penalty`, `hidden`, `idnumber`, `tags`.

### multichoice
- `<single>true</single>` = radio buttons, `false` = checkboxes.
- `<answer fraction="…">` in percent. Single: one answer = 100. Multiple: positives sum to 100, wrong answers may be negative.
- `answernumbering`: `abc | ABCD | 123 | iii | IIII | none`.
- Combined feedback (correct / partially / incorrect) + `<shownumcorrect/>`.

### kprime / mtf (ETH)
- Rows = statements (`<row number>` with `optiontext` + `feedbacktext`), columns = judgement labels (`<responsetext>`, format `moodle_auto_format`; plugin reads only the text).
- Correct judgement per row = the column whose `<weight>` value is > 0; one `<weight>` per row/column pair.
- kprime: exactly 4 rows × 2 columns. `scoringmethod`: `kprime` (default) | `kprimeonezero` | `subpoints`.
- mtf: any number of rows; also `<answernumbering>none</answernumbering>` and `<deduction>0</deduction>`. `scoringmethod`: `subpoints` (default) | `mtfonezero` | `subpointdeduction` (only if admin enabled deductions).
- `scoringmethod` is wrapped in `<text>`.
- The import **ignores combined feedback and hints**; per-row feedback and general feedback work.

### sc (ETH)
- Rows only, `<correctrow>` = number of the correct row.
- `scoringmethod`: `sconezero` (default) | `aprime` | `subpoints`.
- `<answernumbering>` wraps `<text>` (unlike mtf).

### ddwtos (Drag&drop auf Text)
Reference: `sample-ddwtos.xml` (the two SW09 alerting gap questions; imported successfully).
- Question text contains `[[1]]`, `[[2]]` …; gap `[[n]]` is answered by the n-th `<dragbox>` (1-based). So the correct words come first, distractors after.
- `<dragbox><text>word</text><group>g</group></dragbox>`, optional `<infinite/>` (word can be used more than once). Dragbox text is plain text.
- **Groups restrict which words fit a gap**: a gap only accepts dragboxes of the same group as its correct answer, and Moodle colours each group differently. Pattern used in the exam: one group per kind of gap (keywords, functions, labels, numbers, operators, severities), each with 2–4 plausible distractors.
- The same word may appear in two groups (e.g. `count` in group 1 and 3).
- Score is split equally across the gaps (`defaultgrade` 4 with 8 gaps = 0.5 each). `penalty` 0 suits exams.
- `<shuffleanswers>1</shuffleanswers>` (numeric form also accepted).
- Code in the question: **`<pre style="font-family: monospace; line-height: 1.2;">`** (decided: 1.2 – the first import used 2.2, changed by hand in Moodle).
- Export vs. import file: identical apart from formatting – Moodle adds an empty `<idnumber>`, puts line breaks between HTML blocks, and writes `> 1` as `<![CDATA[> 1]]>` instead of `&gt; 1` (equivalent).
- Generator checks worth adding: every gap number has a dragbox, each gap's group has at least one distractor, no duplicate word within a group.

### ddimageortext (Drag&drop auf ein Bild)
- Background PNG as base64 `<file>` directly inside `<question>`.
- `<drag>`: `<no>`, `<text>`, `<draggroup>`, optional `<infinite/>`. Unreferenced drags = distractors.
- `<drop>`: `<choice>` = `<no>` of the correct drag; `<xleft>`/`<ytop>` = **top-left corner in the image's own pixels**. No zone size stored – Moodle sizes zones to the largest drag in the group.
- Generator idea: author the image as SVG with marked boxes (`id="drop-1"` …), render the PNG at a fixed width (e.g. 1200 px), compute zone positions from the same render, centre with an estimated label width.

## Converter conventions (decided)

- **Text content goes into CDATA, not XML escaping**: every `<text>` with special characters is written as `<![CDATA[…]]>` (also plain-text fields such as dragbox labels: `<text><![CDATA[> 1]]></text>`, the way Moodle exports it).
  - CDATA cannot contain `]]>`; if it ever occurs, split it (`]]]]><![CDATA[>`).
  - CDATA only replaces the XML layer. Fields that are HTML (question text, feedback, options) are still HTML inside: in code `<` and `&` must be written `&lt;` / `&amp;` (e.g. PromQL `rate(x[5m]) < 0.1`), otherwise the browser reads them as tags. `>` may stay literal. The generator does this for code blocks automatically.
- `ddwtos` code blocks use `line-height: 1.2`.

## Categories

- Category entries (`<question type="category">`) apply to all following questions until the next one.
- Nested paths work: `import-test/SW07` creates missing levels.
- Write paths **without** `$course$/` and **without** `top/`: they are then created in the question bank you import into (Moodle 4.x and 5.x). In 5.x a `$course$/` prefix is deprecated and redirected to a default course question bank. A path starting with `top/` and fewer than three levels gets an extra `top` prepended.
- Import option **"Get category from file"** must be ticked.
- Exports always write full paths (`$course$/top/import-test/SW07`) plus an entry for each parent – the generator does not need to.

## Design decisions (design interview, 2026-11-13)

Terms: see `CONTEXT.md`. Decision records: `docs/adr/0001`–`0003`.

**Scope and distribution**
- A general tool for lecturers, built for the Observability module first; nothing module-specific in the tool.
- Questions and categories only, no quizzes (ADR 0002). Moodle XML, not the web service API (ADR 0001).
- Python. Used via Docker image or by cloning the repo; no PyPI package for now.
- Public GitHub repo, MIT licence, image on GitHub's container registry. Name: `moodle-qc`.
- The tool lives in its own repo; each module keeps its question collection in its own repo.

**Question collection**
- One question per Markdown file; `generate` takes files or folders and writes one import file.
- Collection config `moodle-qc.yaml` at the collection root: defaults (feedback texts, penalty, points, tags, code `line-height`, root category, allowed question types, per-type defaults such as scoring method and judgement labels). Question sources override any value; tags are combined. CLI flags for one-off overrides.
- Categories = folder path relative to the collection root (found by searching upwards for the config), optionally below a root category. Folder → category name: `_` becomes a space, the first letter of each word is capitalised, nothing else changes (dashes untouched). Renaming a folder creates a new category on the next import.
- Question ID = derived from the source path (or explicit `id:`), written to `idnumber`.
- Images: next to the question source, relative paths, embedded on generate, written back on extract.
- German only for now; `lang: de` in each file keeps a second language possible.

**Question source format** (ADR 0003)
- YAML front matter + Markdown body; Markdown turned into HTML, raw HTML allowed as fallback.
- Question name: front matter `name:` → first `# heading` → file name. The first heading is never question text.
- Fixed sections: `## Answers`, `## Solution` (→ Moodle general feedback; exam quizzes hide it via review options), `## Notes` (git only, never generated).
- Choice questions (`multichoice`, `sc`, `kprime`, `mtf`): task list under `## Answers`, `[x]` = correct/true, per-answer feedback as indented `>` quote. Checks: one `[x]` for `sc`, four answers for `kprime`.
- `multichoice` radio buttons vs checkboxes: front matter `multiple: true|false`; if missing, one `[x]` = radio buttons, several = checkboxes. (`multiple: true` with one `[x]` hides how many answers are correct.)
- Multiple-answer `multichoice`: correct answers share 100 %, wrong ones deduct the same share; per-answer override `{50%}`.
- `ddwtos`: inline gaps `[[word|group]]` (also inside code blocks), distractors per gap group in the front matter; the converter numbers gaps and groups. No group = one shared group. Words are used once by default; a gap group can allow reuse in the front matter (`reusable: [group]` → Moodle `<infinite/>`).

**Commands**
- `generate` (files/folders → import file; validates first), `extract` (Moodle export → question sources), `check` (validation only, for CI), `preview` (local HTML rendering, roughly Moodle-like).
- No git integration for "only what changed": select files/folders explicitly.

**Extract**
- Question ID already in the collection → overwrite that file where it is (refuse if it has uncommitted changes). New questions → folder from the category (spaces → `_`).
- Questions without `idnumber` get an ID from category + name, used as file name and written to the front matter.
- Unsupported question types become raw question sources (original XML kept, generated back unchanged).
- Moodle HTML is converted to Markdown only where converting back gives exactly the same result; otherwise it stays raw HTML.

**Quality**
- Round trip is a promise for supported types: extract(generate(x)) = x, and generate(extract(y)) has the same content as y (Moodle formatting like `1.0000000` ignored). The reference files in `tests/fixtures/moodle/` are the test cases.

**First version: question types**
`multichoice`, `sc`, `kprime`, `mtf`, `ddwtos`; everything else as raw question sources. `gapselect` next, `ddimageortext` (SVG → PNG + drop zones) later.
