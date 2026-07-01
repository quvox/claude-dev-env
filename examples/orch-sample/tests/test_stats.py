from mathkit.stats import mean, median


def test_mean_basic():
    assert mean([1, 2, 3]) == 2


def test_mean_single():
    assert mean([5]) == 5


def test_median_odd():
    assert median([1, 2, 3]) == 2


def test_median_even():
    assert median([1, 2, 3, 4]) == 2.5


def test_median_unsorted():
    assert median([3, 1, 2]) == 2
