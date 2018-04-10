from errator import narrate_cm, narrate, get_narration, set_narration_options


@narrate("So I started to 'nf1'...")
def f1():
    f2()


@narrate("...which occasioned me to 'nf2'")
def f2():
    with narrate_cm("during which I started a narration context..."):
        f3()


@narrate("...and that led me to finally 'nf3'")
def f3():
    raise Exception("oops")


if __name__ == "__main__":
    set_narration_options(verbose=True)
    try:
        f1()
    except:
        for l in get_narration():
            print(l)
