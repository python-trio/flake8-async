.. flake8-async documentation master file, created by
   sphinx-quickstart on Wed Mar 20 13:37:26 2024.
   You can adapt this file completely to your liking, but it should at least
   contain the root `toctree` directive.

############
flake8-async
############


A highly opinionated flake8 plugin for problems related to `Trio <https://github.com/python-trio/trio>`_, `AnyIO <https://github.com/agronholm/anyio>`_, or `asyncio <https://docs.python.org/3/library/asyncio.html>`_.


This can include anything from outright bugs, to pointless/dead code,
to likely performance issues, to minor points of idiom that might signal
a misunderstanding.


The plugin may well be too noisy or pedantic depending on your requirements or opinions, in which case you should consider :ref:`--disable` for those rules.
Pairs well with flake8-bugbear.


Some checks are incorporated into `ruff <https://github.com/astral-sh/ruff>`_.


This plugin was previously known as flake8-trio, and there was a separate small plugin known as flake8-async for asyncio. But this plugin was a superset of the checks in flake8-async, and support for anyio was added, so it's now named flake8-async to more properly convey its usage. At the same time all error codes were renamed from TRIOxxx to ASYNCxxx, as was previously used by the old flake8-async.


*********
Contents:
*********
.. toctree::
   :maxdepth: 2

   usage
   rules


******************
Indices and tables
******************

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
* :doc:`usage`
* :doc:`rules`
