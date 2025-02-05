#!/usr/bin/env python3
"""Main setup & config file."""

from pathlib import Path

from setuptools import find_packages, setup  # type: ignore


def local_file(name: str) -> Path:
    return Path(__file__).parent / name


with open(Path(__file__).parent / "flake8_async" / "__init__.py") as o:
    for line in o:
        if line.startswith("__version__"):
            _, __version__, _ = line.split('"')
            break
    else:
        raise AssertionError("__version__ must be set")


setup(
    name="flake8-async",
    version=__version__,
    author="Zac Hatfield-Dodds, John Litborn, and Contributors",
    author_email="zac@zhd.dev",
    packages=find_packages(include=["flake8_async", "flake8_async.*"]),
    project_urls={
        "Homepage": "https://github.com/python-trio/flake8-async",
        "Documentation": "https://flake8-async.readthedocs.io/",
        "Changelog": "https://flake8-async.readthedocs.io/en/latest/changelog.html",
    },
    license="MIT",
    license_files=[],  # https://github.com/pypa/twine/issues/1216
    description="A highly opinionated flake8 plugin for Trio-related problems.",
    zip_safe=False,
    install_requires=["libcst>=1.0.1"],
    extras_require={"flake8": ["flake8>=6"]},
    python_requires=">=3.9",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Framework :: Flake8",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
        "Programming Language :: Python :: 3.11",
        "Programming Language :: Python :: 3.12",
        "Programming Language :: Python :: 3.13",
    ],
    long_description=(local_file("README.md").open().read()),
    long_description_content_type="text/markdown",
    entry_points={
        # You're not allowed to register error codes longer than 3 characters. But flake8
        # doesn't enforce anything about the characters trailing the code, so we can say
        # the code is ASY and then just always happen to print NCxxx directly after it.
        "flake8.extension": ["ASY = flake8_async:Plugin"],
        "console_scripts": ["flake8-async=flake8_async:main"],
    },
)
