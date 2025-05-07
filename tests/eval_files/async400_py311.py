try:
    ...
except* ValueError as e:
    e.anything  # error: 4, "anything"
    e.foo()  # error: 4, "foo"
    e.bar.zee  # error: 4, "bar"

    # from ExceptionGroup
    e.message
    e.exceptions
    e.subgroup
    e.split
    e.derive

    # from BaseException
    e.args
    e.with_traceback
    e.add_note

    # ignore anything that looks like a dunder
    e.__foo__
    e.__bar__

e.anything  # safe

# assigning to the variable clears it
try:
    ...
except* ValueError as e:
    e = e.exceptions[0]
    e.ignore  # safe
except* ValueError as e:
    e, f = 1, 2
    e.anything  # safe
except* TypeError as e:
    (e, f) = (1, 2)
    e.anything  # safe
except* ValueError as e:
    with blah as e:
        e.anything
    e.anything
except* ValueError as e:
    e: int = 1
    e.real
except* ValueError as e:
    with blah as (e, f):
        e.anything

# check state saving
try:
    ...
except* ValueError as e:
    ...
except* BaseException:
    e.error  # safe

try:
    ...
except* ValueError as e:
    try:
        ...
    except* TypeError as e:
        ...
    e.anything  # error: 4, "anything"

try:
    ...
except* ValueError as e:

    def foo():
        # possibly problematic, but we minimize false alarms
        e.anything

    e.anything  # error: 4, "anything"

    def foo(e):
        # this one is more clear it should be treated as safe
        e.anything

    e.anything  # error: 4, "anything"

    lambda e: e.anything

    e.anything  # error: 4, "anything"
