# Moodle question converter (`moodle-qc`)

A general tool for lecturers that turns question sources kept in git into Moodle XML for import into a Moodle question bank, and turns Moodle exports back into question sources. It handles questions and categories only; quizzes are assembled in Moodle.

## Language

### Tool and files

**Question converter**:
The tool as a whole, named `moodle-qc`.
_Avoid_: generator (as a name for the tool), compiler, exporter

**Question collection**:
A folder tree of question sources whose root folder holds the collection config, typically living in a module's own repo.
_Avoid_: question bank (that is the Moodle side), quiz, project

**Collection config**:
The settings file (`moodle-qc.yaml`) at the root of a question collection holding defaults for all its question sources, including per question type; a question source may override any value, except that tags are combined.
_Avoid_: settings, profile

**Question source**:
One authored Markdown file with YAML front matter describing exactly one Moodle question. Only `.md` files are question sources; other files next to them are assets such as images.
_Avoid_: question file, item, template

**Raw question source**:
A question source of a question type the converter has no format for; it carries the original Moodle XML unchanged and is written back as is.
_Avoid_: unsupported question, passthrough

**Generate**:
Turning a selection of question sources (files or folders inside one question collection) into a single import file.
_Avoid_: build, compile, convert (as the verb for this direction)

**Extract**:
Turning a Moodle export into question sources inside a question collection, overwriting sources with the same question ID.
_Avoid_: import (that is Moodle's import), reverse, decompile, convert back

**Import file**:
The Moodle XML file produced by generating, ready for Question bank → Import.
_Avoid_: export, quiz file, output

### Moodle side

**Category**:
A Moodle question bank category; derived from the folder a question source sits in, relative to the root of its question collection and optionally below a root category. It does not depend on which part of the collection is generated.
_Avoid_: week, topic, folder (when meaning the Moodle side)

**Root category**:
An optional category prefix under which all generated categories are placed (e.g. `import-test`).
_Avoid_: base category, parent

**Question type**:
Moodle's internal type name of a question (`multichoice`, `ddwtos`, `kprime`, …), as used in `<question type="…">`.
_Avoid_: format, kind

### Parts of a question

**Question ID**:
The stable identifier of a question, derived from its source path unless set explicitly; carried in Moodle's `idnumber` field.
_Avoid_: idnumber (Moodle's field name), key, slug

**Question name**:
The title of a question as shown in the Moodle question bank; taken from the front matter, else the first heading, else the file name. The first heading is never part of the question text.
_Avoid_: title, label

**Question text**:
What students read: the Markdown body between the first heading and the first fixed section.
_Avoid_: body, prompt, stem

**Solution**:
The grading information for lecturers (`## Solution`); goes into Moodle's general feedback, which exam quizzes hide from students through their review options.
_Avoid_: general feedback (Moodle's field name), answer key, Lösung

**Notes**:
Private remarks about a question (`## Notes`) that stay in git and are never generated.
_Avoid_: comments, remarks

**Answer**:
One statement of a choice question (`multichoice`, `sc`, `kprime`, `mtf`), marked right or wrong, with optional feedback.
_Avoid_: option, choice, row, statement (when meaning the data item)

**Gap**:
A place in the question text of a `ddwtos` question where a word is dropped; written with its correct word and gap group.
_Avoid_: blank, drop zone (that is `ddimageortext`), placeholder

**Gap group**:
A named set of words that fit the same kind of gap; a gap only accepts words from its own group.
_Avoid_: group number, category

**Distractor**:
A wrong word offered in a gap group, or a wrong label in `ddimageortext`.
_Avoid_: decoy, wrong answer
