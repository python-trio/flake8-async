*****************
Contributor Guide
*****************

Contributions welcome!  We'll expand this guide as we go.

Development
===========

When you wish to add a check to ``flake8-async`` please ensure the following:

- ``rules.rst`` gets an entry about your new warning
- Add a changelog entry (see 'Releasing a new version' below)
- A test in ``tests/eval_files`` is added for your check. See the "Test generator" heading below.

Checks
------
We use pre-commit for managing formatters, linters, type-checkers, etc. Passing the checks is required to merge a pull request.

.. code-block::

  pre-commit run [--all-files]


Running tests
-------------
Run tests against current version of python and latest flake8

.. code-block::

  tox -e testenv

Run all test environments (``tox -a`` for a complete list)

.. code-block::

  tox

Run a specific python version

.. code-block::

   tox -e py311

Tip: Use ``--parallel`` and ``--develop``, to save time when modifying and rerunning.

.. code-block::

  tox -p --develop

``--quiet`` and ``--parallel-no-spinner`` are also nice for output control.

Meta-tests
==========
To check that all codes are tested and documented there's a test that error codes mentioned in ``docs/rules.rst``, ``docs/changelog.rst`` (matching ``ASYNC\d\d\d``), the keys in ``flake8_async.Error_codes`` and codes parsed from filenames and files in ``tests/eval_files/``, are all equal.

Test generator
==============
Tests are automatically generated for files in the ``tests/eval_files/`` directory, with the code that it's testing interpreted from the file name. The file extension is split off, if there's a match for for ``_py\d*`` it strips that off and uses it to determine if there's a minimum python version for which the test should only run. (Note: no tests are currently version-gated). Other descriptions after ``async\d\d\d_`` are not interpreted by the test generator.

``error:``
----------
Lines containing ``error:`` are parsed as expecting an error of the code matching the file name, with everything on the line after the colon ``eval``'d and passed as arguments to ``flake8_async.Error_codes[<error_code>].str_format``. The ``globals`` argument to ``eval`` contains a ``lineno`` variable assigned the current line number, and the ``flake8_async.Statement`` namedtuple. The first element after ``error:`` *must* be an integer containing the column where the error on that line originates.

``ASYNCxxx:``
^^^^^^^^^^^^^
You can instead of ``error`` specify the error code. This is required if multiple different errors are enabled for the same test file.

Library parametrization
-----------------------
Eval files are evaluated with each supported library. It does this by replacing all instances of the ``BASE_LIBRARY`` ("trio" by default) with the two other libraries, and setting the corresponding flag (``--anyio`` or ``--asyncio``). See :ref:`BASE_LIBRARY`


Magic Markers
-------------
Special comments can be put into eval files to customize different aspects of the test generator.

.. _BASE_LIBRARY:

``# BASE_LIBRARY``
^^^^^^^^^^^^^^^^^^
Used to specify the primary library an eval file is testing. Defaults to ``trio``. E.g.

.. code-block:: python

  # BASE_LIBRARY anyio


``# AUTOFIX``
^^^^^^^^^^^^^
Files in ``tests/eval_files`` with this marker will have two files in ``tests/autofix_files/``. One with the same name containing the code after being autofixed, and a diff file between those two.
During tests the result of running the checker on the eval file with autofix enabled will be compared to the content of the autofix file and will print a diff (if ``-s`` is on) and assert that the content is the same. ``--generate-autofix`` is added as a pytest flag to ease development, which will print a diff (with ``-s``) and overwrite the content of the autofix file.
Files without this marker will be checked that they *don't* modify the file content.

``# ARG``
^^^^^^^^^
With ``# ARG`` lines you can also specify command-line arguments that should be passed to the plugin when parsing a file. Can be specified multiple times for several different arguments.
Generated tests will by default ``--select`` the error code of the file, which will enable any visitors that can generate that code (and if those visitors can raise other codes they might be raised too). This can be overridden by adding an ``# ARG --select=...`` line.

``# ANYIO_NO_ERROR``, ``# TRIO_NO_ERROR``, ``# ASYNCIO_NO_ERROR``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
A file which is marked with this will ignore all ``# error`` or ``# TRIO...`` comments when running with anyio. Use when an error is library-specific and replacing all instances means the file should no longer raise any errors.

``# NOANYIO``, ``# NOTRIO``, ``#NOASYNCIO``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^
Disables checking a file with the specified library. Should be used somewhat sparingly, and always have a comment motivating its use.

Running pytest outside tox
==========================
If you don't want to bother with tox to quickly test stuff, you'll need to install the following dependencies:

.. code-block:: console

  pip install -e .
  pip install pytest pytest-cov hypothesis hypothesmith flake8

Style Guide
===========

**Code style:** code review should focus on correctness, performance, and readability.
Low-level nitpicks are handled *exclusively* by our formatters and linters, so if
``pre-commit`` passes there's nothing else to say.

**Terminology:** use "false/missed alarm" rather than "true/false positive", or the
even worse "type I/II error".  "False alarm" or "missed alarm" have obvious meanings
which do not rely on confusing conventions (is noticing an error positive or negative?)
or rote memorization of an arbitrary convention.

Releasing a new version
=======================
We want to ship bugfixes or new features as soon as they're ready,
so our release process is automated:

1. Increment ``__version__`` in ``flake8_async/__init__.py``
2. Ensure there's a corresponding entry in ``docs/changelog.rst`` with same version
3. Merge to main, and CI will do the rest!
