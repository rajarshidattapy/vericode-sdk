from vericode import verify


def test_valid():
    assert verify("x = 1").ok


def test_invalid():
    r = verify("def f(:")
    assert not r.ok and r.issues
