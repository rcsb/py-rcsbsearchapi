import setuptools
import sys

# Load the version number from __init__.py
__version__ = "Undefined"
for line in open("rcsbsearch/__init__.py"):
    if line.startswith("__version__"):
        exec(line.strip())

# Version-specific requirements
install_requires = ["requests"]
if sys.version_info < (3, 8):
    install_requires.append("typing_extensions")  # 3.6-3.7 only

# README
with open("README.md", "r") as fh:
    long_description = fh.read()


setuptools.setup(
    name="rcsbsearch",
    url="https://github.com/sbliven/rcsbsearch",
    description="Access the RCSB Search API",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="Spencer Bliven",
    author_email="spencer.bliven@gmail.com",
    version=__version__,
    tests_requires=["tox", "pytest", "black", "flake8", "mypy"],
    install_requires=install_requires,
    extras={
        "progressbar": ["tqdm"],
        "docs": ["mkdocs"]
    },
    packages=setuptools.find_packages(exclude=["tests"]),
    scripts=[],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Development Status :: 4 - Beta",
        # "Development Status :: 5 - Production/Stable",
        "License :: OSI Approved :: MIT License",
        "Operating System :: OS Independent",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: BSD License",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Typing :: Typed",
    ],
    # Uses dataclasses, f-strings, typing
    python_requires=">=3.7",
)
