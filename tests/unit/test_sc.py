from moodle_qc.collection import BUILTIN_DEFAULTS, BUILTIN_TYPE_DEFAULTS, merge_settings
from moodle_qc.qtypes.sc import SingleChoice
from moodle_qc.question import Question
from moodle_qc.source import Answer, SourceDocument


def sc_question(*correct: bool, **settings: object) -> Question:
    answers = [Answer(f"Antwort {i}", flag) for i, flag in enumerate(correct, 1)]
    return Question(
        qtype="sc",
        name="Q",
        question_id="q",
        category="",
        document=SourceDocument(answers=answers),
        settings=merge_settings(BUILTIN_DEFAULTS, BUILTIN_TYPE_DEFAULTS["sc"], settings),
        origin="q.md",
    )


def test_exactly_one_correct_answer_is_valid() -> None:
    assert SingleChoice().validate(sc_question(False, True, False)) == []


def test_no_or_several_correct_answers_are_reported() -> None:
    assert SingleChoice().validate(sc_question(False, False)) == [
        "needs exactly one correct answer ([x]), has 0"
    ]
    assert SingleChoice().validate(sc_question(True, True)) == [
        "needs exactly one correct answer ([x]), has 2"
    ]


def test_unknown_scoring_method_is_reported() -> None:
    assert SingleChoice().validate(sc_question(True, scoring="kprime")) == [
        "scoring must be one of sconezero, aprime, subpoints"
    ]
