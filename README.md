Errator
=======

Provide human-readable error narration of exception tracebacks with
Errator.

1. [Intro](#intro)
2. [How it works](#howitworks)
3. [Requirements](#reqs)
2. [Installing](#installing)
5. [Quick Start](#quickstart)

## <a name="intro">Intro</a>

Errator came as an idea on the back of trying to figure out what the meaning of an exception traceback is in non-trivial pieces of code.

When an exception occurs deep inside a call stack within some generic
utility function that is used in numerous contexts, reading the traceback
is often not helpful in determine the source of the problem. Data values
aren't obvious, and the initial starting conditions of the error can't
easily been seen.

Logging is a step in the right direction, but in general outputs too much
information; often, there is lots of info regarding error-free processing
in the log, making it hard to find the right log output that is associated
with the error.

Errator is something of a marriage between logging and tracebacks: plain text messages that are associated
directly with the call trail that led to an exception. Errator works by providing tools that let you state intent
of code in text, but only captures that text when an exception bubbles up
up the stack. You can then acquire this "error narration" and display it
to your user in the most appropriate fashion.

## <a name="howitworks">How it works</a>
Errator uses decorators and context managers to maintain a stack of "narration fragments"
behind the scenes. When code executes without exceptions, these fragments
are created and thrown away as narrated code executes and returns. However, when an exception
is raised, the narration fragments are retained and their content can be
retrieved. Fragments can be automatically discarded (pruned) when an
exception doesn't propagate any further up the stack, or can be discarded
under user control, allowing more control over the content of "narration" provided
for the exception.

## <a name="reqs">Requirements</a>
Errator doesn't have any external dependencies. It is compatible with
Python 2 and 3.

## <a name="installing">Installing</a>
Errator is a single file, and can be installed either with pip or running
'python setup.py install' after pulling the Git project.

## <a name="quickstart">Quick Start</a>
Then next section discusses Errator with functions, but you can also use it the decorators
described with methods, too.

Start with pulling errator into your module that you want to narrate:

```python
from errator import *
```

Now, suppose you have a utility function that performs some specialized string formatting,
but it is possible to pass in arguments that cause a exception to be raised.
Your function is called all over the place for a variety of different reasons,
often very deep down the call stack where it isn't obvious what the original
functional intent was, or where the source of bad arguments may have been.

To start building the narration to your function's execution, you can use the 'narrate'
decorator to associate a bit of text with your utility function to provide easily understandable
explanations about what's going on:

```python
@narrate("I'm trying to format a string")
def special_formatter(fmt_string, **kwargs):
    # magic format code that sometimes raises an exception
```

The 'narrate()' decorator knows to look for exceptions and doesn't impede their propagation,
but captures that bit of text in an internal stack when an exception occurs. So if you
write:

```python
try:
    s = special_formatter(fmt, **args)
exception Exception:
    the_tale = get_narration_text()
```

...and special_formatter() raises an exception, the exception will still bubble up the stack,
but get_narration_text() will return a list of strings for all the narrate()
decorated functions down to the exception. If no exception is raised, there
are no strings (well, it's a little more complicated than that, but we'll
get to that).

Maybe you'd like some insight as to the arguments present when an exception is raised so
you can better tell what's causing it. Instead of a string, you can supply
the narrate() decorator with a callable that has the same signature as the function
being decorated. This callable will be invoked only if the decorated function raises
an exception, and gets invoked with the same arguments that the function was:

```python
@narrate(lambda fs, **kw: "I'm trying to format a string with '%s' and args '%s'" % (fs, str(kw)))
def special_formatter(fmt_string, **kwargs):
    # magic format code that sometimes raises an exception

```

The lambda passed to narrate() will only be called when special_formatter()
raises an exception, otherwise it will go un-executed.

Now, perhaps special_formatter() is a rather long function, and you'd like
to be able to narrate it's operation in more detail to get better narrations
when things go wrong. You can use the narrate_cm() context manager to create a narration fragment for
a block of code. If everything goes well in the block, then the fragment is discarded, but
the fragment will be retained if an exception occurs:

```python
def special_formatter(fmt_string, **kwargs):
    for format_token in parse_format(fmt_string):
        if format_token.type == float:
            with narrate_cm("I started processing a float format"):
                # do magic stuff for floats...
        elif format_token.type == int:
            with narrate_cm("I started processing an int format"):
                # do magic stuff for ints...
```

Narration fragments added with narrate_cm() are treated just like those created by
the function decorator-- they are added to the stack, and silently removed if
the context manager's code block exits normally. But exceptions raised in the
context block are retained as the exception propagates back through the stack.

Like narrate(), narrate_cm() allows you to supply a callable instead of a string:

```python
with narrate_cm(lambda x: "I started processing an int with format %s" % x, format_token.format):
    # format code
```

...and again, this callable will only be invoked if an exception is raised in the context. Unlike
narrate(), however, you are free to define a callable with any signature, as long as you supply
the arguments needed as well to invoke the callable if need be.

Context managers may nest, and in fact any combination of function decorator and context manager
will work as expected.