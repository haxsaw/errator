#############
Using Errator
#############

#. `If you don't read anything else, READ THIS <#if-you-don-t-read-anything-else-read-this>`__
#. `Errator's operation <#errator-s-operation>`__
#. `Capturing the narration <#capturing-the-narration>`__
#. `Skipping decorating functions <#skipping-decorating-functions>`__
#. `Customizing the narration <#customizing-the-narration>`__
#. `Getting more details with contexts <#getting-more-details-with-contexts>`__
#. `Advanced fragment access <#advanced-fragment-access>`__
#. `Verbose narrations <#verbose-narrations>`__
#. `Testing and debugging <#testing-and-debugging>`__
#. `Tidying up stack traces <#tidying-up-stack-traces>`__
#. `Usage tips <#usage-tips>`__

Errator is a fairly small library (one file) that's easy to wrap your head around. While basic
usage is fairly simple, errator also allows you more sophisticated uses in multi-threaded
programs where each thread can have its own exception narration, as well as being able to
manage partial narrations.

There are a couple of anti-patterns in errator's use which are important to understand, so
we'll lead off with addressing those before launching into a more general discussion on using
errator.

.. note::

    The documentation generally discusses decorating functions with errator, but errator's
    decorators can also
    be used to decorate methods. For brevity, when 'function' is used it should be assumed to
    mean 'function or method'.

If you don't read anything else, READ THIS
------------------------------------------

Errator decorators, context managers, and narration management functions work together to
manage a set of per-thread stacks of "narration fragments". In "normally" operating code (that is, with no
exceptions), these fragments are created at the start of a function or context, and discarded
when the function or context completes without an exception (push on call, pop on return).

But when an exception occurs, the fragment
is retained, and as the exception passes un-caught up the stack through other errator managed functions
or contexts, additional fragments may also be retained, until the exception is caught and errator
is told that it may finally discard the fragments. This discarding may be done automatically or
under programmatic control, depending on how errator is to be used, but the key is that unless errator
discards the fragments, they will simply keep growing in number and may cause memory issues if code
experiences numerous errors without disposing of the fragments, not to mention yielding confusing
narrations of exceptions.

There are two anti-patterns that can lead to this situation to be aware of.

--------------------------------------------------------------------------------------------
Anti-pattern #1-- catching the exception outside of errator's view
--------------------------------------------------------------------------------------------

If you catch an exception in a function that hasn't been decorated with errator decorators (and there are no more
errator-decorated functions or contexts at a more global level in the call stack), it will leak narration
fragments and the narration will grow, making it useless:

.. code-block::

    def f1():
        "NOTE: not decorated with 'narrate()'"
        try:
            f2()
        except Exception as e:
            story = get_narration()
            # handle the exception

    @narrate("I starting to 'f2'")
    def f2():
        f3()

    @narrate("I've been asked to 'f3'")
    def f3():
        raise Exception("catch me!")

    # some time later...
    f1()

The problem is that f1() isn't decorated with ``narrate()``, and hence errator doesn't know that
the exception was handled. Try it-- enter the above code and call f1() twice, and then look at the
returned narration from ``get_narration()``. **Remember**: this isn't a problem if there is an
errator decorated function or context at a more global level in the call stack.

You can fix this a couple of ways:

**Approach #1:**

.. code-block::

    # this approach will cause errator to automatically clean fragments:

    @narrate("I'm starting f1")  # we added decoration to the ``f1()`` function
    def f1():
        "NOTE: NOW decorated with 'narrate()'"
        try:
            f2()
        except Exception as e:
            story = get_narration()
            # handle the exception

    @narrate("I starting to 'f2'")
    def f2():
        f3()

    @narrate("I've been asked to 'f3'")
    def f3():
        raise Exception("catch me!")

    # some time later...
    f1()

**Approach #2**

.. code-block::

    # in this approach, you manually clear out the narration fragments

    def f1():
        "NOTE: no decoration, but we clean up in the exception clause"
        try:
            f2()
        except Exception as e:
            story = get_narration()
            reset_narration()  # CLEANS UP FRAGMENTS
            # handle the exception

    @narrate("I starting to 'f2'")
    def f2():
        f3()

    @narrate("I've been asked to 'f3'")
    def f3():
        raise Exception("catch me!")

    # some time later...
    f1()

-----------------------------------------------------------------------------
Anti-pattern #2: Shutting off automatic cleanup but not clearing up fragments
-----------------------------------------------------------------------------

For more complex uses of errator, you can turn off automatic fragment cleanup, but if
you do so then you **must** handle cleanup yourself. The following will suffer from the same
leakage/growing narration as the first anti-pattern:

.. code-block::

    @narrate("Look out-- I'm about to f1()!")
    def f1():
        "we've got f1 decorated"
        try:
            f2()
        except Exception as e:
            story = get_narration()
            # handle the exception

    @narrate("I starting to 'f2'")
    def f2():
        f3()

    @narrate("I've been asked to 'f3'")
    def f3():
        raise Exception("catch me!")

    set_narration_options(auto_prune=False)

    # later, in the same thread:
    f1()

In this example, even though all functions in the call chain are decorated with ``narrate()``,
we'll still leak fragements and allow the narration to grow. This is because
``set_narration_options()`` was used to turn off "auto_prune", which makes errator not discard
fragments when exceptions have been handled. Note that this has to happen in the same thread;
each thread can have different narration options.

If you want to have auto_prune off (and there are cases where you might want to do this), fixing
this is like the second solution to the first anti-pattern:

.. code-block::

    @narrate("Look out-- I'm about to f1()!")
    def f1():
        "we've got f1 decorated"
        try:
            f2()
        except Exception as e:
            story = get_narration()
            reset_narration()         #CLEANS UP THE FRAGMENTS
            # handle the exception

    @narrate("I starting to 'f2'")
    def f2():
        f3()

    @narrate("I've been asked to 'f3'")
    def f3():
        raise Exception("catch me!")

    set_narration_options(auto_prune=False)

    # later, in the same thread:
    f1()

Here, we've simply called ``reset_narration()`` after the narration text has been acquired, and
this gets rid of all fragments for the thread.

Errator's Operation
-------------------

Let's look at an example of a set of functions that can be decorated with errator's
``narrate()`` decorator. Let's suppose we have a set of functions ``f1`` through ``f6``, where
``f1`` calls ``f2``, ``f2`` calls ``f3``, and so forth. If we stopped in the debugger in ``f6``, Python
would report the stack like so:

+-------+------------------+
|  func |  execution point |
+=======+==================+
|    f1 |                  |
+-------+------------------+
|    f2 |                  |
+-------+------------------+
|    f3 |                  |
+-------+------------------+
|    f4 |                  |
+-------+------------------+
|    f5 |                  |
+-------+------------------+
|    f6 | <-- current frame|
+-------+------------------+

When we decorate functions with ``narrate()``, additional stack frames are added to
the trace; we won't show those here, but instead will show what fragments are managed
as the execution progresses. Here's the retained narration fragments if ``f1..f6`` are all decorated with
``narrate()`` and the current function is ``f4``:

+-------+------------------+---------------------+
|  func |  execution point | fragments for funcs |
+=======+==================+=====================+
|    f1 |                  |                     |
+-------+------------------+---------------------+
|    f2 |                  |                     |
+-------+------------------+---------------------+
|    f3 |                  |                     |
+-------+------------------+---------------------+
|    f4 | <-- current frame| f1, f2, f3, f4      |
+-------+------------------+---------------------+
|    f5 |                  |                     |
+-------+------------------+---------------------+
|    f6 |                  |                     |
+-------+------------------+---------------------+

When ``f4`` returns, the fragments are:

+-------+------------------+---------------------+
|  func |  execution point | fragments for funcs |
+=======+==================+=====================+
|    f1 |                  |                     |
+-------+------------------+---------------------+
|    f2 |                  |                     |
+-------+------------------+---------------------+
|    f3 | <-- current frame| f1, f2, f3          |
+-------+------------------+---------------------+
|    f4 |                  |                     |
+-------+------------------+---------------------+
|    f5 |                  |                     |
+-------+------------------+---------------------+
|    f6 |                  |                     |
+-------+------------------+---------------------+

Note that the fragment for ``f4`` is removed.

Now suppose that we have an exception in
``f6``, but the exception isn't captured until ``f3``, at which point the exception is caught and
doesn't propagate up the stack any further. This next table shows the
fragments present as the functions either return and the exception propagates upward:

+-------+------------------+---------------------+
|  func |  execution point | fragments for funcs |
+=======+==================+=====================+
|    f1 | normal return    | f1                  |
+-------+------------------+---------------------+
|    f2 | normal return    | f1,f2               |
+-------+------------------+---------------------+
|    f3 | exc handled      | f1,f2,f3,f4,f5,f6   |
+-------+------------------+---------------------+
|    f4 | exc passes thru  | f1,f2,f3,f4,f5,f6   |
+-------+------------------+---------------------+
|    f5 | exc passes thru  | f1,f2,f3,f4,f5,f6   |
+-------+------------------+---------------------+
|    f6 | exception raised | f1,f2,f3,f4,f5,f6   |
+-------+------------------+---------------------+

Notice that in ``f3`` where the exception is handled we still have all the fragments for all
stack frames between the exception origin and the handler, but once the handler returns and
errator sees that the exception isn't propagating further it removes the fragments that are
no longer useful in narrating an exception (this makes ``f3`` a good place to acquire the
narration for the exception; more on that later).

Capturing the narration
-----------------------

Let's repeat the example from earlier, where we said that a function caught an exception and
processed it in ``f3``:

+-------+------------------+---------------------+
|  func |  execution point | fragments for funcs |
+=======+==================+=====================+
|    f1 | normal return    | f1                  |
+-------+------------------+---------------------+
|    f2 | normal return    | f1,f2               |
+-------+------------------+---------------------+
|    f3 | exc handled      | f1,f2,f3,f4,f5,f6   |
+-------+------------------+---------------------+
|    f4 | exc passes thru  | f1,f2,f3,f4,f5,f6   |
+-------+------------------+---------------------+
|    f5 | exc passes thru  | f1,f2,f3,f4,f5,f6   |
+-------+------------------+---------------------+
|    f6 | exception raised | f1,f2,f3,f4,f5,f6   |
+-------+------------------+---------------------+

If ``f3`` catches the exception, it's probably a good place to grab the exception narration
(this isn't required, but it may be a natural place). Suppose ``f3()`` looks like the following:

.. code-block::

    @narrate("While I was running f3")
    def f3():
        try:
            f4()
        except MyException:
            story = get_narration()

In the ``except`` clause, we call ``get_narration()`` to acquire a list of strings that are
the narration for the exception. This will return the entire narration that exists for this
call stack; that is, it will give a list of narration fragment strings for ``f1()`` through ``f6()``.

But perhaps the whole narration isn't wanted; perhaps all that's desired is the narration for
``f3()`` through ``f6()``, as the the narrations before this point actually make the exception narration less
clear. You can trim your narration down with by calling ``get_narration()`` with the keyword
argument ``from_here`` set to True:

.. code-block::

    @narrate("While I was running f3...")
    def f3():
        try:
            f4()
        except MyException:
            story = get_narration(from_here=True)

This will only return the narration strings from the current function to the function that's
the source of the exception, in this case ``f3()`` through ``f6()``. The ``from_here`` argument allows
you to control how much narration is returned from ``get_narration()``. It defaults to False,
meaning to return the entire narration.

Skipping decorating functions
-----------------------------

What happens if you skip decorating some functions in a calling sequence? Nothing much;
errator simply won't have anything in it's narration for that function. Below, we indicate a
decorated function with an ``(e)`` before the function name, and skip decoration of some
functions. When we get to ``f5``, the captured fragments are as shown:

+-------+------------------+---------------------+
|  func |  execution point | fragments for funcs |
+=======+==================+=====================+
| (e)f1 |                  | f1                  |
+-------+------------------+---------------------+
| (e)f2 |                  | f1,f2               |
+-------+------------------+---------------------+
|    f3 |                  | f1,f2               |
+-------+------------------+---------------------+
| (e)f4 |                  | f1,f2,f4            |
+-------+------------------+---------------------+
|    f5 | <-- current frame| f1,f2,f4            |
+-------+------------------+---------------------+
|    f6 |                  |                     |
+-------+------------------+---------------------+

Customizing the narration
-------------------------

Suppose you have a function of several variables:

.. code-block::

    @narrate("While I was calling f...")
    def f(x, y):
        # do stuff

And a narration with a fixed string doesn't give you enough information as to how the
function was called if there was an exception. The ``narrate()`` function allows you to supply it
with a callable object instead of a string; this callable will be passed all the arguments
that were passed to
the function and must return a string, which will then be used as the descriptive string for
the narration fragment. This function is **only** invoked if the decorated function raises
an exception, otherwise it goes uncalled.

Lambdas provide a nice way to specify a function that yields a string:

.. code-block::

    @narrate(lambda a, b: "While I was calling f with x={} and y={}...".format(a, b))
    def f(x, y):
        # do stuff

But you can supply any callable that can cope with the argument list to the decorated
function. This allows your narrations to provide more details regarding the calling context
of a particular function, since actual argument values can become part of the narration.

Getting more details with contexts
----------------------------------

It may be the case that narration at the function level isn't granular enough.
You may have a lengthy function or one that calls out to other libraries, each of which
can raise exceptions of their own. You might be helpful to have narration capabilities
at a more granular level to address this.

To support more granular narration, errator provides a context manager that is created with
a call to ``narrate_cm()``. This context manager acts similarly to the ``narrate()``
decorator. First, a narration fragment is captured when the context is entered. If the context
exits "normally" the fragment is discarded. However, if an exception is raised during the
context, the fragment is retained as the exception propagates upward.

Suppose we have a function that does two web service calls during its execution,
and we'd like to know narration details around each of these activities if any fails in our
function. We can use ``narrate_cm()`` to achieve this:

.. code-block::

    @narrate(lambda a, b:"So call_em was invoked with x={} and y={}".format(a, b))
    def call_em(x, y):
        # do some stuff to form the first WS call
        with narrate_cm("...and I started the first web service call..."):
            # do the web service call

        # extract data and do the second call, computing a string named ws2_req
        with narrate_cm(lambda req: "...I started WS call #2 call with {}".format(req), ws2_req):
            # do the second web service call

        # and whatever else...

This example was constructed to illustrate a couple of uses. Similarly to ``narrate()``, ``narrate_cm()``
can be called either with a fixed string, or a callable that returns a string which will be invoked
only if there's an exception raised in the context.

The first use of ``narrate_cm()`` simply passes a fixed string. If there's an exception during the first
web service call, the string is retained, but when reported the string will be indented a few spaces to
show that the narration fragment is within the scope of the function's narration.

The second use of ``narrate_cm()`` passes a lambda as its callable. But unlike passing a callable to
``narrate()``, you must also supply the arguments to give the callable to ``narrate_cm()``, in this
case the local variable ws2_req. This is because the context manager doesn't know what is import relative
to the context-- the function arguments or the local variables. You may pass both postional and keyword
arguments to ``narrate_cm()``.

Advanced fragment access
------------------------

Errator provides a way to get copies of the actual objects where narration fragments are stored. There are
a number of situations where this is useful:

- if more control over fragment formatting is required
- if retention of the details of an error narration is required
- you're just that way

You can get these objects by using the ``copy_narration()`` function. Instead of returning a list of strings
like ``get_narration()`` does, this function returns a list of ``NarrationFragment``
objects which are copies of the
objects managed by errator itself. The ``copy_narration()`` function takes the same ``thread`` and
``from_here`` arguments as does ``get_narration()``, so you can control what objects are returned in
the same manner. Useful methods on NarrationFragment objects are:

- ``tell()``, which returns a string that is the fragment's part of the overall narration
- ``tell_ex()``, similar to ``tell()`` but provides more contextual information (not fully implemented)
- ``fragment_exception_text()``, which returns a string that describes the actual exception; really
  only useful on the last fragment in the call chain

Being a lower-level object, you should expect the rest of NarrationFragment's interface to be a bit more volatile,
and should stick with calling ``tell()`` if you wish to be isolated from change.

Verbose narrations
------------------

The story errator tells is meant to be user-focused; that is, from the perspective of a program's semantics rather than from that of a stack trace. However, there may be circumstances where it would be helpful to have some of the information in a stack trace merged into the rendered narration. Errator supports this with the ``verbose`` keyword on the ``get_narration()`` function. It defaults to ``False``, but if set to ``True``, then each retrieved narration line will be followed by a line that reports the line number, function, and source file associated with the narration fragment.

Consider this narrated program in a file named verbose.py:

.. code-block::

    from errator import narrate_cm, narrate, get_narration

    @narrate("So I started to 'f1'...")
    def f1():
        f2()

    @narrate("...which occasioned me to 'f2'")
    def f2():
        with narrate_cm("during which I started a narration context..."):
            f3()

    @narrate("...and that led me to finally 'f3'")
    def f3():
        raise Exception("oops")

    if __name__ == "__main__":
        try:
            f1()
        except:
            for l in get_narration(verbose=False):
                print(l)

Which yields the following output when run:

.. code-block::

    So I started to 'f1'...
    ...which occasioned me to 'f2'
      during which I started a narration context...
    ...and that led me to finally 'f3', but exception type: Exception, value: 'oops' was raised

If we set ``verbose=True`` in the ``get_narration()`` call, then the output looks like the following:

.. code-block::

    So I started to 'f1'...
        line 5 in f1, /home/tom/errator/docs/verbose.py
    ...which occasioned me to 'f2'
        line 10 in f2, /home/tom/errator/docs/verbose.py
      during which I started a narration context...
           line 10 in f2, /home/tom/errator/docs/verbose.py
    ...and that led me to finally 'f3', but exception type: Exception, value: 'oops' was raised
        line 14 in f3, /home/tom/errator/docs/verbose.py

...thus letting you see the actual lines being executed when the exception is raised.

Testing and debugging
---------------------

As errator is meant to help you make sense when something goes wrong, it would be a shame if something
went wrong while errator was doing its thing. But since errator users can supply a callable to ``narrate()``
and ``narrate_cm()``, there's the possibility that an error lurks in the callable itself, and errator could raise
an exception in trying to tell you about an exception. Worse, if there is a bug in a callable, you'd only know
about it if an exception is raised, which may be difficult to force in testing, or may escape testing and only
show up in production.

To help you find problems earlier, errator provides an option that changes the rules regarding when fragments,
and hence callables, are formatted. By adding:

.. code-block::

    set_default_options(check=True)

Before entering an errator decorated function or managed context, you inform errator that you wish to
check the generation of every narration fragment, whether there's been an exception raised or not. You can
also set the 'check' option on an existing narration's thread with:

.. code-block::

    set_narration_options(check=True)

which will set fragment checking only for the current thread's narration (or the thread named with the ``thread=``
argument; see the documentation for ``set_narration_options()`` for details).

When the ``check`` option is True, every time a decorated function returns or a managed context exits, errator
formats the narration fragment, including calling any callable supplied to exercise the code it refers to.
By setting check to True in your testing code, you can be sure that every narration fragment is generated,
and hence every callable for a fragment is invoked. This helps you ensure that you have the correct number of
arguments to your callable and raises confidence that the callable will operate correctly in a real exception
situation (this isn't a guarantee, however, as the conditions that raise an exception my be different from
those in testing).

.. note::

    You don't want to run production code with ``check`` set to True (it defaults to False). This is because
    doing so incurs the execution time of every callable where the check==True applies, which can have
    significant performance impact on your code. Errator normally only invokes the callable if there's an
    exception, thus sparing your code from the call overhead and extra execution time. So be sure not have
    the check option set True in production.

Tidying up stack traces
-----------------------

Errator's ``narrate()`` decorator wraps the function being decorated, which means that if you use the various stack
and traceback reporting functions in the standard ``traceback`` module, you can get materially longer traces than
you'd otherwise like. If you'd rather not see these, errator supplies a set of wrapper functions that are analogs of
the functions in ``traceback`` that strip out the errator calls from returned objects or printed stack traces. These
functions are all argument-compatible with the functions in ``traceback``. Specifically, errator provides analogs to:

- extract_tb
- extract_stack
- format_tb
- format_stack
- format_exception_only
- format_exception
- print_tb
- print_exception
- print_exc
- format_exc
- print_last
- print_stack

...all of which remove traces of errator from the output.

Usage tips
----------

* When decorating a method with ``narrate()`` and supplying a callable, don't forget to include the ``self`` argument
  in the callable's argument list.

* Decorating generator functions gives unexpected results; the function will return immediately with the
  generator as the value, hence the narration fragment will not be retained. If you wish to get narration for
  generator functions, you need to use the ``narrate_cm()`` context manager within the generator to accomplish this.

* At the moment, behavior with coroutines has not been investigated, but almost certainly the current release
  will do surprising things. This will need further investigation.

