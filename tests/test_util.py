from gt.util import strip_markdown


def test_strip_markdown_basic():
    md = "# Title\nSome `code` and a [link](http://ex).\n> quote\n````\nblock\n````"
    out = strip_markdown(md)
    assert "Title" in out
    assert "code" in out
    assert "link (http://ex)" in out
    assert "quote" in out
    assert "block" not in out  # code block removed

