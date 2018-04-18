from threading import current_thread, Thread
import traceback
import sys
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

from _errator import (ErratorException, _default_options, ErratorDeque, _thread_fragments,
                      NarrationFragment, NarrationFragmentContextManager, narrate, get_narration)

__version__ = "0.3.3"


def set_default_options(auto_prune=None, check=None, verbose=None):
    """
    Sets default options that are applied to each per-narration thread
    :param auto_prune: optional, boolean, defaults to True. If not specified, then don't
        change the existing value of the auto_prune default option. Otherwise, set the
        default value to the boolean interpretation of auto_prune.

        auto_prune tells errator whether or not to remove narration fragments upon successful
        returns from a function/method or exits from a context. If set to False, fragments
        are retained on returns/exits, and it is up to the user entirely to manage the fragment
        stack using reset_narration().
    :param check: optional, boolean, defaults to False. If not specified, then don't change
        the existing value. Otherwise, set the default value to the boolean interpretation of
        check.

        The check option changes the logic around fragment text generation. Normally, fragments
        only get their text generated in the case of an exception in a decorated function/method
        or context. When check is True, the fragment's text is always generated when the function/
        method or context finishes, regardless if there's an exception. This is particularly handy
        in testing for the cases where narrate() or narrate_cm() have been given a callable
        instead of a string-- the callable will be invoked every time instead of just when there's
        an exception, allowing you to make sure that the callable operates properly and itself
        won't be a source of errors (which may manifest themselves as exceptions raised within
        errator itself). The check option should normally be False, as there's a performance penalty
        to pay for always generating fragment text.
    :param verbose: boolean, optional, default False. If True, then the returned list of strings will include
        information on file, function, and line number. These more verbose strings will have an embedded
        \n to split the lines into two.
    :return: dict of default options.
    """
    if auto_prune is not None:
        _default_options["auto_prune"] = bool(auto_prune)
    if check is not None:
        _default_options["check"] = bool(check)
    if verbose is not None:
        _default_options["verbose"] = bool(verbose)

    return dict(_default_options)


def reset_all_narrations():
    """
    Clears out all narration fragments for all threads

    This function simply removes all narration fragments from tracking. Any options
    set on a per-thread narration capture basis are retained.
    """
    for k in list(_thread_fragments.keys()):
        _thread_fragments[k].clear()


def reset_narration(thread=None, from_here=False):
    """
    Clears out narration fragments for the specified thread

    This function removes narration fragments from the named thread. It can clear them all out
    or a subset based on the current execution point of the code.
    :param thread: a Thread object (optional). Indicates which thread's narration
        fragments are to be cleared. If not specified, the calling thread's narration is
        cleared.
    :param from_here: boolean, optional, default False. If True, then only clear out the fragments
        from the fragment nearest the current stack frame to the fragment where the exception occurred.
        This is useful if you have auto_prune set to False for this thread's narration and you want
        to clean up the fragments for which you may have previously retrieved the narration using
        get_narration().
    """
    if thread is None:
        thread = current_thread()
    elif not isinstance(thread, Thread):
        raise ErratorException("the 'thread' argument isn't an instance of Thread: {}".format(thread))
    d = _thread_fragments.get(thread.name)
    if d:
        assert isinstance(d, ErratorDeque)
        if not from_here:
            d.clear()
        else:
            for i in range(-1, -1 * len(d) - 1, -1):
                if d[i].status == NarrationFragment.IN_PROCESS:
                    if d.auto_prune:
                        if i != -1:
                            target = d[i+1]
                            d.pop_until_true(lambda x: x is target)
                    else:
                        target = d[i]
                        d.pop_until_true(lambda x: x is target)
                    break
            else:
                # in this case, nothing was IN_PROCESS, so we should clear all
                d.clear()


def set_narration_options(thread=None, auto_prune=None, check=None, verbose=None):
    """
    Set options for capturing narration for the current thread.

    :param thread: Thread object. If not supplied, the current thread is used.
        Identifies the thread whose narration will be impacted by the options.
    :param auto_prune: optional, boolean, defaults to True. If not specified, then don't
        change the existing value of the auto_prune option. Otherwise, set the
        value to the boolean interpretation of auto_prune.

        auto_prune tells errator whether or not to remove narration fragments upon successful
        returns from a function/method or exits from a context. If set to False, fragments
        are retained on returns/exits, and it is up to the user entirely to manage the fragment
        stack using reset_narration().
    :param check: optional, boolean, defaults to False. If not specified, then don't change
        the existing value. Otherwise, set the value to the boolean interpretation of
        check.

        The check option changes the logic around fragment text generation. Normally, fragments
        only get their text generated in the case of an exception in a decorated function/method
        or context. When check is True, the fragment's text is always generated when the function/
        method or context finishes, regardless if there's an exception. This is particularly handy
        in testing for the cases where narrate() or narrate_cm() have been given a callable
        instead of a string-- the callable will be invoked every time instead of just when there's
        an exception, allowing you to make sure that the callable operates properly and itself
        won't be a source of errors (which may manifest themselves as exceptions raised within
        errator itself). The check option should normally be False, as there's a performance penalty
        to pay for always generating fragment text.
    :param verbose: boolean, optional, default False. If True, then the returned list of strings will include
        information on file, function, and line number. These more verbose strings will have an embedded
        \n to split the lines into two.
    """
    if thread is None:
        thread = current_thread()
    elif not isinstance(thread, Thread):
        raise ErratorException("the 'thread' argument isn't an instance of Thread: {}".format(thread))
    try:
        d = _thread_fragments[thread.name]
        d.set_auto_prune(auto_prune).set_check(check).set_verbose(verbose)
    except KeyError:
        # this should never happen now that _thread_fragments is a defaultdict
        _thread_fragments[thread.name] = ErratorDeque(auto_prune=bool(auto_prune)
                                                      if auto_prune is not None
                                                      else None,
                                                      check=bool(check)
                                                      if check is not None
                                                      else None)


def copy_narration(thread=None, from_here=False):
    """
    Acquire copies of the NarrationFragment objects for the current exception
    narration.

    This method returns a list of NarrationFragment objects that capture all the narration
    fragments for the current narration for a specific thread. The actual narration can then
    be cleared, but this list will be unaffected.
    :param thread: optional, instance of Thread. If unspecified, the current thread is used.
    :param from_here: boolean, optional, default False. If True, then the list of fragments returned is
        from the narration fragment nearest the active stack frame and down to the exception origin, not
        from the most global level to the exception. This is useful from where the exception is actually caught,
        as it provides a way to only show the narration from this point forward. However, not showing all the
        fragments may actually hide important aspects of the narration, so bear this in mind when using
        this to prune the narration. Use in conjuction with the auto_prune option set to False to allow
        several stack frames to return before collecting the narration (be sure to manually clean up
        the narration when auto_prune is False).
    :return: a list of NarrationFragment objects. The first item is the most global in the narration.
    """
    if thread is None:
        thread = current_thread()
    elif not isinstance(thread, Thread):
        raise ErratorException("the 'thread' argument isn't an instance of Thread: {}".format(thread))
    d = _thread_fragments.get(thread.name)
    if not d:
        l = []
    elif not from_here:
        l = [o.__class__.clone(o) for o in d]
    else:
        l = []
        for i in range(-1, -1 * len(d) - 1, -1):
            if d[i].status == NarrationFragment.IN_PROCESS:
                for j in range(i, 0, 1):
                    l.append(NarrationFragment.clone(d[j]))
                break
    return l


_magic_name = "narrate_it"


def narrate_cm(text_or_func, *args, **kwargs):
    """
    Create a context manager that captures some narration of the operations being done within it

    This function returns an object that is a context manager which captures the narration
    of the code executing within the context. It has similar behaviour to narrate() in
    that either a fixed string can be provided or a callable that will be invoked if there
    is an exception raised during the execution of the context.

    :param text_or_func: either a string that will be captured and rendered if the function
        fails, or else a callable with the same signature as the function/method that is
        being decorated that will only be called if the function/method raises and exception;
        in this case, the callable will be invoked with the (possibly modified) arguments
        that were passed to the function. The callable must return a string, and that will
        be used for the string that describes the execution of the function/method
    :param args: sequence of positional arguments; if str_or_func is a callable, these will
        be the  positional arguments passed to the callable. If str_or_func is a string
        itself, positional arguments are ignored.
    :param kwargs: keyword arguments; if str_or_func is a callable, then these will be the
        keyword arguments passed to the callable. If str_or_func is a string itself,
        keyword arguments are ignored.
    :return: An errator context manager (NarrationFragmentContextManager)
    """
    ifsf = NarrationFragmentContextManager.get_instance(text_or_func, None, *args, **kwargs)
    return ifsf


# Traceback sanitizers
# errator leaves a bunch of cruft in the stack trace when an exception occurs; this cruft
# appears when you use the various functions in the standard traceback module. The following
# functions provide analogs to a number of the functions in traceback, but they filter
# out the internal function calls to errator functions.

def extract_tb(tb, limit=None):
    """
    behaves like traceback.extract_tb, but removes errator functions from the trace
    :param tb: traceback to process
    :param limit: optional; int. The number of stack frame entries to return; the actual
        number returned may be lower once errator calls are removed
    :return: a list of 4-tuples containing (filename, line number, function name, text)
    """
    return [f for f in traceback.extract_tb(tb, limit) if _magic_name not in f[2]]


def extract_stack(f=None, limit=None):
    """
    behaves like traceback.extract_stack, but removes errator functions from the trace
    :param f: optional; specifies an alternate stack frame to start at
    :param limit: optional; int. The number of stack frame entries to return; the actual
        number returned may be lower once errator calls are removed
    :return: a list of 4-tuples containing (filename, line number, function name, text)
    """
    return [f for f in traceback.extract_stack(f, limit) if _magic_name not in f[2]]


def format_tb(tb, limit=None):
    """
    behaves like traceback.format_tb, but removes errator functions from the trace
    :param tb: The traceback you wish to format
    :param limit: optional; int. The number of stack frame entries to return; the actual
        number returned may be lower once errator calls are removed
    :return: a list of formatted strings for the trace
    """
    return traceback.format_list(extract_tb(tb, limit))


def format_stack(f=None, limit=None):
    """
    behaves like traceback.format_stack, but removes errator functions from the trace
    :param f: optional; specifies an alternate stack frame to start at
    :param limit: optional; int. The number of stack frame entries to return; the actual
        number returned may be lower once errator calls are removed
    :return: a list of formatted strings for the trace
    """
    return traceback.format_list(extract_stack(f, limit))


format_exception_only = traceback.format_exception_only


def format_exception(etype, evalue, tb, limit=None):
    """
    behaves like traceback.format_exception, but removes errator functions from the trace
    :param etype: exeption type
    :param evalue: exception value
    :param tb: traceback to print; these are the values returne by sys.exc_info()
    :param limit: optional; int. The number of stack frame entries to return; the actual
        number returned may be lower once errator calls are removed
    :return: a list of formatted strings for the trace
    """
    tb = format_tb(tb, limit)
    exc = format_exception_only(etype, evalue)
    return tb + exc


def print_tb(tb, limit=None, file=sys.stderr):
    """
    behaves like traceback.print_tb, but removes errator functions from the trace
    :param tb: traceback to print; these are the values returne by sys.exc_info()
    :param limit: optional; int. The number of stack frame entries to return; the actual
        number returned may be lower once errator calls are removed
    :param file: optional; open file-like object to write() to; if not specified defaults to sys.stderr
    """
    for l in format_tb(tb, limit):
        file.write(l.decode() if hasattr(l, "decode") else l)
    file.flush()


def print_exception(etype, evalue, tb, limit=None, file=sys.stderr):
    """
    behaves like traceback.print_exception, but removes errator functions from the trace
    :param etype: exeption type
    :param evalue: exception value
    :param tb: traceback to print; these are the values returne by sys.exc_info()
    :param limit: optional; int. The number of stack frame entries to return; the actual
        number returned may be lower once errator calls are removed
    :param file: optional; open file-like object to write() to; if not specified defaults to sys.stderr
    """
    for l in format_exception(etype, evalue, tb, limit):
        file.write(l.decode() if hasattr(l, "decode") else l)
    file.flush()


def print_exc(limit=None, file=sys.stderr):
    """
    behaves like traceback.print_exc, but removes errator functions from the trace
    :param limit: optional; int. The number of stack frame entries to return; the actual
        number returned may be lower once errator calls are removed
    :param file: optional; open file-like object to write() to; if not specified defaults to sys.stderr
    """
    etype, evalue, tb = sys.exc_info()
    print_exception(etype, evalue, tb, limit, file)


def format_exc(limit=None):
    """
    behaves like traceback.format_exc, but removes errator functions from the trace
    :param limit: optional; int. The number of stack frame entries to return; the actual
        number returned may be lower once errator calls are removed
    :return: a string containing the formatted exception and traceback
    """
    f = StringIO()
    print_exc(limit, f)
    return f.getvalue()


def print_last(limit=None, file=sys.stderr):
    """
    behaves like traceback.print_last, but removes errator functions from the trace. As noted
    in the man page for traceback.print_last, this will only work when an exception has reached the
    interactive prompt
    :param limit: optional; int. The number of stack frame entries to return; the actual
        number returned may be lower once errator calls are removed
    :param file: optional; open file-like object to write() to; if not specified defaults to sys.stderr
    """
    print_exception(getattr(sys, "last_type", None), getattr(sys, "last_value", None),
                    getattr(sys, "last_traceback", None), limit, file)


def print_stack(f=None, limit=None, file=sys.stderr):
    """
    behaves like traceback.print_stack, but removes errator functions from the trace.
    :param f: optional; specifies an alternate stack frame to start at
    :param limit: optional; int. The number of stack frame entries to return; the actual
        number returned may be lower once errator calls are removed
    :param file: optional; open file-like object to write() to; if not specified defaults to sys.stderr
    """
    for l in format_stack(f, limit):
        file.write(l.decode() if hasattr(l, "decode") else l)
    file.flush()


__all__ = ("narrate", "narrate_cm", "copy_narration", "NarrationFragment", "NarrationFragmentContextManager",
           "reset_all_narrations", "reset_narration", "get_narration", "set_narration_options",
           "ErratorException", "set_default_options", "extract_tb", "extract_stack", "format_tb",
           "format_stack", "format_exception_only", "format_exception", "print_tb", "print_exception",
           "print_exc", "format_exc", "print_last", "print_stack")
