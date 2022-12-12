# specify command-line arguments to be used when testing this file.
# ARGS --trio200-blocking-calls=bar->BAR,bee->SHOULD_NOT_BE_PRINTED,bonnet->SHOULD_NOT_BE_PRINTED,bee.bonnet->BEEBONNET,*.postwild->POSTWILD,prewild.*->PREWILD,*.*.*->TRIPLEDOT

# don't error in sync function
def foo():
    bar()


async def afoo():
    bar()  # TRIO200: 4, "bar", "BAR"
    print(bar())  # TRIO200: 10, "bar", "BAR"

    # check that bee.bonnet triggers, and neither `bee` nor `bonnet`
    bee.bonnet()  # TRIO200: 4, "bee.bonnet", "BEEBONNET"

    # check wildcard support
    bar.postwild()  # TRIO200: 4, "*.postwild", "POSTWILD"
    prewild.anything()  # TRIO200: 4, "prewild.*", "PREWILD"
    a.b.c()  # TRIO200: 4, "*.*.*", "TRIPLEDOT"

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
    def bar():
        bar()

        async def bar():
            bar()  # TRIO200: 12, "bar", "BAR"

    bar()  # TRIO200: 4, "bar", "BAR"
