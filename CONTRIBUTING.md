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
pre-commit run [--all-files]
# Run tests against current version of python and latest flake8
tox -e testenv
# Run all test environments (tox -a for a complete list)
tox
# Tip: Use --parallel and --develop, to save time when modifying and rerunning.
tox -p --develop
# --quiet and --parallel-no-spinner are also nice for output control.
```

## Meta-tests
To check that all codes are tested and documented there's a test that error codes mentioned in `README.md`, `CHANGELOG.md` (matching `TRIO\d\d\d`), the keys in `flake8_trio.Error_codes` and codes parsed from filenames and files in `tests/eval_files/`, are all equal.

## Test generator
Tests are automatically generated for files in the `tests/eval_files/` directory, with the code that it's testing interpreted from the file name. The file extension is split off, if there's a match for for `_py\d*` it strips that off and uses it to determine if there's a minimum python version for which the test should only run.

### `error:`
Lines containing `error:` are parsed as expecting an error of the code matching the file name, with everything on the line after the colon `eval`'d and passed as arguments to `flake8_trio.Error_codes[<error_code>].str_format`. The `globals` argument to `eval` contains a `lineno` variable assigned the current line number, and the `flake8_trio.Statement` namedtuple. The first element after `error:` *must* be an integer containing the column where the error on that line originates.
#### `TRIOxxx:`
You can instead of `error` specify the error code.

### `# ARG`
With `# ARG` lines you can also specify command-line arguments that should be passed to the plugin when parsing a file. Can be specified multiple times for several different arguments.  
Generated tests will by default `--select` the error code of the file, which will enable any visitors that can generate that code (and if those visitors can raise other codes they might be raised too). This can be overridden by adding an `# ARG --select=...` line.

### `# NOANYIO` and `# NOTRIO`
Eval files are also evaluated where ~all instances of "trio" is replaced with "anyio" and `--anyio` is prepended to the argument list, to check for compatibility with the [anyio](https://github.com/agronholm/anyio) library - unless they are marked with `# NOANYIO`.
If a file is marked with `# NOTRIO` it will not replace instances of "trio" with "anyio", and the file will not be run by the normal `eval_files` test generator.
#### `# ANYIO_NO_ERROR`
A file which is marked with this will ignore all `# error` or `# TRIO...` comments when running with anyio. Use when an error is trio-specific and replacing "trio" with "anyio" should silence all errors.

## Running pytest outside tox
If you don't want to bother with tox to quickly test stuff, you'll need to install the following dependencies:
```
pip install -e .
pip install pytest pytest-cov hypothesis hypothesmith flake8
```

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
