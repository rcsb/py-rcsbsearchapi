import setuptools  # type: ignore
import sys

# Load the version number from __init__.py
__version__ = "Undefined"
for line in open("rcsbsearch/__init__.py"):
    if line.startswith("__version__"):
        exec(line.strip())

# Version-specific requirements
install_requires = ["requests", "jsonschema"]
if sys.version_info < (3, 8):
    install_requires.append("typing_extensions")  # 3.7 only

# pin black version to get around https://github.com/psf/black/issues/2168
tests_requires = ["tox", "pytest", "black==20.8b1", "flake8", "mypy"]

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
    tests_require=tests_requires,
    install_requires=install_requires,
    extras_require={
        "progressbar": ["tqdm"],
        "tests": tests_requires,
        # should match docs/requirements.txt
        "docs": ["sphinx", "sphinx-rtd-theme", "myst-parser"],
    },
    packages=setuptools.find_packages(exclude=["tests"]),
    package_data={"": ["resources/*"]},
    scripts=[],
    classifiers=[
        "Programming Language :: Python :: 3",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Development Status :: 4 - Beta",
        # "Development Status :: 5 - Production/Stable",
        "Operating System :: OS Independent",
        "Intended Audience :: Science/Research",
        "License :: OSI Approved :: BSD License",
        "Topic :: Scientific/Engineering :: Bio-Informatics",
        "Typing :: Typed",
    ],
    # Uses dataclasses, f-strings, typing
    python_requires=">=3.7",
)
