#!/usr/bin/env python3

from pathlib import Path

import setuptools


def local_file(name: str) -> Path:
    return Path(__file__).parent / name


with local_file("flake8_trio.py").open("r") as o:
    for line in o:
        if line.startswith("__version__"):
            _, __version__, _ = line.split('"')
            break
    else:
        raise AssertionError("__version__ must be set")


setuptools.setup(
    name="flake8-trio",
    version=__version__,
    author="Zac Hatfield-Dodds and Contributors",
    author_email="me@cooperlees.com",
    py_modules=["flake8_trio"],
    url="https://github.com/Zac-HD/flake8-trio",
    license="MIT",
    description="A highly opinionated flake8 plugin for Trio-related problems.",
    zip_safe=False,
    install_requires=["flake8"],
    python_requires=">=3.8",
    classifiers=[
        "Development Status :: 3 - Alpha",
        "Framework :: Flake8",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: MIT License",
        "Programming Language :: Python",
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Programming Language :: Python :: 3.10",
    ],
    long_description=(
        local_file("README.md").open().read()
        + "\n\n"
        + local_file("CHANGELOG.md").open().read()
    ),
    long_description_content_type="text/markdown",
    entry_points={
        "flake8.extension": ["TRIO = flake8_trio:Plugin"],
    },
    extras_require={"dev": ["hypothesis", "hypothesmith>=0.2"]},
)
