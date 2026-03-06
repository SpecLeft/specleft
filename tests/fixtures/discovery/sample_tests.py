"""Sample tests for discovery validation fixtures."""


def test_add():
    assert (1 + 1) == 2


def test_parametrized():
    assert 2 > 1


class TestMath:
    def test_subtract(self):
        assert 3 - 1 == 2
