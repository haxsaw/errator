from collections import deque, defaultdict
import inspect
from threading import current_thread, Thread

_default_options = {"auto_prune": True,
                    "check": False,
                    "verbose": False}


class ErratorException(Exception):
    pass


class ErratorDeque(deque):
    def __init__(self, iterable=(), auto_prune=None, check=None, verbose=None):
        super(ErratorDeque, self).__init__(iterable=iterable)
        self.__dict__.update(_default_options)
        if auto_prune is not None:
            self.auto_prune = bool(auto_prune)

        if check is not None:
            self.check = bool(check)

        if verbose is not None:
            self.verbose = bool(verbose)

    def set_check(self, value):
        """
        sets the check flag to the provided boolean value
        :param value: interpreted as a boolean value for self.check; if None don't change the value
        :return: self
        """
        if value is not None:
            self.check = bool(value)
        return self

    def set_auto_prune(self, value):
        """
        sets the auto_prune flag to the provided boolean value
        :param value: interpreted as a boolean value for self.auto_prune; if None don't change the value
        :return: self
        """
        if value is not None:
            self.auto_prune = bool(value)
        return self

    def set_verbose(self, value):
        """
        sets the verbose flag to the provided boolean value
        :param value: interpreted as a boolean value for self.verbose; if None don't change
        :return: self
        """
        if value is not None:
            self.verbose = bool(value)
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
        selfpop = self.pop
        while self and not f(self[-1]):
            inst = selfpop()
            inst.__class__.return_instance(inst)
        if self:
            inst = selfpop()
            inst.__class__.return_instance(inst)
        return


# _thread_fragments is hashed by a thread's name and contains a deque NarrationFragment for each frame
# in the thread's call path
_thread_fragments = defaultdict(ErratorDeque)


cdef class NarrationFragment(object):
    # CYTHON
    cdef public text_or_func
    cdef public tuple args
    cdef public dict kwargs
    cdef public str exception_text
    cdef public calling
    cdef public int status
    cdef public str func_name, source_file
    cdef public int lineno
    # CYTHON

    IN_PROCESS = 1
    RAISED_EXCEPTION = 2
    PASSEDTHRU_EXCEPTION = 3
    COMPLETED = 4

    _free_instances = deque()

    _callable_id_to_filename = {}


    @classmethod
    def get_instance(cls, text_or_func, narrated_callable, *args, **kwargs):
        cdef NarrationFragment inst
        try:
            inst = cls._free_instances.pop()
            inst.__init__(text_or_func, narrated_callable, *args, **kwargs)
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
        cdef long ncid
        cdef str str
        self.text_or_func = text_or_func
        self.args = args
        self.kwargs = kwargs if kwargs else {}
        self.exception_text = None
        self.calling = None
        self.status = self.IN_PROCESS
        self.func_name = None
        self.source_file = None
        self.lineno = 0

    cpdef bint frame_describes_func(self, frame):
        """
        returns True if the supplied tuple from inspect.stack/trace matches the
        function and file name for this fragment
        :param frame:
        :return:
        """
        return self.func_name == frame[3] and self.source_file == frame[1]

    cpdef annotate_fragment(self, frame):
        """
        Extract relevant info from supplied FrameInfo object
        :param frame:
        :return:
        """
        self.lineno = frame[2]

    @classmethod
    def clone(cls, NarrationFragment src):
        cdef NarrationFragment new = cls(src.text_or_func, None,
                                         *src.args if src.args is not None else (),
                                         **src.kwargs if src.kwargs is not None else {})
        new.exception_text = src.exception_text
        new.calling = src.calling
        new.func_name = src.func_name
        new.source_file = src.source_file
        new.lineno = src.lineno
        return new

    cpdef str format(self, bint verbose=False):
        cdef str result
        cdef str tale = (self.text_or_func(*self.args, **self.kwargs)
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

    cpdef str tell(self, verbose=False):
        cdef str tale = self.format(verbose=verbose)
        return tale

    cpdef fragment_exception_text(self, etype, text):
        self.exception_text = "exception type: {}, value: '{}'".format(etype.__name__, text)


cdef inline bint _pop_until_found_calling(item):
    return item.calling == item


cdef class NarrationFragmentContextManager(NarrationFragment):
    _free_instances = deque()

    def __init__(self, *args, **kwargs):
        super(NarrationFragmentContextManager, self).__init__(*args, **kwargs)
        if _thread_fragments[current_thread().name].verbose:
            calling_frame = inspect.stack()[3]
            self.func_name = calling_frame[3]
            self.source_file = calling_frame[1]

    cpdef str format(self, bint verbose=False):
        cdef str tale = super(NarrationFragmentContextManager, self).format(verbose=verbose)
        cdef list parts = tale.split("\n")
        parts = [" " * (i + 2) + parts[i] for i in range(len(parts))]
        return "\n".join(parts)

    def __enter__(self):
        cdef str tname = current_thread().name
        _thread_fragments[tname].append(self)
        self.calling = self
        return self

    def __exit__(self, exc_type, exc_val, _):
        cdef str tname = current_thread().name
        d = _thread_fragments[tname]
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
                # so if verbose output is requested it can be included
                if d.verbose:
                    tb = inspect.trace()
                    stack = inspect.stack()
                    stack.reverse()
                    sc = deque(stack + tb)  # NOTE: slightly different than for func decorators!
                    scpop = sc.pop
                    deck = deque(d)
                    deckpop = deck.pop
                    while deck and sc:
                        while sc and not deck[-1].frame_describes_func(sc[-1]):
                            scpop()
                        if sc:
                            deck[-1].annotate_fragment(sc[-1])
                            deckpop()
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
        cdef str func_name=m.__name__, source_file=inspect.getsourcefile(m)
        def narrate_it(*args, **kwargs):
            global current_thread
            cdef NarrationFragment fragment = NarrationFragment.get_instance(str_or_func, m, *args, **kwargs)
            fragment.func_name = func_name
            fragment.source_file = source_file
            fragment.calling = m
            frag_deque = _thread_fragments[current_thread().name]
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
                    if frag_deque.verbose:
                        tb = inspect.trace()
                        stack = inspect.stack()
                        stack.reverse()
                        sc = deque(stack + tb[1:])
                        scpop = sc.pop
                        deck = deque(frag_deque)
                        deckpop = deck.pop
                        while deck and sc:
                            while sc and not deck[-1].frame_describes_func(sc[-1]):
                                scpop()
                            if sc:
                                deck[-1].annotate_fragment(sc[-1])
                                deckpop()
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


cpdef list get_narration(thread=None, bint from_here=False):
    """
    Return a list of strings, each one a narration fragment in the function call path.

    This method tells the tale of an exception; it returns a list of strings that are the narration fragments
    from each function/method call or context where narration has been captured. It starts at the most global level
    and goes to the level where the exception was raised.

    :param thread: instance of Thread. If not supplied, the current thread is used.
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
    cdef list l
    cdef bint verbose
    if thread is None:
        thread = current_thread()
    elif not isinstance(thread, Thread):
        raise ErratorException("the 'thread' argument isn't an instance of Thread: {}".format(thread))
    d = _thread_fragments.get(thread.name)
    if not d:
        l = list()
    else:
        verbose = d.verbose
        if not from_here:
            l = [nf.tell(verbose=verbose) for nf in d]
        else:
            # collect from the last IN_PROCESS fragment to the exception
            l = list()
            lappend = l.append
            for i in range(-1, -1 * len(d) - 1, -1):
                if d[i].status == NarrationFragment.IN_PROCESS:
                    for j in range(i, 0, 1):
                        lappend(d[j].tell(verbose=verbose))
                    break
    return l
