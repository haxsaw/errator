import traceback
import sys
import threading
from errator import *
from _errator import (_thread_fragments,)
from io import StringIO


def test01():
    """
    test01: Check string function of StoryFragment
    :return:
    """
    the_text = "some text"
    sf = NarrationFragment(the_text, test01)
    assert the_text in sf.tell(), "The text we supplied wasn't in the fragment's output"


def test02():
    """
    test02: Check that a callable gets invoked
    :return:
    """
    text = "callable text"

    def f(a1, kw1=""):
        return "f:{} {}".format(a1, kw1)

    sf = NarrationFragment(f, test02, "callable", kw1="text")
    assert text in sf.tell(), "The callable didn't manage to return the expected string"


def test03():
    """
    test03: Check that we push a fragment into our thread's list in a function
    :return:
    """
    reset_all_narrations()
    tname = threading.current_thread().name

    @narrate("Visiting inner")
    def inner(x, y):
        di = _thread_fragments[tname]
        assert len(di) == 1, "Expected 1 fragment, got {}".format(len(di))
        return True

    inner(1, 2)
    d = _thread_fragments[tname]
    assert len(d) == 0, "Expected 0 fragments, got {}".format(len(d))


def test04():
    """
    test04: Check that we push a fragment into our deque when we use a formatting function
    :return:
    """
    reset_all_narrations()
    tname = threading.current_thread().name

    @narrate(lambda x, y: "{}-{}".format(x, y))
    def f(x, y):
        di = _thread_fragments[tname]
        assert len(di) == 1, "expected 1 fragment, got {}".format(len(di))
        return True

    f(4, 5)
    d = _thread_fragments[tname]
    assert len(d) == 0, "Expected 0, fragments, got {}".format(len(d))


def test05():
    """
    test05: Check that we accumulate fragments in multiple errated function calls
    :return:
    """
    reset_all_narrations()
    tname = threading.current_thread().name

    @narrate("Calling nf1")
    def f1():
        di = _thread_fragments[tname]
        assert len(di) == 1, "expected 1 fragment, got {}".format(len(di))
        f2()
        assert len(di) == 1, "expected 1 fragment, got {}".format(len(di))

    @narrate("Calling nf2")
    def f2():
        di = _thread_fragments[tname]
        assert len(di) == 2, "expected 2 fragments, got {}".format(len(di))

    f1()
    d = _thread_fragments[tname]
    assert len(d) == 0, "expected 0 fragments, got {}".format(len(d))


def test06():
    """
    test06: Check that if we raise an exception, we keep the fragments
    :return:
    """
    reset_all_narrations()
    tname = threading.current_thread().name

    class T6Exception(Exception):
        pass

    extext = "We got's messed up!"

    @narrate("Buggered!")
    def broken(x, y):
        raise T6Exception(extext)

    try:
        broken(1, 2)
        assert False, "We should have encountered the exception our function raised"
    except T6Exception as e:
        assert extext in str(e)
        d = _thread_fragments[tname]
        assert len(d) == 1, "Expected 1 fragment, got {}".format(len(d))
        sf = d.pop()
        assert isinstance(sf, NarrationFragment)
        assert "Buggered!" in sf.tell()


def test07():
    """
    test07: Check that we work with methods too
    :return:
    """

    reset_all_narrations()
    tname = threading.current_thread().name

    class T07(object):
        @narrate("T7 narration")
        def f(self, x, y):
            di = _thread_fragments[tname]
            assert x == 4, "x is {}, not 4".format(x)
            assert y == 5, "y is {}".format(y)
            assert len(di) == 1, "Expected 1 fragment, got {}".format(len(di))

    t07 = T07()
    t07.f(4, 5)
    d = _thread_fragments[tname]
    assert len(d) == 0, "Expected 0 fragments, got {}".format(len(d))


def test08():
    """
    test08: Check that we promote any non-standard attributes on a callable to the wrapper
    :return:
    """
    reset_all_narrations()
    tname = threading.current_thread().name

    def deco(m):
        m.wibble = "Surprise!"
        return m

    @narrate("Trying to wibble")
    @deco
    def f():
        di = _thread_fragments[tname]
        assert len(di) == 1, "Expected 1 fragment, got {}".format(len(di))
        return

    @deco
    @narrate("Trying to wobble")
    def f1():
        di = _thread_fragments[tname]
        assert len(di) == 1, "Expected 1 fragment, to {}".format(len(di))
        return

    f()
    f1()
    d = _thread_fragments[tname]
    assert len(d) == 0, "Expected 0 fragments, got {}".format(len(d))
    assert hasattr(f, "wibble") and f.wibble == "Surprise!"
    assert hasattr(f1, "wibble") and f.wibble == "Surprise!"


def test09():
    """
    test09: Check that the context manager works properly
    :return:
    """
    reset_all_narrations()
    tname = threading.current_thread().name

    for i in range(5):
        with narrate_cm(lambda x: "iteration {}".format(x), i):
            di = _thread_fragments[tname]
            assert len(di) == 1, "Expected 1 fragment, got {}, i={}".format(len(di), i)
    d = _thread_fragments[tname]
    assert len(d) == 0, "Expected 0 fragments, got {}".format(len(d))


def test10():
    """
    test10: ensure we survive clearing narrations in the middle of one
    :return:
    """
    reset_all_narrations()
    tname = threading.current_thread().name

    @narrate("will it survive?")
    def f():
        di = _thread_fragments[tname]
        assert len(di) == 1, "Expected 1 fragment, got {}".format(len(di))
        reset_all_narrations()

    f()
    d = _thread_fragments[tname]
    assert len(d) == 0, "Expected 0 fragments, got {}".format(len(d))


def test11():
    """
    test11: ensure that copied fragments are retained
    """
    reset_all_narrations()

    @narrate("nf1")
    def f1():
        return f2()

    @narrate("nf2")
    def f2():
        return f3()

    @narrate("nf3")
    def f3():
        frags = copy_narration()
        reset_narration()
        return frags

    the_story = f1()
    for name in ("nf1", "nf2", "nf3"):
        assert any([name in nf.tell() for nf in the_story]), "didn't find function {}".format(name)


def test12():
    """
    test12: ensure we work with generators
    """
    reset_all_narrations()
    tname = threading.current_thread().name

    def g(x):
        with narrate_cm("only once"):
            di = _thread_fragments[tname]
            for i in range(x):
                assert len(di) == 1, "Expected 1 fragment, got {}".format(len(di))
                yield i

    for _ in g(5):
        pass

    d = _thread_fragments[tname]
    assert len(d) == 0, "Expected 0 fragments, got {}".format(len(d))


def test13():
    """
    test13: Check we do the right thing if we raise inside a context
    """
    reset_all_narrations()
    tname = threading.current_thread().name

    class Test13Exc(Exception):
        pass

    try:
        with narrate_cm("Blammo"):
            raise Test13Exc("oh dear")
        assert False, "we should have raised from our context block"
    except Test13Exc:
        d = _thread_fragments[tname]
        assert len(d) == 1, "Expecting 1 fragment, got {}".format(len(d))


def test14():
    """
    test14: check that only the frame where the exception occurred has exc details
    """
    reset_all_narrations()

    exc_text = "Here we go!"

    class T14Exc(Exception):
        pass

    @narrate("nf1")
    def f1():
        f2()

    @narrate("nf2")
    def f2():
        f3()

    @narrate("nf3")
    def f3():
        raise T14Exc(exc_text)

    try:
        f1()
        assert False, "We should have had an exception bubble up!"
    except T14Exc as e:
        assert str(e) == exc_text
        lines = get_narration()
        assert len(lines) == 3, "Expecting 3 lines, got {}".format(len(lines))
        assert exc_text not in lines[0]
        assert exc_text not in lines[1]
        assert exc_text in lines[2]


def test15():
    """
    test15: check that we can get only some of the narration text
    """
    reset_all_narrations()
    set_narration_options(auto_prune=False)

    @narrate("nf1")
    def f1():
        f2()

    @narrate("nf2")
    def f2():
        try:
            f3()
        except KeyError:
            lines = get_narration(from_here=True)
            assert len(lines) == 3
            reset_narration(from_here=True)

    @narrate("nf3")
    def f3():
        f4()

    @narrate("nf4")
    def f4():
        raise KeyError("wibble")

    f1()
    l2 = get_narration()
    assert len(l2) == 1, "Expected there to be one left, got {}".format(len(l2))
    set_narration_options(auto_prune=True)
    reset_all_narrations()


def test16():
    """
    test16: check that we behave right when we clear from the first fragment, auto_prune=True
    """
    reset_all_narrations()
    set_narration_options(auto_prune=True)

    @narrate("nf1")
    def f1():
        try:
            f2()
        except KeyError:
            reset_narration(from_here=True)
            lines = get_narration(from_here=True)
            assert len(lines) == 1, "Expected 1 line, got {}".format(len(lines))

    @narrate("nf2")
    def f2():
        f3()

    @narrate("nf3")
    def f3():
        raise KeyError("oopsie!")

    f1()
    l2 = get_narration()
    assert len(l2) == 0, "Expected 0 lines, got {}".format(len(l2))


def test17():
    """
    test17: check that we behave right when we clear from teh first fragment, auto_prune=False
    """
    reset_all_narrations()
    set_narration_options(auto_prune=False)

    @narrate("nf1")
    def f1():
        try:
            f2()
        except KeyError:
            reset_narration(from_here=True)
            lines = get_narration(from_here=True)
            assert len(lines) == 0, "Expected 0 lines, got {}".format(len(lines))

    @narrate("nf2")
    def f2():
        f3()

    @narrate("nf3")
    def f3():
        raise KeyError("youch!")

    lines = get_narration()
    assert len(lines) == 0, "Expected 0 lines, got {}".format(len(lines))
    set_narration_options(auto_prune=True)


def test18():
    """
    test18: check behavior clear from first fragment frame with contexts, auto_prune=True
    :return:
    """
    reset_all_narrations()
    set_narration_options(auto_prune=True)

    def f1():
        with narrate_cm("nf1 context"):
            try:
                f2()
            except KeyError:
                reset_narration(from_here=True)
                lines = get_narration(from_here=True)
                assert len(lines) == 1, "Expecting 1 lines, got {}".format(len(lines))

    @narrate("nf2")
    def f2():
        lines = get_narration()
        assert len(lines) == 2, "Expecting 2 lines, got {}".format(len(lines))
        with narrate_cm("nf3 context"):
            lines = get_narration()
            assert len(lines) == 3, "Expecting 3 lines, got {}".format(len(lines))
            raise KeyError

    f1()
    l2 = get_narration()
    assert len(l2) == 0, "Expecting no lines, got {}".format(len(l2))


def test18a():
    """
    test18a: check that clearing all narrations from the midst of a chain of calls doesn't break more global processing
    """
    reset_all_narrations()
    set_narration_options(auto_prune=True)

    @narrate("in f1")
    def f1():
        try:
            f2()
        except KeyError:
            lines = get_narration()
            assert 1 == len(lines), "got {}".format(lines)

    @narrate("in f2")
    def f2():
        try:
            f3()
        except KeyError:
            lines = get_narration()
            assert len(lines) == 3, "only {} lines".format(len(lines))
            reset_narration()

    @narrate("in f3")
    def f3():
        raise KeyError()

    f1()
    lines = get_narration()
    assert 0 == len(lines), "had {} lines".format(len(lines))


def test19():
    """
    test19: making sure the example in the quickstart works as it says!
    """
    reset_all_narrations()

    @narrate("I was just showing how it works")
    def f1():
        raise KeyError("when I blorked")

    try:
        f1()
    except KeyError:
        lines = get_narration()
        assert len(lines) == 1, "Expecting 1 line, got {}".format(len(lines))


def test20():
    """
    test20:
    :return: if auto_prune is off, check that 'clear to hear' removes the first tracked func
    """
    reset_all_narrations()
    set_narration_options(auto_prune=False)

    @narrate("nf1")
    def f1():
        f2()
        lines = get_narration()
        assert "nf1" not in lines

    def f2():
        try:
            f3()
        except KeyError:
            lines = get_narration(from_here=True)
            assert "nf1" in lines
            reset_narration(from_here=True)

    @narrate("nf3")
    def f3():
        raise KeyError("ouch")

    f1()
    set_narration_options(auto_prune=True)


def test21():
    """
    test21: Check that auto_prune==False still gets all clear when all funcs return
    """
    reset_all_narrations()
    set_narration_options(auto_prune=False)

    @narrate("nf1")
    def f1():
        f2()

    @narrate("nf2")
    def f2():
        raise KeyError("another mistake? I'm fired")

    try:
        f1()
    except KeyError:
        lines = get_narration()
        assert len(lines) == 2, "Expected 2 lines, got {}".format(len(lines))
        reset_narration(from_here=True)
        lines = get_narration()
        assert len(lines) == 0, "Expected no lines, got {}".format(len(lines))


def test22():
    """
    test22: ensure proper behavior when decorating a method on a class
    """
    reset_all_narrations()
    set_narration_options(auto_prune=True)

    class T22(object):
        @narrate(lambda _, x: "x is {}".format(x))
        def m(self, x):
            raise KeyError("die m die")

    o = T22()
    try:
        o.m(5)
    except KeyError:
        assert len(get_narration()) == 1, "We should have have a single narration line"


def test23():
    """
    test23: check that the 'check' option works for functions
    """
    reset_all_narrations()
    set_narration_options(auto_prune=False, check=True)

    @narrate(lambda v: "Entering nf1 with {}".format(v))
    def f1(x):
        return f2(x * 2)

    @narrate(lambda v: "Entering nf2 with {}".format(v))
    def f2(y):
        y += 2
        return y

    a = f1(5)
    assert a == 12, "Unexpected value for a: {}".format(a)
    frags = copy_narration()
    assert len(frags) == 2, "Expected 2 fragments, got {}".format(len(frags))
    tof0 = frags[0].text_or_func
    assert "nf1" in tof0, "the name 'nf1' wasn't in the fragment: {}".format(tof0)
    assert "5" in tof0, "the value 5 isn't in the fragment: {}".format(tof0)
    tof1 = frags[1].text_or_func
    assert "nf2" in tof1, "the name 'nf2' wasn't in the fragment: {}".format(tof1)
    assert "10" in tof1, "the value 10 wasn't int he fragment: {}".format(tof1)
    reset_all_narrations()
    set_narration_options(auto_prune=True, check=False)


def test24():
    """
    test24: check that the 'check' option works for context managers
    """
    reset_all_narrations()
    set_narration_options(auto_prune=False, check=True)

    initial = 5
    with narrate_cm(lambda v: "Exiting c1 with {}".format(v), initial):
        initial *= 2
        with narrate_cm(lambda w: "Exiting c2 with {}".format(w), initial):
            initial += 2

    assert initial == 12, "Unexpected value for initial: {}".format(initial)
    frags = copy_narration()
    assert len(frags) == 2, "Expected 2 fragments, got {}".format(len(frags))
    tof0 = frags[0].text_or_func
    assert "c1" in tof0, "the name c1 wasn't in the fragment: {}".format(tof0)
    assert "5" in tof0, "the value 5 wasn't in the fragment: {}".format(tof0)
    tof1 = frags[1].text_or_func
    assert "c2" in tof1, "the name c2 wasn't int he fragment: {}".format(tof1)
    assert "10" in tof1, "the value 10 wasn't in the fragment: {}".format(tof1)
    reset_all_narrations()
    set_narration_options(auto_prune=True, check=False)


def test25():
    """
    test25: check that we raise a fragment formatting exception for a bad callable
    """

    set_narration_options(check=True)
    reset_all_narrations()

    try:
        with narrate_cm(lambda arg: "oops"):
            pass
    except ErratorException:
        assert any(">>>>" in l for l in get_narration()), "no format failure messages"
    except Exception as e:
        assert False, f'{e} was raised'
    else:
        assert False, "We should have raised an exception"

    set_narration_options(check=False)


def test26():
    """
    test26: check that we get an ErratorException when we try to run a broken
    callable during an exception
    """
    set_narration_options(check=False)
    reset_all_narrations()

    try:
        with narrate_cm(lambda arg: "oops"):
            raise KeyError("not this one")
    except ErratorException:
        assert any(">>>>" in l for l in get_narration())
    except KeyError:
        assert False, "KeyError should not have come through"
    else:
        assert False, "We should have gotten an exception"


def test27():
    """
    test27: check that we get an ErratorException from the decorator for a broken callable with check
    """
    set_narration_options(check=True)
    reset_all_narrations()

    @narrate(lambda x, y: "again")
    def f():
        pass

    try:
        f()
    except ErratorException:
        assert any(">>>>" in l for l in get_narration())
    else:
        assert False, "we should have got an exception"
    set_narration_options(check=False)


def test28():
    """
    test28: check that we get an ErratorException from the decorator for a broken callable without check
    """
    set_narration_options(check=False)
    reset_all_narrations()

    @narrate(lambda missing: "oops")
    def f():
        raise KeyError("heads up")

    try:
        f()
    except ErratorException:
        assert any(">>>>" in l for l in get_narration())
    except KeyError:
        assert False, "We shouldn't have gotten a KeyError"
    else:
        assert False, "we should have gotten an exception"


def test29():
    """
    test29: check basic verbose=True narration fetching
    """
    set_narration_options(check=False, verbose=True)
    reset_all_narrations()

    @narrate("calling f")
    def f():
        raise Exception("oops")

    try:
        f()
        assert False, "there should have been an exception"
    except Exception as _:
        stuff = get_narration()
        assert stuff, "there should have been a narration"


# this next batch of functions is in support of testing
# verbose narration

@narrate(lambda x: "nf1 called with %s" % x)
def f1(arg):
    if arg == "nf1":
        raise Exception("in nf1")
    f2(arg)


@narrate(lambda x: "nf2 called with %s" % x)
def f2(arg):
    if arg == "nf2":
        raise Exception("in nf2")
    f3(arg)


def f3(arg):
    if arg == "nf3":
        raise Exception("in nf3")
    f4(arg)


@narrate(lambda x: "nf4 called with %s" % x)
def f4(arg):
    if arg == "nf4":
        raise Exception("in nf4")
    with narrate_cm(lambda x: "cm1 in nf4 with %s" % x, arg):
        if arg == "nf4@cm1":
            raise Exception("in nf4@cm1")
        f5(arg)


def f5(arg):
    if arg == "nf5":
        raise Exception("in nf5")
    with narrate_cm(lambda x: "cm2 in nf5 with %s" % x, arg) as cm2:
        if arg == "nf5@cm2":
            raise Exception("in nf5@cm2")
        f6(arg)


@narrate(lambda x: "nf6 called with %s" % x)
def f6(arg):
    if arg == "nf6":
        raise Exception("in nf6")


def count_nones(lines):
    return sum(1 for x in lines if "None" in x)


def test30():
    """
    test30: checking that basic processing doesn't crater on it's own
    """
    set_narration_options(check=False, verbose=True)
    reset_all_narrations()
    try:
        f1("nf6")
        assert False, "this should have raised"
    except Exception as e:
        assert "nf6" in str(e), "got an unexpected exception: %s" % str(e)
        lines = get_narration()
        assert len(lines) == 6, "unexpected number of strings: %s" % str(lines)


def test31():
    """
    test31: checking verbose output from raise in nf1
    """
    set_narration_options(check=False, verbose=True)
    reset_all_narrations()
    try:
        f1("nf1")
        assert False, "this should have raised"
    except Exception:
        lines = get_narration()
        assert len(lines) == 1, "got the following lines: %s" % str(lines)
        assert "nf1 called with nf1" in lines[0], "returned line contains: %s" % lines[0]
        assert "\n" in lines[0], "no newline in: %s" % lines[0]
        assert not count_nones(lines)


def test32():
    """
    test32: checking verbose output from raise in nf2
    """
    set_narration_options(check=False, verbose=True)
    reset_all_narrations()
    try:
        f1("nf2")
        assert False, "this should have raised"
    except Exception as e:
        assert "in nf2" in str(e)
        lines = get_narration()
        assert len(lines) == 2, "got the following lines: %s" % str(lines)
        assert "nf2 called with nf2" in lines[-1], "last line contains: %s" % lines[-1]
        assert "\n" in lines[0] and "\n" in lines[1], "newline missing: %s" % str(lines)
        assert not count_nones(lines)


def test33():
    """
    test33: checking verbose output from raise in nf3
    """
    set_narration_options(check=False, verbose=True)
    reset_all_narrations()
    try:
        f1("nf3")
        assert False, "this should have raised"
    except Exception as e:
        assert "in nf3" in str(e)
        lines = get_narration()
        assert len(lines) == 2, "got the following lines: %s" % str(lines)
        assert "nf2 called with nf3" in lines[-1], "last line contains: %s" % lines[-1]
        assert "\n" in lines[0] and "\n" in lines[1], "newline missing: %s" % str(lines)
        assert not count_nones(lines)


def test34():
    """
    test34: checking verbose output from raise in nf4
    """
    set_narration_options(check=False, verbose=True)
    reset_all_narrations()
    try:
        f1("nf4")
        assert False, "this should have raised"
    except Exception as e:
        assert "in nf4" in str(e), "wrong exception message: %s" % str(e)
        lines = get_narration()
        assert len(lines) == 3, "got the following lines: %s" % str(lines)
        assert "nf4 called with nf4" in lines[-1], "last line contains: %s" % lines[-1]
        assert 3 == sum(1 for x in lines if "\n" in x), "newline missing: %s" % str(lines)
        assert not count_nones(lines)


def test34cm1():
    """
    test34cm1: checking verbose output from a context manager in nf4
    """
    set_narration_options(check=False, verbose=True)
    reset_all_narrations()
    try:
        f1("nf4@cm1")
        assert False, "this should have raised"
    except Exception as e:
        assert "nf4@cm1" in str(e), "Unexpected text in exception: %s" % str(e)
        lines = get_narration()
        assert len(lines) == 4, "got the following lines: %s" % str(lines)
        assert "cm1 in nf4 with nf4@cm1" in lines[-1], "last line contains: %s" % lines[-1]
        assert 4 == sum(1 for x in lines if "\n" in x), "wrong number of newlines: %s" % str(lines)
        assert not count_nones(lines)


def test35():
    """
    test35: checking verbose output from nf5
    """
    set_narration_options(check=False, verbose=True)
    reset_all_narrations()
    try:
        f1("nf5")
        assert False, "this should have raised"
    except Exception as e:
        assert "in nf5" in str(e), "wrong exception value: %s" % str(e)
        lines = get_narration()
        assert len(lines) == 4, "got the following lines: %s" % str(lines)
        assert "cm1 in nf4 with nf5" in lines[-1], "last line contains: %s" % lines[-1]
        assert 4 == sum(1 for x in lines if "\n" in x), "wrong number of newlines: %s" % str(lines)
        assert not count_nones(lines)


def test35cm2():
    """
    test35cm2: checking verbose output from nf5 at cm2
    """
    set_narration_options(check=False, verbose=True)
    reset_all_narrations()
    try:
        f1("nf5@cm2")
        assert False, "this should have raised"
    except Exception as e:
        assert "in nf5@cm2" in str(e), "wrong exception value: %s" % str(e)
        lines = get_narration()
        assert len(lines) == 5, "got the following lines: %s" % str(lines)
        assert "cm2 in nf5 with nf5@cm2" in lines[-1], "last line contains: %s" % lines[-1]
        assert 5 == sum(1 for x in lines if "\n" in x), "wrong number of newlines: %s" % str(lines)
        assert not count_nones(lines)


def test36():
    """
    test36: checking verbose output from nf6
    """
    set_narration_options(check=False, verbose=True)
    reset_all_narrations()
    try:
        f1("nf6")
        assert False, "this should have raised"
    except Exception as e:
        assert "in nf6" in str(e), "wrong value in exception: %s" % str(e)
        lines = get_narration()
        assert len(lines) == 6, "wrong number of lines: %s" % len(lines)
        assert "nf6 called with nf6" in lines[-1], "last line is: %s" % lines[-1]
        assert 6 == sum(1 for x in lines if "\n" in x), "wrong number of newlines: %s" % str(lines)
        assert not count_nones(lines)


def test37():
    """
    test37: check that calling get_narration() more than once returns the same exception data
    each time
    """
    set_narration_options(check=False)
    reset_all_narrations()

    @narrate("Calling f")
    def f(i):
        raise Exception("test37")

    try:
        f(1)
        assert False, "should have raised"
    except Exception:
        l1 = get_narration()
        l2 = get_narration()
        assert len(l1) == 1, "got $%s lines" % len(l1)
        assert l1[0] == l2[0], "get_narration() returns different data in sequential calls"
        assert "test37" in l1[0], "narration doesn't appear to contain detail on exception"


to_find = "narrate_it"


def test38():
    """
    test38; check that extract_tb works properly
    """
    set_narration_options(check=False)
    reset_all_narrations()

    try:
        f1("nf6")
        assert False, "should have raised"
    except:
        et, ev, tb = sys.exc_info()
        tb_lines = extract_tb(tb)
        assert not any(True for x in tb_lines if to_find in x[2]), "found a narrate_it"


def test39():
    """
    test39: check that extract_stack works properly
    """
    set_narration_options(check=False)
    reset_all_narrations()

    @narrate("in f")
    def f():
        return extract_stack()

    stack_lines = f()
    assert not any(True for x in stack_lines if to_find in x[2]), "found a narrate_it"


def test40():
    """
    test40: check that format_tb works
    """
    set_narration_options(check=False)
    reset_all_narrations()

    try:
        f1("nf6")
        assert False, "should have raised"
    except:
        _, _, tb = sys.exc_info()
        tb_lines = format_tb(tb)
        assert not any(True for x in tb_lines if to_find in x), "found a narrate_it"


def test41():
    """
    test41: check that format_stack works
    """
    set_narration_options(check=False)
    reset_all_narrations()

    @narrate("in f")
    def f():
        return format_stack()

    stack_lines = f()
    assert not any(True for x in stack_lines if to_find in x), "found a %s" % to_find


def test42():
    """
    test42: check that format_exception works
    """
    set_narration_options(check=False)
    reset_all_narrations()

    try:
        f1("nf6")
    except:
        lines = format_exception(*sys.exc_info())
        assert not any(True for x in lines if to_find in x), "found a %s" % to_find


def test43():
    """
    test43: check that print_tb works
    """
    set_narration_options(check=False)
    reset_all_narrations()

    try:
        f1("nf6")
    except:
        _, _, tb = sys.exc_info()
        f = StringIO()
        print_tb(tb, file=f)
        result = f.getvalue()
        assert to_find not in result


def test44():
    """
    test44: check that print_exception works
    """
    set_narration_options(check=False)
    reset_all_narrations()

    try:
        f1("nf6")
    except:
        et, ev, tb = sys.exc_info()
        f = StringIO()
        print_exception(et, ev, tb, file=f)
        result = f.getvalue()
        assert to_find not in result


def test45():
    """
    test45: check that print_exc works
    """
    set_narration_options(check=False)
    reset_all_narrations()

    try:
        f1("nf6")
    except:
        f = StringIO()
        print_exc(file=f)
        result = f.getvalue()
        assert to_find not in result


def test46():
    """
    test46: check that format_exc works
    """
    set_narration_options(check=False)
    reset_all_narrations()

    try:
        f1("nf6")
    except:
        stuff = format_exc()
        assert to_find not in stuff


def test47():
    """
    test47: check that print_last works

    NOTE: this may not have meaningful results due to limitations in traceback.print_last
    """
    set_narration_options(check=False)
    reset_all_narrations()

    try:
        f1("nf6")
    except:
        pass
    f = StringIO()
    print_last(file=f)
    result = f.getvalue()
    assert to_find not in result


def test48():
    """
    test48: check that print_stack works
    """
    set_narration_options(check=False)
    reset_all_narrations()

    @narrate("test48")
    def f():
        f = StringIO()
        print_stack(file=f)
        return f.getvalue()

    result = f()
    assert to_find not in result


def test49():
    """
    test49: check that get_narration with different tags don't get the fragments
    """
    set_narration_options(check=False)
    reset_all_narrations()

    @narrate("test49", tags=["wibble"])
    def f():
        raise KeyError('ugh')

    try:
        f()
    except KeyError:
        assert len(get_narration(with_tags=["wobble"])) == 0
    except Exception as e:
        assert False, f'got an {e}'


def test50():
    """
    test50: check that get_narration with same tag gets the fragment
    """
    set_narration_options(check=False)
    reset_all_narrations()

    @narrate("test50", tags=["wibble"])
    def f():
        raise KeyError('ugh')

    try:
        f()
    except KeyError:
        assert any(['test50' in l for l in get_narration(with_tags=['wibble'])]),  \
                f'got: {get_narration(with_tags=["wibble"])}'
    except Exception as e:
        assert False, f'got an {e}'


def test51():
    """
    test51: check that using get_narration() with no tags gets all fragments
    """
    set_narration_options(check=False)
    reset_all_narrations()

    @narrate("test51", tags=["wibble"])
    def f():
        raise KeyError('ugh')

    try:
        f()
    except KeyError:
        assert any(['test51' in l for l in get_narration()]),  \
                f'got: {get_narration()}'
    except Exception as e:
        assert False, f'got an {e}'


def test52():
    """
    test52: check that a fragment with no tag is picked up when looking for a tag
    """
    set_narration_options(check=False)
    reset_all_narrations()

    @narrate("test52")
    def f():
        raise KeyError('ugh')

    try:
        f()
    except KeyError:
        assert any(['test52' in l for l in get_narration(with_tags=["wibble"])]),  \
                f'got: {get_narration(with_tags=["wibble"])}'
    except Exception as e:
        assert False, f'got an {e}'


def test53():
    """
    test53: Check that we do pick up context manager fragments with the right tag
    """
    set_narration_options(check=False)
    reset_all_narrations()

    def f():
        with narrate_cm("test53cm", tags=["wibble"]):
            raise KeyError('oops')

    try:
        f()
    except KeyError:
        assert len(get_narration(with_tags=['wibble'])) == 1
    except Exception as e:
        assert False, f'got an {e}'


def test54():
    """
    test54: check that we don't pick up cm fragments with the wrong tag
    """
    set_narration_options(check=False)
    reset_all_narrations()

    def f():
        with narrate_cm("test54cm", tags=["wibble"]):
            raise KeyError('oops')

    try:
        f()
    except KeyError:
        assert len(get_narration(with_tags=['wobble'])) == 0
    except Exception as e:
        assert False, f'got an {e}'


def test55():
    """
    test55: check we pick up cm fragements that don't have a tag
    """
    set_narration_options(check=False)
    reset_all_narrations()

    def f():
        with narrate_cm("test55cm"):
            raise KeyError('oops')

    try:
        f()
    except KeyError:
        assert len(get_narration(with_tags=['wobble'])) == 1
    except Exception as e:
        assert False, f'got an {e}'


def test56():
    """
    test56: check we pick up a tagged cm when we don't specify any
    """
    set_narration_options(check=False)
    reset_all_narrations()

    def f():
        with narrate_cm("test56cm", tags=['ibble']):
            raise KeyError('oops')

    try:
        f()
    except KeyError:
        assert len(get_narration()) == 1
    except Exception as e:
        assert False, f'got an {e}'


def test57():
    """
    test57: test a stack of calls, only pick up 1/2 of the fragments with tags
    """
    set_narration_options(check=False)
    reset_all_narrations()

    @narrate('f1', tags=["hit"])
    def f1():
        f2()

    @narrate('f2', tags=['miss', 'common'])
    def f2():
        f3()

    def f3():
        with narrate_cm('f3cm', tags=['hit', 'common']):
            f4()

    @narrate('f4', tags=['miss'])
    def f4():
        raise KeyError('you sunk my battleship')

    try:
        f1()
    except KeyError:
        pass
    except Exception as e:
        assert False, f'got an {e}'
    else:
        assert len(get_narration(with_tags=["hit"])) == 2
        assert len(get_narration(with_tags=["miss"])) == 2
        assert len(get_narration(with_tags=["common"])) == 2


def do_all():
    for k, v in sorted(globals().items()):
        if callable(v) and k.startswith("test"):
            print("Running test {}".format(k))
            try:
                v()
            except Exception as e:
                print("Test {} failed with:\n".format(k))
                traceback.print_exception(*sys.exc_info())


if __name__ == "__main__":
    do_all()
