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
        for l in get_narration(verbose=True):
            print(l)
