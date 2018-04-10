from errator import narrate, get_narration, set_narration_options
import timeit
import platform


def f1(borkfunc, catchfunc):
    if borkfunc == 1:
        raise Exception("bork1")
    else:
        try:
            f2(borkfunc, catchfunc)
        except Exception:
            if catchfunc == 1:
                _ = get_narration()
            else:
                raise


@narrate("in 1")
def nf1(borkfunc, catchfunc):
    if borkfunc == 1:
        raise Exception("bork1")
    else:
        try:
            nf2(borkfunc, catchfunc)
        except Exception:
            if catchfunc == 1:
                _ = get_narration()
            else:
                raise


def f2(borkfunc, catchfunc):
    if borkfunc == 2:
        raise Exception("bork2")
    else:
        try:
            f3(borkfunc, catchfunc)
        except Exception:
            if catchfunc == 2:
                _ = get_narration()
            else:
                raise


@narrate("in 2")
def nf2(borkfunc, catchfunc):
    if borkfunc == 2:
        raise Exception("bork2")
    else:
        try:
            nf3(borkfunc, catchfunc)
        except Exception:
            if catchfunc == 2:
                _ = get_narration()
            else:
                raise


def f3(borkfunc, catchfunc):
    if borkfunc == 3:
        raise Exception("bork3")
    else:
        try:
            f4(borkfunc, catchfunc)
        except Exception:
            if catchfunc == 3:
                _ = get_narration()
            else:
                raise


@narrate("in 3")
def nf3(borkfunc, catchfunc):
    if borkfunc == 3:
        raise Exception("bork3")
    else:
        try:
            nf4(borkfunc, catchfunc)
        except Exception:
            if catchfunc == 3:
                _ = get_narration()
            else:
                raise


def f4(borkfunc, catchfunc):
    if borkfunc == 4:
        raise Exception("bork4")
    else:
        try:
            f5(borkfunc, catchfunc)
        except Exception:
            if catchfunc == 4:
                _ = get_narration()
            else:
                raise


@narrate("in 4")
def nf4(borkfunc, catchfunc):
    if borkfunc == 4:
        raise Exception("bork4")
    else:
        try:
            nf5(borkfunc, catchfunc)
        except Exception:
            if catchfunc == 4:
                _ = get_narration()
            else:
                raise


def f5(borkfunc, catchfunc):
    if borkfunc == 5:
        raise Exception("bork5")
    else:
        try:
            f6(borkfunc, catchfunc)
        except Exception:
            if catchfunc == 5:
                _ = get_narration()
            else:
                raise


@narrate("in 5")
def nf5(borkfunc, catchfunc):
    if borkfunc == 5:
        raise Exception("bork5")
    else:
        try:
            nf6(borkfunc, catchfunc)
        except Exception:
            if catchfunc == 5:
                _ = get_narration()
            else:
                raise


def f6(borkfunc, catchfunc):
    if borkfunc == 6:
        raise Exception("bork6")
    else:
        try:
            f7(borkfunc, catchfunc)
        except Exception:
            if catchfunc == 6:
                _ = get_narration()
            else:
                raise


@narrate("in 6")
def nf6(borkfunc, catchfunc):
    if borkfunc == 6:
        raise Exception("bork6")
    else:
        try:
            nf7(borkfunc, catchfunc)
        except Exception:
            if catchfunc == 6:
                _ = get_narration()
            else:
                raise


def f7(borkfunc, catchfunc):
    if borkfunc == 7:
        raise Exception("bork7")
    else:
        try:
            f8(borkfunc, catchfunc)
        except Exception:
            if catchfunc == 7:
                _ = get_narration()
            else:
                raise


@narrate("in 7")
def nf7(borkfunc, catchfunc):
    if borkfunc == 7:
        raise Exception("bork7")
    else:
        try:
            nf8(borkfunc, catchfunc)
        except Exception:
            if catchfunc == 7:
                _ = get_narration()
            else:
                raise


def f8(borkfunc, catchfunc):
    if borkfunc == 8:
        raise Exception("bork8")
    else:
        try:
            f9(borkfunc, catchfunc)
        except Exception:
            if catchfunc == 8:
                _ = get_narration()
            else:
                raise


@narrate("in 8")
def nf8(borkfunc, catchfunc):
    if borkfunc == 8:
        raise Exception("bork8")
    else:
        try:
            nf9(borkfunc, catchfunc)
        except Exception:
            if catchfunc == 8:
                _ = get_narration()
            else:
                raise


def f9(borkfunc, catchfunc):
    if borkfunc == 9:
        raise Exception("bork9")
    else:
        try:
            f10(borkfunc, catchfunc)
        except Exception:
            if catchfunc == 9:
                _ = get_narration()
            else:
                raise


@narrate("in 9")
def nf9(borkfunc, catchfunc):
    if borkfunc == 9:
        raise Exception("bork9")
    else:
        try:
            nf10(borkfunc, catchfunc)
        except Exception:
            if catchfunc == 9:
                _ = get_narration()
            else:
                raise


def f10(borkfunc, catchfunc):
    if borkfunc == 10:
        raise Exception("bottom")
    return


@narrate("in 10")
def nf10(borkfunc, catchfunc):
    if borkfunc == 10:
        raise Exception("bottom")
    return


def plain(bf, cf):
    return bf + cf


@narrate("simple")
def simple(bf, cf):
    return bf + cf


def do_it(errated=True):
    if errated:
        startfunc = nf1
    else:
        startfunc = f1

    for bf in range(1, 11):
        for cf in range(1, bf):
            try:
                startfunc(bf, cf)
            except Exception:
                if errated:
                    _ = get_narration()


def nested_call_timing(errated=True):
    if errated:
        startfunc = nf1
    else:
        startfunc = f1

    startfunc(100, 100)  # never raise, never catch
    if errated:
        _ = get_narration()


if __name__ == "__main__":
    print("Python version: {}".format(platform.python_version()))
    set_narration_options(verbose=False)
    loops = 1000
    timeit.do_it = do_it
    timeit.simple = simple
    timeit.plain = plain
    timeit.nested_call_timing = nested_call_timing
    # prime things so there's no first run penalty
    do_it(errated=True)

    # now do calls that show handling of narrations when there is a exception
    print("==Narrated nested call stack with exceptions==")
    narrated_elapsed = timeit.timeit(stmt="do_it(errated=True)", number=loops)
    print("{} loops took {}".format(loops, narrated_elapsed))
    print("==Plain nested call stack with exceptions==")
    plain_elapsed = timeit.timeit(stmt="do_it(errated=False)", number=loops)
    print("{} loops took {}".format(loops, plain_elapsed))
    print("Plain is {} times faster".format(narrated_elapsed / plain_elapsed))

    # next, do the same nested calls, but never raise an exception
    loops = 100000
    narrated_elapsed = timeit.timeit(stmt="nested_call_timing(errated=True)", number=loops)
    print("\n==Nested call times with narrations but no exceptions==")
    print("{} loops took {}".format(loops, narrated_elapsed))
    plain_elapsed = timeit.timeit(stmt="nested_call_timing(errated=False)", number=loops)
    print("==Nested call times with no narrations, no exceptions==")
    print("{} loops tool {}".format(loops, plain_elapsed))
    print("Plain is {} times faster".format(narrated_elapsed / plain_elapsed))

    # now do plain functions
    simple(1, 1)  # prime any first-time overheads out
    loops = 1000000
    narrated_elapsed = timeit.timeit(stmt="simple(1, 1)", number=loops)
    print("\n==Single string narrated call, no exceptions, {} calls: {}".format(loops, narrated_elapsed))
    plain_elapsed = timeit.timeit(stmt="plain(1, 1)", number=loops)
    print("==No errator decoration, no exceptions, {} calls: {}".format(loops, plain_elapsed))

    print("Plain is {} times faster".format(narrated_elapsed / plain_elapsed))
