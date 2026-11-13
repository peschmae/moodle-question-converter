from moodle_qc.xmlnode import Node, serialize


def test_text_with_markup_is_written_as_cdata() -> None:
    assert serialize(Node("text", text="<p>a & b</p>")) == "<text><![CDATA[<p>a & b</p>]]></text>\n"


def test_plain_text_is_written_as_is() -> None:
    assert serialize(Node("text", text="SW09 – Alerting")) == "<text>SW09 – Alerting</text>\n"


def test_cdata_end_marker_inside_text_is_split() -> None:
    assert serialize(Node("text", text="a]]>b")) == "<text><![CDATA[a]]]]><![CDATA[>b]]></text>\n"


def test_empty_text_and_flag_elements() -> None:
    node = Node("question")
    node.add("idnumber", "")
    node.add("shownumcorrect")

    assert (
        serialize(node) == "<question>\n  <idnumber></idnumber>\n  <shownumcorrect/>\n</question>\n"
    )


def test_attributes_are_escaped_and_raw_nodes_written_verbatim() -> None:
    node = Node("quiz")
    node.add("answer", "x", fraction="50", format='a"b')
    node.children.append(Node("question", raw='<question type="ddimageortext"/>'))

    assert serialize(node) == (
        '<quiz>\n  <answer fraction="50" format=\'a"b\'>x</answer>\n'
        '  <question type="ddimageortext"/>\n</quiz>\n'
    )
