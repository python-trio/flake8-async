************
Installation
************

Install from `PyPI <https://pypi.org/project/flake8-async>`__

.. code-block:: sh

   pip install flake8-async

*****
Usage
*****

install and run through flake8
==============================

.. code-block:: sh

   pip install flake8 flake8-async
   flake8 .

.. _install-run-pre-commit:

install and run with pre-commit
===============================

If you use `pre-commit <https://pre-commit.com/>`__, you can use it with flake8-async by
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
``flake8-async`` does not retain any memory between files, they are parsed completely independently.

Afterwards, run

.. code-block:: sh

   pip install pre-commit flake8-async
   pre-commit run .

.. _run_standalone:

install and run as standalone
=============================

If inside a git repository, running without arguments will run it against all ``*.py`` files in the repository.

Note that this does not currently support reading config files, and does not respect ``# noqa`` comments.

.. code-block:: sh

   pip install flake8-async
   flake8-async

with autofixes
--------------

.. code-block:: sh

   flake8-async --autofix=ASYNC

specifying source files
-----------------------

.. code-block:: sh

   flake8-async my_python_file.py

zsh-only
^^^^^^^^

.. code-block:: zsh

   flake8-async **/*.py


Run through ruff
================
`Ruff <https://github.com/astral-sh/ruff>`_ is a linter and formatter that reimplements a lot of rules from various flake8 plugins.

They currently only support a small subset of the ``flake8-async`` rules though, see https://github.com/astral-sh/ruff/issues/8451 for current status and https://docs.astral.sh/ruff/rules/#flake8-async-async for documentation.

*************
Configuration
*************

`You can configure flake8 with command-line options <https://flake8.pycqa.org/en/latest/user/invocation.html>`_,
but we prefer using a config file. See general documentation for `configuring flake8  <https://flake8.pycqa.org/en/latest/user/configuration.html>`_ which also handles options registered by plugins such as ``flake8-async``.

If you want to use a ``pyproject.toml`` file for configuring flake8 we recommend `pyproject-flake8 <https://github.com/csachs/pyproject-flake8>`_ or similar.

Note that when running ``flake8-async`` as a standalone it's not currently possible to use a configuration file. Consider using some wrapper that lets you specify command-line flags in a file. For example, :ref:`install-run-pre-commit`, `tox <https://tox.wiki>`_, `hatch scripts <https://hatch.pypa.io/1.9/environment/#scripts>`_, MakeFiles, etc.

Selecting rules
===============

.. _valueerror_ignore:

``ValueError`` when trying to ``ignore`` error codes in config file
-------------------------------------------------------------------

Error codes with more than three letters are not possible to ``ignore`` in
config files since flake8>=6, as flake8 tries to validate correct
configuration with a regex. We have decided not to conform to this, as it
would be a breaking change for end-users requiring them to update ``noqa``\ s
and configurations, we think the ``ASYNC`` code is much more readable than
e.g. ``ASYxxx``, and ruff does not enforce such a limit.
The easiest option for users hitting this error is to instead use the :ref:`disable`
option.
See further discussion and other
workarounds in https://github.com/python-trio/flake8-async/issues/230.

.. _enable:

``enable``
------------

Comma-separated list of error codes to enable, similar to flake8 --select but is additionally more performant as it will disable non-enabled visitors from running instead of just silencing their errors. Defaults to "ASYNC".

Example
^^^^^^^
.. code-block:: none

    enable=ASYNC1,ASYNC200

.. _disable:

``disable``
-------------

Comma-separated list of error codes to disable, similar to flake8 ``--ignore`` but is additionally more performant as it will disable non-enabled visitors from running instead of just silencing their errors. :ref:`It will also bypass errors introduced in flake8>=6 <valueerror_ignore>`.
This is parsed after :ref:`enable`, so if a rule is both "enabled" and "disabled" it will be disabled.
Defaults to "ASYNC9".

Example
^^^^^^^
.. code-block:: none

    disable=ASYNC91,ASYNC117

.. _autofix:

``autofix``
-------------

Comma-separated list of error-codes to enable autofixing for if implemented.
Requires :ref:`running as a standalone program <run_standalone>`.
Only a subset of rules support autofixing, see :ref:`this list <autofix-support>`.
Pass ``--autofix=ASYNC`` to enable all available autofixes.

Defaults to an empty list.

Example
^^^^^^^
.. code-block:: none

    autofix=ASYNC


``error-on-autofix``
----------------------

Whether to also print an error message for autofixed errors.
Defaults to ``False``

Example
^^^^^^^
.. code-block:: none

    error-on-autofix=True

Modifying rule behaviour
========================

.. _anyio:

``anyio``
-----------

Change the default library to be anyio instead of trio.
This is mostly used for the sake of printing suggestions in error messages, but may affect some logic.
If additional libraries are imported other than the default then rules will assume multiple are available simultaneously.
It is currently not possible to set multiple default libraries, other than `anyio`+`asyncio`.

Example
^^^^^^^
.. code-block:: none

    anyio=True

.. _asyncio:

``asyncio``
-------------
Set default library to be ``asyncio``. See :ref:`anyio`

Example
^^^^^^^
.. code-block:: none

    asyncio=True


``no-checkpoint-warning-decorators``
------------------------------------

Comma-separated list of decorators to disable checkpointing checks for, turning off :ref:`ASYNC910 <async910>` and :ref:`ASYNC911 <async911>` warnings for functions decorated with any decorator matching against an entry in the list.
Matching is done with `fnmatch <https://docs.python.org/3/library/fnmatch.html>`_.
Defaults to disabling for ``asynccontextmanager``.

Decorators-to-match must be identifiers or dotted names only (not PEP-614 expressions), and will match against the name only - e.g. ``foo.bar`` matches ``foo.bar``, ``foo.bar()``, and ``foo.bar(args, here)``, etc.

Example
^^^^^^^

.. code-block:: none

   no-checkpoint-warning-decorators =
     mydecorator,
     mydecoratorpackage.checkpointing_decorators.*,
     ign*,
     *.ignore,

.. _exception-suppress-context-managers:

``exception-suppress-context-managers``
---------------------------------------


Comma-separated list of contextmanagers which may suppress exceptions
without reraising. For ASYNC91x, these will be parsed in the worst-case scenario,
where any checkpoints inside the contextmanager are not executed, and all
exceptions are suppressed.
``contextlib.suppress`` will be added to the list after parsing, and some basic parsing
of ``from contextlib import suppress`` is supported.
Decorators can be dotted or not, as well as support * as a wildcard.

If you want to be extremely pessimistic, you can specify ``*`` as the context manager.
We may add a whitelist option in the future to support this use-case better.

Example
^^^^^^^

.. code-block:: none

   exception-suppress-context-managers =
     mysuppressor,
     dangerouslibrary.*,
     *.suppress,


.. _--startable-in-context-manager:

``startable-in-context-manager``
--------------------------------

Comma-separated list of functions which should be used with :meth:`trio.Nursery.start`/:meth:`anyio.abc.TaskGroup.start` when opening a context manager.
We then add known functions from Trio to this list, namely :func:`trio.run_process`, :func:`trio.serve_tcp`, :func:`trio.serve_ssl_over_tcp`, :func:`trio.serve_listeners`, and :meth:`trio.DTLSEndpoint.serve`.
AnyIO does not have any functions in its API that defines ``task_status``.
asyncio does not have an equivalent of :meth:`~trio.Nursery.start`, nor ``task_status``, but you could still add functions to this list that you want to be extra careful about when opening in an `asyncio.TaskGroup` in an ``__aenter__``

Names must be valid identifiers as per :meth:`str.isidentifier`.
Used by :ref:`ASYNC113 <async113>`, and :ref:`ASYNC114 <async114>` will warn when encountering methods not in the list.

Example
^^^^^^^

.. code-block:: none

   startable-in-context-manager =
     myfun,
     myfun2,

.. _async200-blocking-calls:

``async200-blocking-calls``
---------------------------

Comma-separated list of pairs of values separated by ``->`` (optional whitespace stripped), where the first is a pattern for a call that should raise :ref:`ASYNC200 <async200>` if found inside an async function, and the second is what should be suggested to use instead.
It uses fnmatch as per `no-checkpoint-warning-decorators`_ for matching.
The part after ``->`` is not used by the checker other than when printing the error, so you could add extra info there if you want.

The format of the error message is ``User-configured blocking sync call {0} in async function, consider replacing with {1}.``, where ``{0}`` is the pattern the call matches and ``{1}`` is the suggested replacement.

Example
^^^^^^^

.. code-block:: none

   async200-blocking-calls =
     my_blocking_call -> async.alternative,
     module.block_call -> other_function_to_use,
     common_error_call -> alternative(). But sometimes you should use other_function(). Ask joe if you're unsure which one,
     dangerous_module.* -> corresponding function in safe_module,
     *.dangerous_call -> .safe_call()

Specified patterns must not have parentheses, and will only match when the pattern is the name of a call, so given the above configuration

.. code-block:: python

   async def my_function():
       my_blocking_call()  # this would raise an error
       x = my_blocking_call(a, b, c)  # as would this
       y = my_blocking_call  # but not this
       y()  # or this
       [my_blocking_call][0]()  # nor this
       def my_blocking_call():  # it's also safe to use the name in other contexts
           ...
       arbitrary_other_function(my_blocking_call=None)

.. _transform-async-generator-decorators:

``transform-async-generator-decorators``
----------------------------------------
Comma-separated list of decorators that make async generators safe, disabling
:ref:`ASYNC900 <ASYNC900>`, :ref:`ASYNC101 <ASYNC101>`, and :ref:`ASYNC119 <ASYNC119>` warnings for.
``[pytest.]fixture`` and ``[contextlib.]asynccontextmanager`` are always considered safe.
Decorators can be dotted or not, as well as support * as a wildcard.

Example
^^^^^^^

.. code-block:: none

   transform-async-generator-decorators =
     fastapi.Depends
     trio_util.trio_async_generator
