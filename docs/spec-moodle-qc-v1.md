# Spec: `moodle-qc` – first version

Status: ready-for-agent · Date: 2026-11-13
Terms follow `CONTEXT.md`. Decisions recorded in `docs/adr/0001`–`0003`. Format facts: `docs/moodle-format-notes.md`. Reference files in `tests/fixtures/moodle/`: `moodle-xml-reference.xml`, `sample-ddwtos.xml`, `sample-ddwtos-export.xml`, `sample-ddimageortext.xml`.

## Problem Statement

Lecturers who write Moodle questions have to do it in Moodle's question editor, which is slow, click-heavy and hard to review. Questions with code (PromQL, YAML) are especially painful: formatting gets lost, gap questions need hand-numbered `[[1]]` markers kept in sync with a separate list of words, and there is no way to see what changed between two versions of a question. Two lecturers sharing a module can't review each other's questions before an exam, can't reuse questions across semesters in a controlled way, and edits made directly in Moodle are invisible to everyone else. Moodle offers no API to create or edit questions, and lecturers have no admin rights to install plugins that would.

## Solution

A command-line tool, the **question converter** `moodle-qc`, that lets lecturers keep their questions as plain Markdown files in git – a **question collection** – and turn them into a Moodle XML **import file** with one command (**generate**). The import file is uploaded through Moodle's normal question bank import. Folders become **categories**, so a whole semester's question bank is created in one import. The reverse direction (**extract**) turns a Moodle export back into question sources, so existing question banks can be moved into git and edits made in Moodle can be brought back. A `check` command validates a collection (also in CI) and `preview` renders questions locally as HTML, so questions can be reviewed without importing them.

The first version supports the question types `multichoice`, `sc`, `kprime`, `mtf` and `ddwtos`. Questions of any other type are kept as **raw question sources** so nothing is lost.

## User Stories

### Writing questions

1. As a lecturer, I want to write each question as a Markdown file with YAML front matter, so that I can edit questions in my usual editor and review them in git.
2. As a lecturer, I want to write question text in Markdown (code, bold, lists, code blocks), so that I don't have to write HTML by hand.
3. As a lecturer, I want to fall back to raw HTML inside the Markdown, so that I can still use formatting Markdown can't express.
4. As a lecturer, I want code blocks to be rendered in Moodle with a consistent monospace style and line height, so that code in exams is readable.
5. As a lecturer, I want `<` and `&` inside code to be escaped automatically, so that PromQL like `rate(x[5m]) < 0.1` doesn't break the question.
6. As a lecturer, I want to give a question its name in the front matter, so that the name in the Moodle question bank is exactly what I chose.
7. As a lecturer, I want the first `# heading` to be used as the question name when the front matter has none, so that I don't have to write the name twice.
8. As a lecturer, I want the file name to be used as the question name when there is neither, so that every question has a name.
9. As a lecturer, I want the first `# heading` never to appear in the question text, so that I can give files a readable title for GitHub without students seeing it.
10. As a lecturer, I want to write the grading information under `## Solution`, so that it ends up in Moodle's general feedback where graders can see it.
11. As a lecturer, I want to write private remarks under `## Notes`, so that ideas, sources and known weaknesses stay in git and never reach Moodle.
12. As a lecturer, I want to write the answers of choice questions as a Markdown task list under `## Answers`, so that right and wrong answers are visible at a glance.
13. As a lecturer, I want to add feedback to a single answer as an indented quote, so that students who chose it learn why it is wrong.
14. As a lecturer, I want `[x]` to mean "correct" for `multichoice` and `sc` and "true" for `kprime` and `mtf`, so that I use one notation for all choice questions.
15. As a lecturer, I want `multichoice` to use radio buttons when exactly one answer is marked and checkboxes when several are, so that I rarely need to set this explicitly.
16. As a lecturer, I want to force checkboxes with `multiple: true` even when only one answer is correct, so that students can't infer how many answers are correct.
17. As a lecturer, I want correct answers of a multiple-answer `multichoice` to share 100 % and wrong answers to deduct the same share, so that ticking everything scores zero.
18. As a lecturer, I want to override the percentage of a single answer (`{50%}`), so that I can weight answers differently when needed.
19. As a lecturer, I want to write `ddwtos` gaps directly in the text as `[[word|group]]`, so that I see which word belongs in which gap without numbering anything.
20. As a lecturer, I want gaps to work inside code blocks, so that I can ask students to complete PromQL or YAML.
21. As a lecturer, I want to list distractors per gap group in the front matter, so that each kind of gap gets its own plausible wrong words.
22. As a lecturer, I want gaps without a group to share one group, so that simple gap questions need no group names.
23. As a lecturer, I want the same word to be allowed in two different gap groups, so that a word like `count` can be correct in one place and a distractor in another.
24. As a lecturer, I want to allow words of a specific gap group to be reused (`reusable: [group]`), so that one word can fill several gaps when that makes sense.
25. As a lecturer, I want to embed images with normal Markdown image syntax, relative to the question source, so that questions can show dashboards or traces.
26. As a lecturer, I want images shared by several questions to work via relative paths into other folders, so that I don't duplicate files.
27. As a lecturer, I want to set points, penalty, tags, scoring method and other settings per question in the front matter, so that special questions can differ from the defaults.
28. As a lecturer, I want to set a question ID explicitly in the front matter, so that a question keeps its identity when I move or rename its file.
29. As a lecturer, I want every question source to carry `lang: de`, so that a second language can be added later without changing the format.

### Question collection and config

30. As a lecturer, I want to keep a `moodle-qc.yaml` collection config at the root of my question collection, so that defaults are written once instead of in every file.
31. As a lecturer, I want to set default feedback texts, points, penalty and tags in the collection config, so that all questions behave consistently.
32. As a lecturer, I want to set per-question-type defaults in the collection config (e.g. `kprime` scoring method and judgement labels "richtig"/"falsch"), so that plugin types work without repeating their settings.
33. As a lecturer, I want built-in defaults for anything the config leaves out, so that a minimal config works.
34. As a lecturer, I want tags from the collection config to be combined with tags from the question source, so that a semester tag like `26hs` is never lost when a question adds its own tags.
35. As a lecturer, I want to list the question types allowed on my Moodle in the collection config, so that the converter rejects a `kprime` question for a Moodle without the ETH plugins.
36. As a lecturer, I want to set the code block line height in the collection config, so that it matches how my questions look best in Moodle.
37. As a lecturer, I want to set a root category in the config and override it with a command-line flag, so that I can import into a test category (`import-test`) without touching the config.
38. As a lecturer, I want command-line flags to override config values for one run, so that one-off imports don't require config edits.

### Categories and question IDs

39. As a lecturer, I want each folder in the collection to become a Moodle category, so that my folder structure is my question bank structure.
40. As a lecturer, I want categories to be computed relative to the collection root, so that a question lands in the same category whether I generate one file, one folder or the whole collection.
41. As a lecturer, I want the converter to find the collection root by searching upwards for `moodle-qc.yaml`, so that I can run it from any subfolder.
42. As a lecturer, I want folder names turned into category names by replacing `_` with a space and capitalising the first letter of each word, without changing any other letter or dashes, so that `SW09_alerting` becomes "SW09 Alerting" and acronyms stay intact.
43. As a lecturer, I want spaces in folder names to be allowed, so that I can name folders exactly as the category should read.
44. As a lecturer, I want nested folders to become nested categories, so that weeks can contain topics.
45. As a lecturer, I want each question to get a question ID derived from its path, written to Moodle's `idnumber`, so that questions in Moodle can be traced back to their source.

### Generate

46. As a lecturer, I want to run `moodle-qc generate` on a file, several files or a folder tree, so that I can create import files for exactly the questions I need.
47. As a lecturer, I want all selected questions in one import file, so that one Moodle import brings in everything.
48. As a lecturer, I want the import file to contain category entries without `$course$/` and `top/` prefixes, so that categories are created in whichever question bank I import into, on Moodle 4.x and 5.x.
49. As a lecturer, I want text written as CDATA rather than XML-escaped, so that the import file is readable and matches how Moodle exports.
50. As a lecturer, I want images embedded into the import file automatically, so that I upload a single file.
51. As a lecturer, I want generate to validate everything first and write nothing if there are errors, so that I never import a half-broken file.
52. As a lecturer, I want raw question sources to be written back unchanged, so that questions of unsupported types survive the trip through git.
53. As a lecturer, I want `kprime`, `mtf` and `sc` questions written in the exact structure the ETH plugins expect, so that they import without errors.

### Extract

54. As a lecturer, I want to run `moodle-qc extract` on a Moodle export, so that my existing questions become question sources in my collection.
55. As a lecturer, I want an extracted question whose question ID already exists to overwrite that question source where it is, so that edits made in Moodle show up as a git diff.
56. As a lecturer, I want extract to refuse to overwrite a question source with uncommitted changes, so that I never lose unsaved work.
57. As a lecturer, I want new questions to be placed in a folder derived from their category (spaces become `_`), so that extracted questions are organised like the question bank.
58. As a lecturer, I want questions without an `idnumber` to get a question ID from their category and name, used as file name and written to the front matter, so that they behave like any other question source afterwards.
59. As a lecturer, I want questions of unsupported types to become raw question sources, so that the whole question bank can live in git.
60. As a lecturer, I want Moodle HTML converted to Markdown only where converting back gives exactly the same HTML, and kept as raw HTML otherwise, so that extract never changes a question silently.
61. As a lecturer, I want a code block with the configured style to become a normal fenced code block, so that typical questions extract to clean Markdown.
62. As a lecturer, I want embedded images to be written as files next to the extracted question source, so that images are versioned with their question.
63. As a lecturer, I want extract to ignore Moodle's formatting noise (`1.0000000`, empty `idnumber`, full category paths with parent entries), so that a round trip produces no spurious diffs.

### Check and preview

64. As a lecturer, I want `moodle-qc check` to validate a collection without writing anything, so that I can run it before committing or in CI.
65. As a lecturer, I want check to reject an `sc` question with more or less than one `[x]`, so that broken single-choice questions are caught.
66. As a lecturer, I want check to reject a `kprime` question without exactly four answers, so that the plugin import doesn't fail.
67. As a lecturer, I want check to reject a gap group without a distractor and duplicate words within a gap group, so that gap questions stay meaningful.
68. As a lecturer, I want check to report missing images, duplicate question IDs and question types not allowed by the config, so that the import doesn't fail in Moodle.
69. As a lecturer, I want every problem reported with the file and a clear description, so that I can fix it without guessing.
70. As a lecturer, I want check to exit with a non-zero code on problems, so that CI pipelines fail.
71. As a lecturer, I want `moodle-qc preview` to render questions as a local HTML page, so that I can review questions without importing them into Moodle.
72. As a co-teacher, I want to review a colleague's questions as a pull request with preview output, so that exam questions are checked by two people.

### Using the tool

73. As a lecturer without a Python setup, I want to run the converter through a Docker image, so that installation is one command.
74. As a lecturer who prefers source, I want to clone the repo and run it directly, so that I can use or adapt it.
75. As a lecturer at another school, I want the tool to be public and MIT-licensed, so that I can use it with my own Moodle.
76. As a maintainer, I want the tool to contain nothing specific to one module, so that it stays usable for every lecturer.

## Implementation Decisions

- **Language and distribution:** Python. Distributed as a Docker image on GitHub's container registry and as a cloneable public GitHub repo under the MIT licence. No PyPI package for now. Command name `moodle-qc`.
- **Architecture:** a neutral in-memory **question model** sits between two representations. Question sources are parsed into it, Moodle XML is read into it, and both are written from it. Commands orchestrate; they contain no format logic.
- **Modules (each with a small public interface, each unit-tested):**
  - **Collection** – finds the collection root by searching upwards for `moodle-qc.yaml`, loads and validates the collection config, resolves which question sources a selection (files/folders) includes, and merges defaults: built-in → collection config → per-question-type section → front matter → command-line flags. Tags are combined at every level; all other values override.
  - **Category naming** – pure functions: folder path relative to the collection root (plus optional root category) → category path, using the agreed rule (`_` → space, capitalise first letter of each word, change nothing else); and category path → folder path for new extracted questions (spaces → `_`).
  - **Question ID** – pure functions: derive a question ID from a source path; derive one from category + question name for extracted questions without `idnumber`; slug rules shared by both.
  - **Question source parser/writer** – splits YAML front matter and Markdown body; applies the question-name rule (front matter → first heading → file name); removes the first heading from the question text; splits the fixed sections `## Answers`, `## Solution`, `## Notes` (English keywords regardless of question language); writes question sources back in a canonical layout so extract output is stable.
  - **Markdown ↔ HTML** – Markdown → HTML with code blocks rendered as `<pre>` with the configured style and `<`/`&` escaped inside code; gap markers left untouched. HTML → Markdown converts only when converting back yields identical HTML, otherwise keeps raw HTML. Image references are collected for embedding.
  - **Question type handlers** – one per type: `multichoice`, `sc`, `kprime`, `mtf`, `ddwtos`, `raw`. Each handler offers the same interface: validate a question (returning problems), convert question model → Moodle XML question element, and Moodle XML question element → question model. Type rules live here: `[x]` meaning, `multiple` inference, fraction calculation with deductions and `{n%}` overrides, `sc` correct row, `kprime` four rows, `kprime`/`mtf` weights and judgement labels, scoring method values per plugin, `ddwtos` gap numbering (correct words first, then distractors), gap-group numbering, `reusable` → `<infinite/>`. The `raw` handler stores and returns the original XML unchanged.
  - **Moodle XML reader/writer** – writes the import file: category entries before their questions (paths without `$course$/` and `top/`), common question header, CDATA for text (splitting `]]>` if present), embedded files as base64 with `@@PLUGINFILE@@` references. Reads exports: tolerates Moodle's formatting (numeric formats, empty fields, full category paths, parent category entries, CDATA vs escaping).
  - **Commands** – `generate` (validate everything, then write one import file; no output on errors), `extract` (write question sources into a collection; refuse to overwrite files with uncommitted git changes), `check` (validate only; non-zero exit code on problems; each problem names file and issue), `preview` (render selected questions to a local HTML page, roughly Moodle-like).
- **Question source format** (ADR 0003): YAML front matter + Markdown body; answers as task list with indented `>` feedback; inline gaps `[[word|group]]`; distractors and `reusable` per gap group in the front matter; `multiple:` for `multichoice`; optional `id:`, `name:`, `category:`, points, penalty, tags, `lang`.
- **Import file conventions:** CDATA instead of XML escaping; code block `line-height` from config (agreed value 1.2); category entries apply to all following questions; the import option "Get category from file" is required and documented.
- **Validation rules** (shared by `generate` and `check`): exactly one `[x]` for `sc`; four answers for `kprime`; at least one `[x]` for `multichoice`; each gap group has a distractor; no duplicate word within a gap group; every referenced image exists; question IDs unique within the selection; question type allowed by the collection config; front matter keys known.
- **First version question types:** `multichoice`, `sc`, `kprime`, `mtf`, `ddwtos`, plus `raw` for everything else.

## Testing Decisions

- **Good tests check external behaviour only:** what goes in and what comes out of a module's public interface or a command. They don't inspect internal state, private helpers or call sequences, so internals can be refactored freely.
- **Two levels of tests:**
  - **Unit tests per module**, at each module's public interface: category naming (e.g. `SW09_alerting` → "SW09 Alerting", `otel_collector` → "Otel Collector", `slo-und-sli` → "Slo-und-sli", `Alerting Basics` unchanged, nested folders, root category, reverse mapping), question ID derivation, config merging (override order, tags combined), question source parsing (name rule, first heading removed, section splitting), Markdown ↔ HTML (code escaping, gaps untouched, exact-round-trip fallback to raw HTML), and every question type handler (validation rules, question model ↔ Moodle XML element for typical and edge cases such as one-correct `multichoice` with `multiple: true`, `{50%}` overrides, a word in two gap groups, reusable groups).
  - **Integration tests on the command level**: commands run in-process on real folders in a temporary directory.
    - `generate`: small collections → import file compared to expected Moodle XML.
    - `extract`: real Moodle exports → expected question sources (paths, front matter, Markdown), including overwrite-in-place, new-question placement, ID creation and raw question sources.
    - Round trip for every example question of each type: generate → extract gives back the original question sources; extract → generate gives Moodle XML with the same content.
    - `check`: broken collections → non-zero exit code and messages naming file and problem.
    - `preview`: smoke test (HTML file exists, contains question names).
- **Content-based XML comparison:** a test helper compares Moodle XML by content, ignoring numeric formatting (`1` vs `1.0000000`), whitespace, CDATA vs escaping, empty `idnumber` and parent category entries. On mismatch it reports the exact place (question ID, element, expected vs actual).
- **Fixtures / prior art:** there is no existing codebase. The reference files in `tests/fixtures/moodle/` are the first fixtures: `moodle-xml-reference.xml` and its verified re-export (`multichoice`, `kprime`, `mtf`, `sc`, categories), `sample-ddwtos.xml` and `sample-ddwtos-export.xml` (`ddwtos` with gap groups and code blocks; the export also shows edits made in Moodle), `sample-ddimageortext.xml` (a type not supported in v1 → raw question source round trip).

## Out of Scope

- Creating or configuring quiz activities (ADR 0002).
- Uploading via a Moodle web service or any other automation of the import (ADR 0001).
- Updating existing questions in Moodle in place; imports always add new questions.
- Question types other than `multichoice`, `sc`, `kprime`, `mtf`, `ddwtos` as structured formats (they are kept as raw question sources). `gapselect` is planned next, `ddimageortext` with SVG → PNG drop zones later.
- A PyPI package; a web interface.
- Git integration for "only changed questions" (e.g. `--changed-since`); lecturers select files or folders.
- Multiple languages per question (only the `lang` field is reserved).
- Readable category titles from per-folder metadata files.
- Pixel-accurate preview of Moodle's rendering.

## Further Notes

- Target instance used for verification: `moodle.assessment.fhnw.ch` (lecturer rights only). Available question types there are listed in `docs/moodle-format-notes.md`.
- Moodle import silently drops an `idnumber` that already exists in the target category and creates the question anyway, so importing the same question twice gives duplicates; documentation should explain this and the recommended workflow (import into a fresh or test category, then assemble quizzes).
- The Solution is visible to students unless the quiz's review options hide general feedback; documentation should tell lecturers to switch it off for exams.
- The ETH plugins (`kprime`, `mtf`, `sc`) ignore combined feedback and hints on import; the converter should not emit them for these types, or `check` should warn if a question source sets them.
- Renaming a folder creates a new category on the next import, since Moodle matches categories by exact name.
