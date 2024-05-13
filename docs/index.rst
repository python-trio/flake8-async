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


Some rules are incorporated into `ruff <https://docs.astral.sh/ruff/rules/#flake8-async-async>`_.


We previously maintained separate flake8-async and flake8-trio plugins, but merged both into this plugin under the more general "flake8-async" name after flake8-trio grew support for anyio and asyncio and became a superset of the former flake8-async.  All flake8-trio error codes were renamed from TRIOxxx to ASYNCxxx and the flake8-trio package is now deprecated.

Changelog: https://github.com/python-trio/flake8-async/blob/main/CHANGELOG.md
Contributor guide: https://github.com/python-trio/flake8-async/blob/main/CONTRIBUTING.md

*********
Contents:
*********
.. toctree::
   :maxdepth: 2

   usage
   rules
   contributing


******************
Indices and tables
******************

* :ref:`genindex`
* :ref:`modindex`
* :ref:`search`
* :doc:`usage`
* :doc:`rules`
* :doc:`contributing`
