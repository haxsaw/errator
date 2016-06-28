Errator
=======

Provide human-readable error narration of exception tracebacks with
Errator.

1. [Intro](#intro)
2. [How it works](#howitworks)
3. [Requirements](#reqs)
2. [Installing](#installing)
5. [Quick Tutorial](#quickstart)

## <a name="intro">Intro</a>

Errator came as an idea on the back of trying to figure out what the meaning
of an exception traceback is in non-trivial pieces of code.

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
of code in text, but only captures that text when an exception bubbles
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

Errator is thread-safe, allowing you to capture separate error narrations for independent
threads of control through the same code.

## <a name="reqs">Requirements</a>
Errator doesn't have any external dependencies. It is compatible with
Python 2.7 and 3.x.

## <a name="installing">Installing</a>
Errator is a single file, and can be installed either with pip or running
'python setup.py install' after pulling the Git project.

## <a name="quickstart">Quick Tutorial</a>
The next section discusses Errator with functions, but you can also use the decorators
described with methods too.

Start with pulling errator into your module that you want to narrate:

```python
from errator import *
```

Now, suppose you have a utility function that performs some specialized string formatting,
but it is possible to pass in arguments that cause a exception to be raised.
Your function is called all over the place for a variety of different reasons,
often very deep down the call stack where it isn't obvious what the original
functional intent was, or where the source of bad arguments may have been.

To start building the narration to your function's execution, you can use the narrate()
decorator to associate a bit of text with your utility function to provide easily understandable
explanations about what's going on:

```python
@narrate("I'm trying to format a string")
def special_formatter(fmt_string, **kwargs):
    # magic format code that sometimes raises an exception
```

The narrate() decorator knows to look for exceptions and doesn't impede their propagation,
but captures that bit of text in an internal stack when an exception occurs. So if you
write:

```python
try:
    s = special_formatter(fmt, **args)
exception Exception:
    the_tale = get_narration()
```

...and special_formatter() raises an exception, the exception will still bubble up the stack,
but get_narration() will return a list of strings for all the narrate()
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

Let's look at an example with more complex calling relationships. Suppose we have functions
A, B, C, D, E, and F. They have the following calling relationships:

<verbatim>
A calls B and C
B calls D
C calls E or F
D calls F
</verbatim>

We'll make it so that if we're unlucky enough to call E, we'll get an exception raised.
This will happen only for input values of A greater than 10.

So let's define these functions and narrate them-- paste these into an interactive
Python session after you've imported errator:

```python
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
```

Now run A with a value less than 11, and look for narration text:

```python
>>> A(3)
very well
very well
>>> get_narration()
[]
>>> 
```

Now run A with a value greater than 10:

```python
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
```

So far, it's as we'd expect, except perhaps for the inclusion of errator calls in the stack.
But now let's look at the narration:

```python
>>> for l in get_narration():
...     print(l)
... 
I'm trying to A with 11 as input
I'm trying to C with 22 as input
I'm trying to E with 22 as input, but exception type: ValueError, value: how dare you call me with such a value? was raised
>>> 
```

We have a narration for our recent exception. Now try the following:

```python
>>> A(8)
very well
very well
>>> get_narration()
["I'm trying to A with 11 as input", "I'm trying to C with 22 as input", # etc...
```

Wait, this didn't have an exception; why is there still narration? This is because
an error narration only gets cleared out if a decorated function does NOT
have an exception bubble up; the assumption is that the exception was
caught and the narration was retrieved, so a decorated function that returns
normally would remove the previous narration fragments. In our example, there is
no function that is decorated with narrate() that catches the exception and
returns normally, so the narration never clears out.

There are a few ways to clear unwanted narrations: first is to manually clear the
narration, and the other is to make sure you have a decorated
function that catches the exception and returns normally, which will clear
the narration automatically

To manually clear narrations we call reset_narration():

```python
>>> reset_narration()
>>> get_narration()
>>> []
```

For the second, if we define a decorated function that calls A but which handles
the exception and returns normally, the narration fragments will be cleaned
up automatically:

```python
@narrate("Handler for A")
def first(val):
    try:
        A(val)
    except:
        print("Got %d narration lines" % len(get_narration()))
```

This outermost function still can retrieve the narration, but as it returns normally,
the narration is cleared out when it returns:

```python
>>> first(11)
very well
Got 4 narration lines
>>> get_narration()
[]
>>> 
```

Errator provides finer degrees of control for getting the narration; these are 
covered in the detailed docs.