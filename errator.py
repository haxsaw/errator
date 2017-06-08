import threading
from collections import deque, defaultdict
import inspect
import traceback
import sys
try:
    from cStringIO import StringIO
except ImportError:
    from io import StringIO

__version__ = "0.2.1"


class ErratorException(Exception):
    pass


class ErratorDeque(deque):
    def __init__(self, iterable=(), auto_prune=None, check=None):
        super(ErratorDeque, self).__init__(iterable=iterable)
        self.__dict__.update(_default_options)
        if auto_prune is not None:
            self.auto_prune = auto_prune
        if check is not None:
            self.check = check

    def set_check(self, value):
        """
        sets the check flag to the provided boolean value
        :param value: interpreted as a boolean value for self.check; if None don't change the value
        :return: self
        """
        if value is not None:
            self.check = bool(value)
        else:
            self.check = _default_options["check"]
        return self

    def set_auto_prune(self, value):
        """
        sets the auto_prune flag to the provided boolean value
        :param value: interpreted as a boolean value for self.auto_prune; if None don't change the value
        :return: self
        """
        if value is not None:
            self.auto_prune = bool(value)
        else:
            self.auto_prune = _default_options["auto_prune"]
        return self

    def pop_until_true(self, f):
        """
        Performs pop(right) from the deque up to and including the element for which f returns True

        This method tests the last element in the deque (right end) using the supplied function f.
        If f returns False for the element, the element is popped and the test repeated for new last
        element. If f returns True, that element is popped and the method returns. If f never returns
        True, then all elements will be popped from the list.
        :param f: callable of one argument, an item on the deque. Returns True if the item is the
            last one to pop from the deque, False otherwise.
        :return:
        """
        while self and not f(self[-1]):
            inst = self.pop()
            inst.__class__.return_instance(inst)
        if self:
            inst = self.pop()
            inst.__class__.return_instance(inst)
        return


# _thread_fragments is hashed by a thread's name and contains a list StoryFragments for each frame
# in the thread's call path
_thread_fragments = defaultdict(ErratorDeque)


def _x():
    pass

_func_attrs = set(_x.__dict__.keys())

del _x


def _i():
    yield None

_gen_attrs = set(_i.__dict__.keys())

del _i


class _X(object):
    def x(self):
        pass

_unbound_meth_attrs = set(_X.x.__dict__.keys())

del _X


_expected_attrs = _func_attrs.union(_unbound_meth_attrs).union(_gen_attrs)


_default_options = {"auto_prune": True,
                    "check": False}


def set_default_options(auto_prune=None, check=None):
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
    :return: dict of default options.
    """
    if auto_prune is not None:
        _default_options["auto_prune"] = bool(auto_prune)
    if check is not None:
        _default_options["check"] = bool(check)

    return dict(_default_options)


class NarrationFragment(object):
    IN_PROCESS = 1
    RAISED_EXCEPTION = 2
    PASSEDTHRU_EXCEPTION = 3
    COMPLETED = 4

    _free_instances = deque()

    _callable_id_to_filename = {}

    @classmethod
    def get_instance(cls, text_or_func, narrated_callable, *args, **kwargs):
        try:
            inst = cls._free_instances.pop()
            assert isinstance(inst, NarrationFragment)
            inst._reset(text_or_func, narrated_callable, *args, **kwargs)
        except IndexError:
            inst = cls(text_or_func, narrated_callable, *args, **kwargs)
        return inst

    @classmethod
    def return_instance(cls, inst):
        cls._free_instances.append(inst)

    def __init__(self, text_or_func, narrated_callable, *args, **kwargs):
        """
        Creates a new NarrationFragment that will report using the supplied text or func
        :param text_or_func: either a string or a callable with the same signature as the
            callable being decorated
        :param narrated_callable: the callable being decorated or None. If supplied, then
            the callable will be inspected and some metadata on it will be saved
        :param args: possibly empty sequence of additional arguments
        :param kwargs: possibly empty dictionary of keyword arguments
        """
        self._reset(text_or_func, narrated_callable, *args, **kwargs)

    def _reset(self, text_or_func, narrated_callable, *args, **kwargs):
        self.text_or_func = text_or_func
        self.args = args
        self.kwargs = kwargs if kwargs else {}
        self.context = None
        self.exception_text = None
        self.calling = None
        self.status = self.IN_PROCESS
        if narrated_callable:
            self.func_name = narrated_callable.__name__
            ncid = id(narrated_callable)
            sf = self._callable_id_to_filename.get(ncid)
            if sf is None:
                self._callable_id_to_filename[ncid] = sf = inspect.getsourcefile(narrated_callable)
            self.source_file = sf
        else:
            self.func_name = None
            self.source_file = None
        self.lineno = None

    def frame_describes_func(self, frame):
        """
        returns True if the supplied tuple from inspect.stack/trace matches the
        function and file name for this fragment
        :param frame:
        :return:
        """
        return self.func_name == frame[3] and self.source_file == frame[1]

    def annotate_fragment(self, frame):
        """
        Extract relevant info from supplied FrameInfo object
        :param frame:
        :return:
        """
        self.lineno = frame[2]

    @classmethod
    def clone(cls, src):
        new = cls(src.text_or_func, None,
                  *src.args if src.args is not None else (),
                  **src.kwargs if src.kwargs is not None else {})
        new.context = src.context
        new.exception_text = src.exception_text
        new.calling = src.calling
        new.func_name = src.func_name
        new.source_file = src.source_file
        new.lineno = src.lineno
        return new

    def format(self, verbose=False):
        tale = (self.text_or_func(*self.args, **self.kwargs)
                if callable(self.text_or_func)
                else self.text_or_func)

        self.args = self.kwargs = None

        if self.exception_text:
            tale = "{}, but {} was raised".format(tale, self.exception_text)
            self.exception_text = None
        self.text_or_func = tale

        if verbose and self.func_name:
            if self.lineno is not None:
                result = "\n".join([tale, "    line %s in %s, %s" % (str(self.lineno),
                                                                   str(self.func_name),
                                                                   str(self.source_file))])
            else:
                result = "\n".join([tale, "%s in %s" % (str(self.func_name),
                                                        str(self.source_file))])
        else:
            result = tale

        return result

    def tell(self, verbose=False):
        tale = self.format(verbose=verbose)
        return tale

    def fragment_context(self, context=None):
        self.context = context

    def fragment_exception_text(self, etype, text):
        self.exception_text = "exception type: {}, value: '{}'".format(etype.__name__, text)

    def tell_ex(self):
        tale = self.format()
        context = str(self.context)
        output = "{} (context:{})".format(tale, context)
        return output


def _pop_until_found_calling(item):
    return item.calling == item


class NarrationFragmentContextManager(NarrationFragment):
    _free_instances = deque()

    def __init__(self, *args, **kwargs):
        super(NarrationFragmentContextManager, self).__init__(*args, **kwargs)
        calling_frame = inspect.stack()[3]
        self.func_name = calling_frame[3]
        self.source_file = calling_frame[1]

    def format(self, verbose=False):
        tale = super(NarrationFragmentContextManager, self).format(verbose=verbose)
        parts = tale.split("\n")
        parts = [" " * (i + 2) + parts[i] for i in range(len(parts))]
        return "\n".join(parts)
        # return "    {}".format(tale)

    def __enter__(self):
        tname = threading.current_thread().name
        _thread_fragments[tname].append(self)
        # d = _thread_fragments.setdefault(tname, ErratorDeque())
        # d.append(self)
        self.calling = self
        return self

    def __exit__(self, exc_type, exc_val, _):
        tname = threading.current_thread().name
        d = _thread_fragments[tname]
        # d = _thread_fragments.setdefault(tname, ErratorDeque())
        if exc_type is None:
            # then all went well; pop ourselves off the end
            self.status = self.COMPLETED
            if d.check:
                try:
                    _ = self.format()
                except Exception as e:
                    ctx_frame = inspect.getouterframes(inspect.currentframe())[1]
                    frame, fname, lineno, function, _, _ = ctx_frame
                    del frame, function, ctx_frame
                    raise ErratorException("Failed formatting fragment in context; got exception {}, '{}'; "
                                           "{}:{} is the last line of the context".format(type(e), str(e),
                                                                                          fname, lineno))

            if d and d.auto_prune:
                d.pop_until_true(_pop_until_found_calling)
            self.calling = None  # break ref cycle
        else:
            if d[-1] is self:
                # this is where the exception was raised
                self.fragment_exception_text(exc_type, str(exc_val))
                self.status = self.RAISED_EXCEPTION
                # the following code annotates fragments with stack trace information
                # so if verbose output is requesting it can be included
                tb = inspect.trace()
                stack = inspect.stack()
                stack.reverse()
                sc = deque(stack + tb)  # NOTE: slightly different than for func decorators!
                deck = deque(d)
                while deck and sc:
                    while sc and not deck[-1].frame_describes_func(sc[-1]):
                        sc.pop()
                    if sc:
                        deck[-1].annotate_fragment(sc[-1])
                        deck.pop()
                        # while deck and isinstance(deck[-1], NarrationFragmentContextManager):
                        #     deck.pop()
                        # if deck and deck[-1].frame_describes_func(sc[-1]):
                        #     deck.pop()
                        # sc.pop()
            else:
                self.status = self.PASSEDTHRU_EXCEPTION
            try:
                _ = self.format()
            except Exception as e:
                ctx_frame = inspect.getouterframes(inspect.currentframe())[1]
                frame, fname, lineno, function, _, _ = ctx_frame
                del frame, function, ctx_frame
                raise ErratorException("Failed formatting fragment in context; got exception {}, '{}'; "
                                       "{}:{} is the last line of the context".format(type(e), str(e),
                                                                                      fname, lineno))


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
    :param thread: a threading.Thread object (optional). Indicates which thread's narration
        fragments are to be cleared. If not specified, the calling thread's narration is
        cleared.
    :param from_here: boolean, optional, default False. If True, then only clear out the fragments
        from the fragment nearest the current stack frame to the fragment where the exception occurred.
        This is useful if you have auto_prune set to False for this thread's narration and you want
        to clean up the fragments for which you may have previously retrieved the narration using
        get_narration().
    """
    if thread is None:
        thread = threading.current_thread()
    elif not isinstance(thread, threading.Thread):
        raise ErratorException("the 'thread' argument isn't an instance of threading.Thread: {}".format(thread))
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


def set_narration_options(thread=None, auto_prune=None, check=None):
    """
    Set options for capturing narration for the current thread.

    :param thread: threading.Thread object. If not supplied, the current thread is used.
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
    """
    if thread is None:
        thread = threading.current_thread()
    elif not isinstance(thread, threading.Thread):
        raise ErratorException("the 'thread' argument isn't an instance of threading.Thread: {}".format(thread))
    try:
        d = _thread_fragments[thread.name]
        d.set_auto_prune(auto_prune).set_check(check)
    except KeyError:
        # this should never happen now that _thread_fragments is a defaultdict
        _thread_fragments[thread.name] = ErratorDeque(auto_prune=bool(auto_prune)
                                                      if auto_prune is not None
                                                      else None,
                                                      check=bool(check)
                                                      if check is not None
                                                      else None)
    else:
        if auto_prune is not None:
            d.auto_prune = bool(auto_prune)
        if check is not None:
            d.check = bool(check)


def copy_narration(thread=None, from_here=False):
    """
    Acquire copies of the NarrationFragment objects for the current exception
    narration.

    This method returns a list of NarrationFragment objects that capture all the narration
    fragments for the current narration for a specific thread. The actual narration can then
    be cleared, but this list will be unaffected.
    :param thread: optional, instance of threading.Thread. If unspecified, the current thread is used.
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
        thread = threading.current_thread()
    elif not isinstance(thread, threading.Thread):
        raise ErratorException("the 'thread' argument isn't an instance of threading.Thread: {}".format(thread))
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


def get_narration(thread=None, from_here=False, verbose=False):
    """
    Return a list of strings, each one a narration fragment in the function call path.

    This method tells the tale of an exception; it returns a list of strings that are the narration fragments
    from each function/method call or context where narration has been captured. It starts at the most global level
    and goes to the level where the exception was raised.

    :param thread: instance of threading.Thread. If not supplied, the current thread is used.
    :param from_here: boolean, optional, default False. If True, then the list of strings returned is
        from the narration fragment nearest the active stack frame and down to the exception origin, not
        from the most global level to the exception. This is useful from where the exception is actually caught,
        as it provides a way to only show the narration from this point forward. However, not showing all the
        fragments may actually hide important aspects of the narration, so bear this in mind when using
        this to prune the narration. Use in conjuction with the auto_prune option set to False to allow
        several stack frames to return before collecting the narration (be sure to manually clean up
        the narration when auto_prune is False).
    :param verbose: boolean, optional, default False. If True, then the returned list of strings will include
        information on file, function, and line number. These more verbose strings will have an embedded
        \n to split the lines into two.
    :return: list of formatted strings.
    """
    if thread is None:
        thread = threading.current_thread()
    elif not isinstance(thread, threading.Thread):
        raise ErratorException("the 'thread' argument isn't an instance of threading.Thread: {}".format(thread))
    d = _thread_fragments.get(thread.name)
    if not d:
        l = []
    elif not from_here:
        l = [nf.tell(verbose=verbose) for nf in d]
    else:
        # collect from the last IN_PROCESS fragment to the exception
        l = []
        for i in range(-1, -1 * len(d) - 1, -1):
            if d[i].status == NarrationFragment.IN_PROCESS:
                for j in range(i, 0, 1):
                    l.append(d[j].tell(verbose=verbose))
                break
    return l


def narrate(str_or_func):
    """
    Decorator for functions or methods that add narration that can be recovered if the
    method raises an exception

    :param str_or_func: either a string that will be captured and rendered if the function
        fails, or else a callable with the same signature as the function/method that is
        being decorated that will only be called if the function/method raises an exception;
        in this case, the callable will be invoked with the (possibly modified) arguments
        that were passed to the function. The callable must return a string, and that will
        be used for the string that describes the execution of the function/method

        NOTE: if a callable is passed in, it will only be called with the decorated
        function's arguments if the decorated function raises an exception during
        execution. This way no time is spent formatting a string that may not be needed.
        However, if the decorated function has changed the value of any of the arguments
        and these are in turn used in formatting the narration string, be aware that these
        may not be the values that were actually passed into the decorated function.
    """
    def capture_stanza(m):
        def narrate_it(*args, **kwargs):
            fragment = NarrationFragment.get_instance(str_or_func, m, *args, **kwargs)
            fragment.calling = m
            tname = threading.current_thread().name
            # frag_deque = _thread_fragments.setdefault(tname, ErratorDeque())
            frag_deque = _thread_fragments[tname]
            frag_deque.append(fragment)
            try:
                _v = m(*args, **kwargs)
                fragment.status = fragment.COMPLETED
                if frag_deque.check:
                    try:
                        _ = fragment.format()
                    except Exception as e:
                        raise ErratorException("Failed formatting the fragment for function {}; "
                                               "received exception {}, '{}'".format(m, type(e), str(e)))
                if frag_deque and frag_deque.auto_prune:
                    frag_deque.pop_until_true(lambda item: item.calling == m)
                fragment = None
                return _v
            except Exception as e:
                if fragment is frag_deque[-1]:
                    # only grab the exception text if this is the last fragment on the call chain
                    fragment.fragment_exception_text(e.__class__, str(e))
                    fragment.status = fragment.RAISED_EXCEPTION
                    # the following code annotates fragments with stack trace information
                    # so if verbose output is requested it can be included
                    tb = inspect.trace()
                    stack = inspect.stack()
                    stack.reverse()
                    sc = deque(stack + tb[1:])
                    deck = deque(frag_deque)
                    while deck and sc:
                        while sc and not deck[-1].frame_describes_func(sc[-1]):
                            sc.pop()
                        if sc:
                            deck[-1].annotate_fragment(sc[-1])
                            deck.pop()
                            # while deck and isinstance(deck[-1], NarrationFragmentContextManager):
                            #     deck.pop()
                            # if deck and deck[-1].frame_describes_func(sc[-1]):
                            #     deck.pop()
                            # sc.pop()
                else:
                    fragment.status = fragment.PASSEDTHRU_EXCEPTION
                try:
                    _ = fragment.format()  # get the formatted fragment right now!
                except Exception as e:
                    raise ErratorException("Failed formatting the fragment for function {}; "
                                           "received exception {}, '{}'".format(m, type(e), str(e)))
                raise

        narrate_it.__name__ = m.__name__
        narrate_it.__doc__ = m.__doc__
        narrate_it.__dict__.update(m.__dict__)
        return narrate_it
    return capture_stanza


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
    return [f for f in traceback.extract_tb(tb, limit) if f[2] != _magic_name]


def extract_stack(f=None, limit=None):
    """
    behaves like traceback.extract_stack, but removes errator functions from the trace
    :param f: optional; specifies an alternate stack frame to start at
    :param limit: optional; int. The number of stack frame entries to return; the actual
        number returned may be lower once errator calls are removed
    :return: a list of 4-tuples containing (filename, line number, function name, text)
    """
    return [f for f in traceback.extract_stack(f, limit) if f[2] != _magic_name]


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
