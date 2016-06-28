import threading
from collections import deque

__version__ = "0.1"


class ErratorException(Exception):
    pass


# fragments is hashed by a thread's name and contains a list StoryFragments for each frame
# in the thread's call path
_thread_fragments = {}


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


class ErratorDeque(deque):
    def __init__(self, iterable=(), auto_prune=True):
        super(ErratorDeque, self).__init__(iterable=iterable)
        self.auto_prune = auto_prune

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
        one_true = any([f(o) for o in self])
        if one_true:
            while self and not f(self[-1]):
                self.pop()
            if self:
                self.pop()
        return


class NarrationFragment(object):
    IN_PROCESS = 1
    RAISED_EXCEPTION = 2
    PASSEDTHRU_EXCEPTION = 3
    COMPLETED = 4

    def __init__(self, text_or_func, *args, **kwargs):
        self.text_or_func = text_or_func
        self.args = args
        self.kwargs = kwargs if kwargs else {}
        self.context = None
        self.exception_text = None
        self.calling = None
        self.status = self.IN_PROCESS

    @classmethod
    def clone(cls, src):
        new = cls(src.text_or_func, *src.args, **src.kwargs)
        new.context = src.context
        new.exception_text = src.exception_text
        new.calling = src.calling
        return new

    def format(self):
        tale = (self.text_or_func(*self.args, **self.kwargs)
                if callable(self.text_or_func)
                else self.text_or_func)
        self.text_or_func = tale
        self.args = self.kwargs = None
        if self.exception_text:
            tale = "{}, but {} was raised".format(tale, self.exception_text)

        return tale

    def tell(self):
        tale = self.format()
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


class NarrationFragmentContextManager(NarrationFragment):
    def format(self):
        tale = super(NarrationFragmentContextManager, self).format()
        return "    {}".format(tale)

    def __enter__(self):
        tname = threading.current_thread().name
        d = _thread_fragments.setdefault(tname, ErratorDeque())
        d.append(self)
        self.calling = self
        return self

    def __exit__(self, exc_type, exc_val, _):
        tname = threading.current_thread().name
        d = _thread_fragments[tname]
        if exc_type is None:
            # then all went well; pop ourselves off the end
            self.status = self.COMPLETED
            if d and d.auto_prune:
                d.pop_until_true(lambda item: item.calling == item)
            self.calling = None  # break ref cycle
        else:
            if d[-1] is self:
                self.fragment_exception_text(exc_type, str(exc_val))
                self.status = self.RAISED_EXCEPTION
            else:
                self.status = self.PASSEDTHRU_EXCEPTION
            _ = self.format()


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
        get_narration_text().
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


def set_narration_options(thread=None, auto_prune=True):
    """
    Set options for capturing narration for the current thread.

    :param thread: threading.Thread object. If not supplied, the current thread is used
    :param auto_prune: boolean. determines if narration fragments are to be automatically
        removed upon successful return of a function of exit of a context manager's context.
        Default is True (prune successful fragments).
    """
    if thread is None:
        thread = threading.current_thread()
    elif not isinstance(thread, threading.Thread):
        raise ErratorException("the 'thread' argument isn't an instance of threading.Thread: {}".format(thread))
    try:
        d = _thread_fragments[thread.name]
    except KeyError:
        _thread_fragments[thread.name] = ErratorDeque(auto_prune=auto_prune)
    else:
        d.auto_prune = auto_prune


def copy_narration(thread=None, from_here=False):
    """
    Acquire copies of the NarrationFragment objects for the current exception
    narration.

    This method returns a list of NarrationFragment objects that capture all the narration
    fragments for the current narration for a specific thread. The actual narration can then
    be cleared, but this list will be uneffected.
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


def get_narration(thread=None, from_here=False):
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
        l = [nf.tell() for nf in d]
    else:
        # collect from the last IN_PROCESS fragment to the exception
        l = []
        for i in range(-1, -1 * len(d) - 1, -1):
            if d[i].status == NarrationFragment.IN_PROCESS:
                for j in range(i, 0, 1):
                    l.append(d[j].tell())
                break
    return l


def narrate(str_or_func):
    """
    Decorator for functions or methods that add narration that can be recovered if the
    method raises an exception

    :param str_or_func: either a string that will be captured and rendered if the function
        fails, or else a callable with the same signature as the function/method that is
        being decorated that will only be called if the function/method raises and exception;
        in this case, the callable will be invoked with the (possibly modified) arguments
        that were passed to the function. The callable must return a string, and that will
        be used for the string that describes the execution of the function/method

        NOTE: if a callable is passed in, it will only be called with the decorated
        function's arguments if the decorated function raises and exception during
        execution. This way no time is spent formatting a string that may not be needed.
        However, if the decorated function has changed the value of any of the arguments
        and these are in turn used in formatting the narration string, be aware that these
        may not be the values that were actually passed into the decorated function.
    """
    def capture_stanza(m):
        def narrate_it(*args, **kwargs):
            fragment = NarrationFragment(str_or_func, *args, **kwargs)
            fragment.calling = m
            tname = threading.current_thread().name
            frag_deque = _thread_fragments.setdefault(tname, ErratorDeque())
            frag_deque.append(fragment)
            try:
                _v = m(*args, **kwargs)
                fragment.status = fragment.COMPLETED
                if frag_deque and frag_deque.auto_prune:
                    frag_deque.pop_until_true(lambda item: item.calling == fragment.calling)
                fragment = None
                return _v
            except Exception as e:
                if fragment is frag_deque[-1]:
                    # only grab the exception text if this is the last fragment on the call chain
                    fragment.fragment_exception_text(e.__class__, str(e))
                    fragment.status = fragment.RAISED_EXCEPTION
                else:
                    fragment.status = fragment.PASSEDTHRU_EXCEPTION
                _ = fragment.format()  # get the formatted fragment right now!
                raise

        narrate_it.__name__ = m.__name__
        narrate_it.__doc__ = m.__doc__
        narrate_it.__dict__.update(m.__dict__)
        return narrate_it
    return capture_stanza


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
    ifsf = NarrationFragmentContextManager(text_or_func, *args, **kwargs)
    return ifsf


__all__ = ("narrate", "narrate_cm", "copy_narration", "NarrationFragment", "NarrationFragmentContextManager",
           "reset_all_narrations", "reset_narration", "get_narration", "set_narration_options",
           "ErratorException")
