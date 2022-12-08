# ARGS --trio200-blocking-calls=bar->BAR,bee->NOERROR,bonnet->NOERROR,bee.bonnet->BEEBONNET


def foo():
    bar()


async def afoo():
    bar()  # TRIO200: 4, "bar", "BAR"
    print(bar())  # TRIO200: 10, "bar", "BAR"
    bee.bonnet()  # TRIO200: 4, "bee.bonnet", "BEEBONNET"

    bar
    bee.bonnet
    boo(bar=None)
    lambda: bar()

    def bar():
        bar()

        async def bar():
            bar()  # TRIO200: 12, "bar", "BAR"
