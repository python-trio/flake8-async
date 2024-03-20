"""Configuration file for the Sphinx documentation builder.

For the full list of built-in configuration values, see the documentation:
https://www.sphinx-doc.org/en/master/usage/configuration.html
"""

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

extensions: list[str] = []

templates_path = ["_templates"]
exclude_patterns: list[str] = []

# Warn about all references to unknown targets
nitpicky = True


# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = "alabaster"
html_static_path = ["_static"]
