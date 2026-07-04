from mathkit.strings import slugify


def test_slugify_basic():
    assert slugify("Hello World!") == "hello-world"


def test_slugify_lowercase():
    assert slugify("Python Is Fun") == "python-is-fun"


def test_slugify_strips_edges():
    assert slugify("  spaced  out  ") == "spaced-out"
