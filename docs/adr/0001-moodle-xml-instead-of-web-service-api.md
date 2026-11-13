# Generate Moodle XML instead of using the web service API

Moodle core has no web service functions for creating or editing questions, and adding them needs a local PHP plugin installed by each site's admins, which lecturers can't do. The question converter therefore writes Moodle XML files that lecturers import through the question bank UI. The few community plugins that expose question import as a web service accept the same Moodle XML, so an automated upload can be added later without changing the format.

## Consequences

An import always creates new questions; it never updates existing ones (a duplicate `idnumber` in the target category is silently dropped). Changing a question that is already in use means importing it again and replacing it in the quiz.
