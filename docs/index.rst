.. flake8-async documentation master file, created by
   sphinx-quickstart on Wed Mar 20 13:37:26 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

flake8-async
========================================

.. toctree::
   :maxdepth: 2
   :caption: Contents:

   rules


Indices and tables
==================

* :doc:`rules`
* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`


A highly opinionated flake8 plugin for problems related to `Trio <https://github.com/python-trio/trio>`_, `AnyIO <https://github.com/agronholm/anyio>`_, or `asyncio <https://docs.python.org/3/library/asyncio.html>`_.
This can include anything from outright bugs, to pointless/dead code,
to likely performance issues, to minor points of idiom that might signal
a misunderstanding.
It may well be too noisy for anyone with different opinions, that's OK.
Pairs well with flake8-bugbear.
Some checks are incorporated into `ruff <https://github.com/astral-sh/ruff>`_.
This plugin was previously known as flake8-trio, and there was a separate small plugin known as flake8-async for asyncio. But this plugin was a superset of the checks in flake8-async, and support for anyio was added, so it's now named flake8-async to more properly convey its usage. At the same time all error codes were renamed from TRIOxxx to ASYNCxxx, as was previously used by the old flake8-async.

Installation
------------

.. code-block:: console

   pip install flake8-async

Usage
--------

install and run through flake8
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: sh

   pip install flake8 flake8-async
   flake8 .

install and run with pre-commit
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you use `pre-commit <https://pre-commit.com/>`_, you can use it with flake8-async by
adding the following to your ``.pre-commit-config.yaml``:

.. code-block:: yaml

   minimum_pre_commit_version: '2.9.0'
   repos:
   - repo: https://github.com/python-trio/flake8-async
     rev: 23.2.5
     hooks:
       - id: flake8-async
         # args: [--enable=ASYNC, --disable=ASYNC9, --autofix=ASYNC]

This is often considerably faster for large projects, because ``pre-commit``
can avoid running ``flake8-async`` on unchanged files.
Afterwards, run

.. code-block:: sh

   pip install pre-commit flake8-async
   pre-commit run .

install and run as standalone
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If inside a git repository, running without arguments will run it against all ``*.py`` files in the repository.

.. code-block:: sh

   pip install flake8-async
   flake8-async

with autofixes
""""""""""""""

.. code-block:: sh

   flake8-async --autofix=ASYNC

specifying source files
"""""""""""""""""""""""

.. code-block:: sh

   flake8-async my_python_file.py

zsh-only
''''''''

.. code-block:: zsh

   flake8-async **/*.py


Run through ruff
^^^^^^^^^^^^^^^^
`Ruff <https://github.com/astral-sh/ruff>` is a linter and formatter that reimplements a lot of rules from various flake8 plugins. They currently only support a small subset of the rules though, see https://github.com/astral-sh/ruff/issues/8451 for current status and https://docs.astral.sh/ruff/rules/#flake8-async-async for documentation.

Configuration
-------------

`You can configure flake8 with command-line options <https://flake8.pycqa.org/en/latest/user/configuration.html>`_,
but we prefer using a config file. The file needs to start with a section marker ``[flake8]`` and the following options are then parsed using flake8's config parser, and can be used just like any other flake8 options.
Note that it's not currently possible to use a configuration file when running ``flake8-async`` standalone.

``ValueError`` when trying to ``ignore`` error codes in config file
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Error codes with more than three letters are not possible to ``ignore`` in
config files since flake8>=6, as flake8 tries to validate correct
configuration with a regex. We have decided not to conform to this, as it
would be a breaking change for end-users requiring them to update ``noqa``\ s
and configurations, we think the ``ASYNC`` code is much more readable than
e.g. ``ASYxxx``, and ruff does not enforce such a limit. The easiest option
for users hitting this error is to instead use the ``--disable`` option as
documented `below <#--disable>`__. See further discussion and other
workarounds in https://github.com/python-trio/flake8-async/issues/230.


``--enable``
^^^^^^^^^^^^

Comma-separated list of error codes to enable, similar to flake8 --select but is additionally more performant as it will disable non-enabled visitors from running instead of just silencing their errors.

``--disable``
^^^^^^^^^^^^^

Comma-separated list of error codes to disable, similar to flake8 --ignore but is additionally more performant as it will disable non-enabled visitors from running instead of just silencing their errors.

``--autofix``
^^^^^^^^^^^^^

Comma-separated list of error-codes to enable autofixing for if implemented. Requires running as a standalone program. Pass ``--autofix=ASYNC`` to enable all autofixes.


``--error-on-autofix``
^^^^^^^^^^^^^^^^^^^^^^

Whether to also print an error message for autofixed errors.

``--anyio``
^^^^^^^^^^^

Change the default library to be anyio instead of trio. If trio is imported it will assume both are available and print suggestions with [anyio/trio].

``no-checkpoint-warning-decorators``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Comma-separated list of decorators to disable checkpointing checks for, turning off ASYNC910 and ASYNC911 warnings for functions decorated with any decorator matching any in the list. Matching is done with `fnmatch <https://docs.python.org/3/library/fnmatch.html>`_. Defaults to disabling for ``asynccontextmanager``.

Decorators-to-match must be identifiers or dotted names only (not PEP-614 expressions), and will match against the name only - e.g. ``foo.bar`` matches ``foo.bar``, ``foo.bar()``, and ``foo.bar(args, here)``, etc.

For example:

::

   no-checkpoint-warning-decorators =
     mydecorator,
     mydecoratorpackage.checkpointing_decorators.*,
     ign*,
     *.ignore,

``startable-in-context-manager``
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Comma-separated list of methods which should be used with ``.start()`` when opening a context manager,
in addition to the default ``trio.run_process``, ``trio.serve_tcp``, ``trio.serve_ssl_over_tcp``, and
``trio.serve_listeners``.  Names must be valid identifiers as per ``str.isidentifier()``. For example:

::

   startable-in-context-manager =
     myfun,
     myfun2,

.. async200-blocking-calls:

``async200-blocking-calls``
^^^^^^^^^^^^^^^^^^^^^^^^^^^

Comma-separated list of pairs of values separated by ``->`` (optional whitespace stripped), where the first is a pattern for a call that should raise an error if found inside an async function, and the second is what should be suggested to use instead. It uses fnmatch as per `no-checkpoint-warning-decorators`_ for matching. The part after ``->`` is not used by the checker other than when printing the error, so you could add extra info there if you want.

The format of the error message is ``User-configured blocking sync call {0} in async function, consider replacing with {1}.``, where ``{0}`` is the pattern the call matches and ``{1}`` is the suggested replacement.

Example:

::

   async200-blocking-calls =
     my_blocking_call -> async.alternative,
     module.block_call -> other_function_to_use,
     common_error_call -> alternative(). But sometimes you should use other_function(). Ask joe if you're unsure which one,
     dangerous_module.* -> corresponding function in safe_module,
     *.dangerous_call -> .safe_call()

Specified patterns must not have parentheses, and will only match when the pattern is the name of a call, so given the above configuration

::

   async def my_function():
       my_blocking_call()  # this would raise an error
       x = my_blocking_call(a, b, c)  # as would this
       y = my_blocking_call  # but not this
       y()  # or this
       [my_blocking_call][0]()  # nor this
       def my_blocking_call():  # it's also safe to use the name in other contexts
           ...
       arbitrary_other_function(my_blocking_call=None)
