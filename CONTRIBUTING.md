# Contributor Guide

Contributions welcome!  We'll expand this guide as we go.


## Development

When you wish to add a check to `flake8-trio` please ensure the following:

- `README.md` gets a one line about your new warning
- Add a CHANGELOG entry (see 'Releasing a new version' below)
- Unittests are added showing the check highlight where it should and shouldn't
  (see flake8-bugbear for examples of good linter tests)

To run our test suite please use tox.

```console
# Formatting and Linting
tox -e check
# Test Running
tox -e test
# Run checks and tests against Python 3.8, 3.9 and 3.10
tox -e ALL
# Tip: Use -p (run tests in parallel) and --develop (install package with -e) to save time when modifying and rerunning
tox -e ALL -p --develop
```

## Meta-tests
To check that all codes are tested and documented there's a test that error codes mentioned in `README.md`, `CHANGELOG.md` (matching `TRIO\d\d\d`), the keys in `flake8_trio.Error_codes` and codes parsed from filenames matching `tests/trio*.py`, are all equal.

## Test generator
Tests are automatically generated for files named `trio*.py` in the `tests/` directory, with the code that it's testing interpreted from the file name. The file extension is split off, if there's a match for for `_py\d*` it strips that off and uses it to determine if there's a minimum python version for which the test should only run.

Lines containing `error:` are parsed as expecting an error of the code matching the file name, with everything on the line after the colon `eval`'d and passed as arguments to `flake8_trio.Error_codes[<error_code>].str_format`. The `globals` argument to `eval` contains a `lineno` variable assigned the current line number, and the `flake8_trio.Statement` namedtuple. The first element after `error:` *must* be an integer containing the column where the error on that line originates.

Test files by default filter out all errors not matching the file name, but if there's a line `#INCLUDE TRIO\d\d\d TRIO\d\d\d` those additional error codes are not filtered out and will be an error if encountered.


## Style Guide

**Code style:** code review should focus on correctness, performance, and readability.
Low-level nitpicks are handled *exclusively* by our formatters and linters, so if
`tox` passes there's nothing else to say.

**Terminology:** use "false/missed alarm" rather than "true/false positive", or the
even worse "type I/II error".  "False alarm" or "missed alarm" have obvious meanings
which do not rely on confusing conventions (is noticing an error positive or negative?)
or rote memorization of an arbitrary convention.


## Releasing a new version
We want to ship bigfixes or new features as soon as they're ready,
so our release process is automated:

1. Increment `__version__` in `src/flake8_trio.py`
2. Ensure there's a corresponding entry in `CHANGELOG.md` with same version
3. Merge to master, and CI will do the rest!
