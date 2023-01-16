"""Test file used in tests/test_decator.py to check decorator and command line."""

app = None


@app.route  # type: ignore
async def f():
    print("hello world")
