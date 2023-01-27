#!/usr/bin/env python3
"""Main setup & config file."""

from pathlib import Path

from setuptools import find_packages, setup


def local_file(name: str) -> Path:
    return Path(__file__).parent / name


with open(Path(__file__).parent / "flake8_trio" / "__init__.py") as o:
    for line in o:
        if line.startswith("__version__"):
            _, __version__, _ = line.split('"')
            break
    else:
        raise AssertionError("__version__ must be set")


setup(
    name="flake8-trio",
    version=__version__,
    author="Zac Hatfield-Dodds, John Litborn, and Contributors",
    author_email="zac@zhd.dev",
    packages=find_packages(include=["flake8_trio", "flake8_trio.*"]),
    url="https://github.com/Zac-HD/flake8-trio",
    license="MIT",
    description="A highly opinionated flake8 plugin for Trio-related problems.",
    zip_safe=False,
    install_requires=["flake8"],
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
    ],
    long_description=(
        local_file("README.md").open().read()
        + "\n\n"
        + local_file("CHANGELOG.md").open().read()
    ),
    long_description_content_type="text/markdown",
    entry_points={
        "flake8.extension": ["TRI = flake8_trio:Plugin"],
    },
)
