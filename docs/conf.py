"""Configuration file for the Sphinx documentation builder.

For the full list of built-in configuration values, see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path("..").resolve()))
import flake8_async

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = "flake8-async"
# A001: shadowing python builtin
copyright = "2024, Zac Hatfield-Dodds, John Litborn, and Contributors"  # noqa: A001
author = "Zac Hatfield-Dodds, John Litborn, and Contributors"


version = flake8_async.__version__
release = version

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions: list[str] = [
    "sphinx.ext.intersphinx",
    "sphinx_codeautolink",
]

intersphinx_mapping = {
    "python": ("https://docs.python.org/3", None),
    "anyio": ("https://anyio.readthedocs.io/en/latest/", None),
    "trio": ("https://trio.readthedocs.io/en/latest/", None),
    # httpx? Did not seem to work on first try - I think they might not be using
    # sphinx at all, so probably can't link through intersphinx?
    # see https://github.com/encode/httpx/discussions/1220
    # we only have a few references to httpx though, so can just link manually.
}

# these are disabled by default, might re-disable them if they turn out to be noisy
codeautolink_warn_on_missing_inventory = True
codeautolink_warn_on_failed_resolve = True

templates_path = ["_templates"]
exclude_patterns: list[str] = ["_build", "Thumbs.db", ".DS_Store"]

# Warn about all references to unknown targets
nitpicky = True


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "alabaster"
# We don't currently use the _static directory, and git doesn't allow empty directories,
# so leaving it commented out for now to silence a warning.
# `html_static_path = ["_static"]`
