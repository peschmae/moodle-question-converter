import re
from pathlib import Path

from tests.support.collections import empty_collection, generate

SC = "---\ntype: sc\n{extra}---\n# {name}\n\nText\n\n## Answers\n- [x] a\n- [ ] b\n"


def write(collection: Path, relative: str, extra: str = "") -> None:
    path = collection / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(SC.format(extra=extra, name=path.stem), encoding="utf-8")


def category_entries(xml: str) -> list[str]:
    return re.findall(r"<category>\s*<text>([^<]*)</text>", xml)


def collection_with_two_weeks(tmp_path: Path) -> Path:
    collection = empty_collection(tmp_path / "questions", "root_category: 26hs\n")
    write(collection, "SW09_alerting/burn_rate/fast.md")
    write(collection, "SW09_alerting/latenz.md")
    write(collection, "SW10_dashboards/panels.md")
    return collection


def test_folders_become_nested_categories_below_the_root_category(tmp_path: Path) -> None:
    collection = collection_with_two_weeks(tmp_path)

    xml = generate([collection], tmp_path / "import.xml")

    assert category_entries(xml) == [
        "26hs/SW09 Alerting/Burn Rate",
        "26hs/SW09 Alerting",
        "26hs/SW10 Dashboards",
    ]


def test_generating_a_subfolder_keeps_the_same_categories(tmp_path: Path) -> None:
    collection = collection_with_two_weeks(tmp_path)

    xml = generate([collection / "SW09_alerting" / "burn_rate"], tmp_path / "import.xml")

    assert category_entries(xml) == ["26hs/SW09 Alerting/Burn Rate"]


def test_root_category_flag_and_front_matter_category(tmp_path: Path) -> None:
    collection = collection_with_two_weeks(tmp_path)
    write(collection, "SW10_dashboards/moved.md", extra="category: Sammlung/Diverses\n")

    xml = generate(
        [collection / "SW10_dashboards"], tmp_path / "import.xml", "--root-category", "import-test"
    )

    assert category_entries(xml) == ["Sammlung/Diverses", "import-test/SW10 Dashboards"]
