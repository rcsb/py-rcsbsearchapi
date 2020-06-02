try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup
import sys

# Load the version number from __init__.py
__version__ = "Undefined"
for line in open("rcsbsearch/__init__.py"):
    if line.startswith("__version__"):
        exec(line.strip())

install_requires = ["requests"]
if sys.version_info < (3, 8):
    install_requires.append("typing_extensions")  # 3.6-3.7 only
config = {
    "name": "rcsbsearch",
    "description": "Access the RCSB Search API",
    "author": "Spencer Bliven",
    "url": "https://github.com/sbliven/rcsbsearch",
    # 'download_url': 'https://github.com/sbliven/rcsbsearch',
    "author_email": "spencer.bliven@gmail.com",
    "version": __version__,
    "tests_requires": ["tox", "pytest", "black", "flake8"],
    "install_requires": install_requires,
    "extras": {"progressbar": "tqdm"},
    "packages": ["rcsbsearch"],
    "scripts": [],
}

setup(**config)
