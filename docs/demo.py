"""
Demonstrate errator in multi-threaded apps

This example just shows how to acquire an error's narration and display it. It also shows how
a separate narration is kept for each thread, and how to display data passed to a function
or method in the case of an exception.
"""
import threading
from errator import narrate_cm, narrate, get_narration


# narrate the call to f2, using a lambda to show the arguments passed when an exception occurs
@narrate(lambda a3, a4:
         "...I was subsequently asked to f2 with {} and {}".format(a3, a4))
def f2(arg3, arg4):
    # use a narration context manager to wrap a block of code with narration
    with narrate_cm("...so I first started to do 'this'"):
        # all of my 'this' activities
        # which create variables x and y
        x = arg3 * 2
        y = arg4 * 3

    with narrate_cm(lambda: "...and then went on to do 'that' with x={} and y={}".format(x, y)):
        # all of my 'that' activities
        raise Exception("ruh-roh")


# narrate the call to f1, using a lambda to show the arguments passed when an exception occurs
@narrate(lambda a1, a2: "I was asked to f1 with {} and {}".format(a1, a2))
def f1(arg1, arg2):
    # do some things, then
    try:
        f2(arg1+1, arg2+1)
    except Exception as e:
        lines = ["My thread {}'s story:".format(
                 threading.current_thread().name)]
        lines.extend([s for s in get_narration()])
        print("\n".join(lines))
        print("")

t1 = threading.Thread(target=f1, args=(1, 2), name="t1")
t2 = threading.Thread(target=f1, args=(10, 20), name="t2")
t1.start()
t2.start()
