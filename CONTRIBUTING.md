# Contributor Guide

Contributions welcome!  We'll expand this guide as we go.


## Development

When you wish to add a check to `flake8-trio` please ensure the following:

- This `README.md` gets a one line about your new warning
- CHANGELOG gets added to a `## UNRELEASED` section
- Unittests are added showing the check highlight where it should and shouldn't
  (see flake8-bugbear for examples of good linter tests)

To run our test suite please use tox.

```console
# Formatting and Linting
tox -e check
# Test Running
tox -e test
```


## Releasing a new version
We want to ship bigfixes or new features as soon as they're ready,
so our release process is automated:

1. Increment `__version__` in `src/flake8_trio.py`
2. Ensure there's a corresponding entry in `CHANGELOG.md` with same version
3. Merge to master, and CI will do the rest!
