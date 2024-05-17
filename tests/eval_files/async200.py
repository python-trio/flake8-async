# type: ignore
# specify command-line arguments to be used when testing this file.
# Test spaces in options, and trailing comma
# Cannot test newlines, since argparse splits on those if passed on the CLI
# ARG --async200-blocking-calls=bar -> BAR, bee-> SHOULD_NOT_BE_PRINTED,bonnet ->SHOULD_NOT_BE_PRINTED,bee.bonnet->BEEBONNET,*.postwild->POSTWILD,prewild.*->PREWILD,*.*.*->TRIPLEDOT,


# don't error in sync function
def bar():
    bar()
    bee.bonnet()


async def afoo():
    bar()  # ASYNC200: 4, "bar", "BAR"
    print(bar())  # ASYNC200: 10, "bar", "BAR"

    # check that bee.bonnet triggers, and neither `bee` nor `bonnet`
    bee.bonnet()  # ASYNC200: 4, "bee.bonnet", "BEEBONNET"

    # check wildcard support
    bar.postwild()  # ASYNC200: 4, "*.postwild", "POSTWILD"
    prewild.anything()  # ASYNC200: 4, "prewild.*", "PREWILD"
    a.b.c()  # ASYNC200: 4, "*.*.*", "TRIPLEDOT"

    # don't error when it's not a call
    bar
    bee.bonnet
    boo(bar=None)

    # it won't catch esoteric ways of calling the function
    [bee.bonnet][0]()
    x = bee.bonnet
    x()

    # don't error inside lambda
    lambda: bar()

    # check that states are properly set/reset on nested functions
    def bar2():
        bar()

        async def bar3():
            bar()  # ASYNC200: 12, "bar", "BAR"

    bar()  # ASYNC200: 4, "bar", "BAR"

    # don't error on directly awaited expressions
    # https://github.com/python-trio/flake8-async/issues/85
    await bar()
    print(await bar())

    # error on not directly awaited expressions
    await print(bar())  # ASYNC200: 16, "bar", "BAR"
    await (foo() if bar() else foo())  # ASYNC200: 20, "bar", "BAR"
    await bee.bonnet(bar())  # ASYNC200: 21, "bar", "BAR"

    # known false alarms
    await (x := bar())  # ASYNC200: 16, "bar", "BAR"
    await (bar() if True else foo())  # ASYNC200: 11, "bar", "BAR"
    await (await bee.bonnet() or bar())  # ASYNC200: 33, "bar", "BAR"
    await ((lambda: bee.bonnet()) and bar())  # ASYNC200: 38, "bar", "BAR"

    # check that errors are enabled again
    bar()  # ASYNC200: 4, "bar", "BAR"
