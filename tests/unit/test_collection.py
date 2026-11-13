from pathlib import Path

import pytest

from moodle_qc.collection import Collection, merge_settings
from moodle_qc.errors import UserError


def test_later_layers_override_and_tags_are_combined() -> None:
    merged = merge_settings(
        {
            "points": 1,
            "tags": ["26hs"],
            "feedback": {"correct": "Richtig.", "incorrect": "Falsch."},
        },
        {"points": 2, "tags": ["probe", "26hs"], "feedback": {"correct": "Gut."}},
    )

    assert merged == {
        "points": 2,
        "tags": ["26hs", "probe"],
        "feedback": {"correct": "Gut.", "incorrect": "Falsch."},
    }


def test_merge_order_builtin_then_config_then_type_section_then_front_matter(
    tmp_path: Path,
) -> None:
    (tmp_path / "moodle-qc.yaml").write_text(
        "defaults:\n  points: 2\n  penalty: 0\n  tags: [26hs]\n"
        "types:\n  kprime:\n    points: 3\n    labels: [richtig, falsch]\n",
        encoding="utf-8",
    )
    collection = Collection.find(tmp_path)

    settings = collection.settings_for("kprime", {"penalty": 0.5, "tags": ["probe"]})

    assert settings["points"] == 3
    assert settings["penalty"] == 0.5
    assert settings["tags"] == ["26hs", "probe"]
    assert settings["labels"] == ["richtig", "falsch"]
    assert settings["scoring"] == "kprime"
    assert collection.settings_for("sc", {})["points"] == 2


def test_root_category_flag_overrides_the_config(tmp_path: Path) -> None:
    (tmp_path / "moodle-qc.yaml").write_text("root_category: 26hs\n", encoding="utf-8")
    collection = Collection.find(tmp_path)

    assert collection.root_category == "26hs"
    collection.root_category_override = "import-test"
    assert collection.root_category == "import-test"


def test_unknown_config_setting_is_an_error(tmp_path: Path) -> None:
    (tmp_path / "moodle-qc.yaml").write_text("root_categroy: x\n", encoding="utf-8")

    with pytest.raises(UserError, match="unknown setting"):
        Collection.find(tmp_path)


def test_code_line_height_sets_the_code_block_style(tmp_path: Path) -> None:
    (tmp_path / "moodle-qc.yaml").write_text("code_line_height: 2.2\n", encoding="utf-8")

    assert Collection.find(tmp_path).pre_style == "font-family: monospace; line-height: 2.2;"
