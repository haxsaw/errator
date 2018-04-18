errator
=======

Provide human-readable error narration of exception tracebacks with ``errator``.

#. `What's new in 0.3 <#what-s-new-in-0-3>`__
#. `Intro <#intro>`__
#. `How it works <#how-it-works>`__
#. `Requirements <#requirements>`__
#. `Installing <#installing>`__
#. `Quick Start <#quick-start>`__
#. `Building from source <#building-from-source>`__

What's new in 0.3
-----------------
This is largely a performance release for ``errator``, as it implements the more costly part of the narration process in a `Cython <http://cython.org/>`__ extension. Additionally, there has been a change in the way verbose narrations are performed, as the original approach entailed a lot of overhead even if verbose narrations weren't required.

- ``errator`` now consists of a Python file and a  Python extension module (built from a Cython source), which improves runtime performance

- The 'verbose' keyword argument has been removed from the ``get_narration()`` function, and has been added to the ``set_narration_options()`` and ``set_default_options()`` functions. Now getting verbose narrations is a matter of setting the option either as a default or on a per-thread basis, hence this option must be set `before` collecting narrations.

- Previously, detailed exception information (file name, line number) was always collected in case a user wanted to fetch verbose narration information with ``get_narration()``. However, this proved to be a big performance hit, and now this information is `only` collected if the 'verbose' option has been set with ``set_narration_options()`` or ``set_default_options()`` function `before` the exception occurs.

What's new in 0.2.1
-------------------

This patch release addresses certain performance issues:

- Patched a bug that caused too many object creations to occur

- Removed some redundant resetting of state in narration fragment objects

- Added caching of filenames for function objects so that lookups aren't always required

- Sped up the resetting process


What's new in 0.2
-----------------

- The ``get_narration()`` now has a new keyword argument, "verbose" (default False), that when True returns expanded narration information that includes the line number, function, and file name of the point in the stack trace that the narration applies to.

- To provide a more tidy display of stack information, ``errator`` now has analogs of the functions from the standard ``traceback`` module that filter out ``errator``-based calls from the call stack, leaving only application calls in the display of stack traces.

- Narration output formatting has been modified slightly.

Intro
-----

``errator`` came as an idea on the back of trying to figure out what the semantics of an exception traceback are in non-trivial pieces of code.

When an exception occurs deep inside a call stack within some generic utility function that is used in numerous contexts, reading the traceback is often not helpful in determining the source of the problem. Data values aren't obvious, and the initial starting conditions of the error can't easily been seen.

Logging is a step in the right direction, but in general outputs too much information; often, there is lots of info regarding error-free processing in the log, making it hard to find the right log output that is associated with the error.

``errator`` is something of a marriage between logging and tracebacks: plain text messages that are associated directly with the call trail that led to an exception. ``errator`` works by providing tools that let you state intent of code in text, but only captures that text when an exception bubbles up the stack. You can then acquire this "error narration" and display it to your user in the most appropriate fashion.

How it works
------------

``errator`` uses decorators and context managers to maintain a stack of "narration fragments" behind the scenes. When code executes without exceptions, these fragments are created and thrown away as narrated code executes and returns. However, when an exception is raised, the narration fragments are retained and their content can be retrieved. Fragments can be automatically discarded (pruned) when an exception doesn't propagate any further up the stack, or can be discarded under user control, allowing more control over the content of "narration" provided for the exception.

``errator`` is thread-safe, allowing you to capture separate error narrations for independent threads of control through the same code.

Requirements
------------

``errator`` doesn't have any runtime external dependencies, and is compatible with Python 2.7 and 3.x. If you wish to build from source, you'll need to install Cython to build the extension module, and have a C compiler and the required Python header files.

Installing
----------

As of 0.3, ``errator`` is comprised of a Python module and an extension wrapper. You can install it with ``pip install errator``, or you can clone the Git project and build from source (more on this below).

Quick Start
-----------

The next section discusses ``errator`` with functions, but you can also use the decorators described with methods too.

**Basic Use**

Start by importing ``errator`` into the module that you want to narrate:

.. code:: python

    from errator import *

Now, suppose you have a utility function that performs some specialized string formatting, but it is possible to pass in arguments that cause a exception to be raised. Your function is called all over the place for a variety of different reasons, often very deep down the call stack where it isn't obvious what the original functional intent was, or where the source of bad arguments may have been.

To start building the narration to your function's execution, you can use the ``narrate()`` decorator to associate a bit of text with your utility function in order to provide easily understandable explanations about what's going on:

.. code:: python

    @narrate("I'm trying to format a string")
    def special_formatter(fmt_string, **kwargs):
        # magic format code that sometimes raises an exception

The ``narrate()`` decorator knows to look for exceptions and doesn't impede their propagation, but captures that bit of text in an internal stack when an exception occurs. So if you write:

.. code:: python

    try:
        s = special_formatter(fmt, **args)
    exception Exception:
        the_tale = get_narration()

...and ``special_formatter()`` raises an exception, the exception will still bubble up the stack, but ``get_narration()`` will return a list of strings for all the ``narrate()``-decorated functions down to the exception. If no exception is raised, there are no strings to fetch (unless you want there to be strings, but we'll get to that).

**Getting more information**

Maybe you'd like some insight as to the value of the arguments passed when an exception is raised, so you can better tell what's causing it. Instead of a string, you can supply the ``narrate()`` decorator with a callable that returns a string and that has the same signature as the function being decorated. This callable will `only be invoked if the decorated function raises an exception`, and gets invoked with the same arguments as the function:

.. code:: python

    @narrate(lambda fs, **kw: "I'm trying to format a string with '%s' and args '%s'" % (fs, str(kw)))
    def special_formatter(fmt_string, **kwargs):
        # magic format code that sometimes raises an exception

The lambda passed to narrate() will only be called when ``special_formatter()`` raises an exception, otherwise it will go un-executed.

**Finer details with contexts**

Now, perhaps ``special_formatter()`` is a rather long function, and you'd like to be able to narrate it's operation in more detail to get better narrations when things go wrong. You can use the ``narrate_cm()`` context manager to create a narration fragment for a block of code. If everything goes well in the block, then the fragment is discarded, but the fragment will be retained if an exception occurs:

.. code:: python

    def special_formatter(fmt_string, **kwargs):
        for format_token in parse_format(fmt_string):
            if format_token.type == float:
                with narrate_cm("I started processing a float format"):
                    # do magic stuff for floats...
            elif format_token.type == int:
                with narrate_cm("I started processing an int format"):
                    # do magic stuff for ints...

Narration fragments added with ``narrate_cm()`` are treated just like those created by the function decorator-- they are added to the stack, and silently removed if the context manager's code block exits normally. But exceptions raised in the context block are retained as the exception propagates back through the stack.

Like ``narrate()``, ``narrate\_cm()`` allows you to supply a callable instead of
a string:

.. code:: python

    with narrate_cm(lambda x: "I started processing an int with format %s" % x, format_token.format):
        # format code

...and again, this callable will only be invoked if an exception is raised in the context. Unlike ``narrate()``, however, you are free to define a callable with any signature, as long as you supply the arguments needed to invoke the callable if need be.

Context managers may nest, and in fact any combination of function decorator and context manager will work as expected.

**A larger example**

Let's look at an example with more complex calling relationships. Suppose we have functions ``A``, ``B``, ``C``, ``D``, ``E``, and ``F``. They have the following calling relationships:


* ``A`` calls ``B`` then ``C``
* ``B`` calls ``D``
* ``C`` calls ``E`` or ``F``
* ``D`` calls ``F``


We'll make it so that if we're unlucky enough to call ``E``, we'll get an exception raised. This will happen only for input values of ``A`` greater than 10.

So let's define these functions and narrate them-- paste these into an interactive Python session after you've imported ``errator``:

.. code:: python

    @narrate(lambda v: "I'm trying to A with %s as input" % v)
    def A(val):
        B(val / 2)
        C(val * 2)
        
    @narrate(lambda v: "I'm trying to B with %s as input" % v)
    def B(val):
        D(val * 10)
        
    @narrate(lambda v: "I'm trying to C with %s as input" % v)
    def C(val):
        if val > 20:
            E(val)
        else:
            F(val)
            
    @narrate(lambda v: "I'm trying to D with %s as input" % v)
    def D(val):
        F(val * 3)
        
    @narrate(lambda v: "I'm trying to E with %s as input" % v)
    def E(val):
        raise ValueError("how dare you call me with such a value?")
        
    @narrate(lambda v: "I'm trying to F with %s as input" % v)
    def F(val):
        print("very well")

Now run ``A`` with a value less than 11, and look for narration text:

.. code:: python

    >>> A(3)
    very well
    very well
    >>> get_narration()
    []
    >>> 

Since there was no exception, there are no narrations. Now run ``A`` with a value greater than 10, which will cause an exception in E:

.. code:: python

    >>> A(11)
    very well
    Traceback (most recent call last):
      File "<stdin>", line 1, in <module>
      File "errator.py", line 322, in callit
        _v = m(*args, **kwargs)
      File "<stdin>", line 4, in A
      File "errator.py", line 322, in callit
        _v = m(*args, **kwargs)
      File "<stdin>", line 4, in C
      File "errator.py", line 322, in callit
        _v = m(*args, **kwargs)
      File "<stdin>", line 3, in E
    ValueError: how dare you call me with such a value?
    >>> 

So far, it's as we'd expect, except perhaps for the inclusion of ``errator`` calls in the stack (``errator`` includes tools that allow you to get stack traces that have been cleaned of ``errator`` calls). But now let's look at the narration:

.. code::

    >>> for l in get_narration():
    ...     print(l)
    ... 
    I'm trying to A with 11 as input
    I'm trying to C with 22 as input
    I'm trying to E with 22 as input, but exception type: ValueError, value: how dare you call me with such a value? was raised
    >>> 

We have a narration for our recent exception. Now try the following:

.. code:: python

    >>> A(8)
    very well
    very well
    >>> get_narration()
    ["I'm trying to A with 11 as input", "I'm trying to C with 22 as input", # etc...

Wait, this didn't have an exception; why is there still error narration? This is because *an error narration only gets cleared out if a decorated function does NOT have an exception bubble up*; the assumption is that the exception was caught and the narration was retrieved, so a decorated function that returns normally would remove the previous narration fragments. In our example, there is no function that is decorated with ``narrate()`` that catches the exception and returns normally, so the narration never clears out.

There are a few ways to clear unwanted narrations: first is to manually clear the narration, and the other is to make sure you have a decorated function that catches the exception and returns normally, which will clear the narration automatically

To manually clear narrations we call ``reset_narration()``:

.. code:: python

    >>> reset_narration()
    >>> get_narration()
    >>> []

For the second, if we define a decorated function that calls A but which handles the exception and returns normally, the narration fragments will be cleaned up automatically:

.. code:: python

    @narrate("Handler for A")
    def first(val):
        try:
            A(val)
        except:
            print("Got %d narration lines" % len(get_narration()))

This outermost function still can retrieve the narration, but as it returns normally, the narration is cleared out when it returns:

.. code:: python

    >>> first(11)
    very well
    Got 4 narration lines
    >>> get_narration()
    []
    >>> 

``errator`` provides various narration options and finer degrees of control for retriving the narration; these are covered in the detailed docs. See the ``using_errator`` file in the docs directory.

Building from source
--------------------

``errator`` is built using Cython, however the source package contains the generated C file, so you only need:

- A C compiler
- Python header files for your version of Python

For development, in the project root, run the following command:

.. code::

    python setup.py build_ext --inplace

...This will create the shared library that is used by ``errator``. You can then do the normal ``python setup.py install`` dance to put the built distribution where you want it to go, or you can simply use it right from where you built it.

If you want to build a wheel, the command is:

.. code::

    python setup.py bdist_wheel

If you wish to build from the Cython pyx file, you'll need to grab the source from the Github repo and run the same commands as above; they will run Cython when appropriate.
