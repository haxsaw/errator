import traceback
import sys
import threading
from collections import deque
from errator import (narrate, NarrationFragment, _thread_fragments, reset_all_narrations,
                     narrate_cm, copy_narration, reset_narration,
                     get_narration, set_narration_options, ErratorException)


def test01():
    """
    test01: Check string function of StoryFragment
    :return:
    """
    the_text = "some text"
    sf = NarrationFragment(the_text)
    assert the_text in sf.tell(), "The text we supplied wasn't in the fragment's output"


def test02():
    """
    test02: Check that a callable gets invoked
    :return:
    """
    text = "callable text"

    def f(a1, kw1=""):
        return "f:{} {}".format(a1, kw1)

    sf = NarrationFragment(f, "callable", kw1="text")
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
        assert isinstance(di, deque)
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

    @narrate("Calling f1")
    def f1():
        di = _thread_fragments[tname]
        assert len(di) == 1, "expected 1 fragment, got {}".format(len(di))
        f2()
        assert len(di) == 1, "expected 1 fragment, got {}".format(len(di))

    @narrate("Calling f2")
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
        assert isinstance(d, deque)
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

    @narrate("f1")
    def f1():
        return f2()

    @narrate("f2")
    def f2():
        return f3()

    @narrate("f3")
    def f3():
        frags = copy_narration()
        reset_narration()
        return frags

    the_story = f1()
    for name in ("f1", "f2", "f3"):
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

    @narrate("f1")
    def f1():
        f2()

    @narrate("f2")
    def f2():
        f3()

    @narrate("f3")
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

    @narrate("f1")
    def f1():
        f2()

    @narrate("f2")
    def f2():
        try:
            f3()
        except KeyError:
            lines = get_narration(from_here=True)
            assert len(lines) == 3
            reset_narration(from_here=True)

    @narrate("f3")
    def f3():
        f4()

    @narrate("f4")
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

    @narrate("f1")
    def f1():
        try:
            f2()
        except KeyError:
            reset_narration(from_here=True)
            lines = get_narration(from_here=True)
            assert len(lines) == 1, "Expected 1 line, got {}".format(len(lines))

    @narrate("f2")
    def f2():
        f3()

    @narrate("f3")
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

    @narrate("f1")
    def f1():
        try:
            f2()
        except KeyError:
            reset_narration(from_here=True)
            lines = get_narration(from_here=True)
            assert len(lines) == 0, "Expected 0 lines, got {}".format(len(lines))

    @narrate("f2")
    def f2():
        f3()

    @narrate("f3")
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
        with narrate_cm("f1 context"):
            try:
                f2()
            except KeyError:
                reset_narration(from_here=True)
                lines = get_narration(from_here=True)
                assert len(lines) == 1, "Expecting 1 lines, got {}".format(len(lines))

    @narrate("f2")
    def f2():
        lines = get_narration()
        assert len(lines) == 2, "Expecting 2 lines, got {}".format(len(lines))
        with narrate_cm("f3 context"):
            lines = get_narration()
            assert len(lines) == 3, "Expecting 3 lines, got {}".format(len(lines))
            raise KeyError

    f1()
    l2 = get_narration()
    assert len(l2) == 0, "Expecting no lines, got {}".format(len(l2))


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

    @narrate("f1")
    def f1():
        f2()
        lines = get_narration()
        assert "f1" not in lines

    def f2():
        try:
            f3()
        except KeyError:
            lines = get_narration(from_here=True)
            assert "f1" in lines
            reset_narration(from_here=True)

    @narrate("f3")
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

    @narrate("f1")
    def f1():
        f2()

    @narrate("f2")
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

    @narrate(lambda v: "Entering f1 with {}".format(v))
    def f1(x):
        return f2(x * 2)

    @narrate(lambda v: "Entering f2 with {}".format(v))
    def f2(y):
        y += 2
        return y

    a = f1(5)
    assert a == 12, "Unexpected value for a: {}".format(a)
    frags = copy_narration()
    assert len(frags) == 2, "Expected 2 fragments, got {}".format(len(frags))
    tof0 = frags[0].text_or_func
    assert "f1" in tof0, "the name 'f1' wasn't in the fragment: {}".format(tof0)
    assert "5" in tof0, "the value 5 isn't in the fragment: {}".format(tof0)
    tof1 = frags[1].text_or_func
    assert "f2" in tof1, "the name 'f2' wasn't in the fragment: {}".format(tof1)
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
    test25: check that we get an ErratorException when we try to run a broken callable for a context
    """

    set_narration_options(check=True)
    reset_all_narrations()

    try:
        with narrate_cm(lambda arg: "oops"):
            pass
    except ErratorException:
        pass
    else:
        assert False, "We should have raised an exception"

    set_narration_options(check=False)


def test26():
    """
    test26: check that we get an ErratorException when we try to run a broken callable during an exception
    """
    set_narration_options(check=False)
    reset_all_narrations()

    try:
        with narrate_cm(lambda arg: "oops"):
            raise KeyError("not this one")
    except ErratorException:
        pass
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
        pass
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
        pass
    except KeyError:
        assert False, "We shouldn't have gotten a KeyError"
    else:
        assert False, "we should have gotten an exception"

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
