try:
    from setuptools import setup
except ImportError:
    from distutils.core import setup

# Load the version number from __init__.py
__version__ = "Undefined"
for line in open("rcsbsearch/__init__.py"):
    if line.startswith("__version__"):
        exec(line.strip())

config = {
    "name": "rcsbsearch",
    "description": "Access the RCSB Search API",
    "author": "Spencer Bliven",
    "url": "https://github.com/sbliven/rcsbsearch",
    # 'download_url': 'https://github.com/sbliven/rcsbsearch',
    "author_email": "spencer.bliven@gmail.com",
    "version": __version__,
    "tests_requires": ["pytest"],
    "install_requires": ["requests", "typing_extensions",],  # 3.6-3.7 only
    "extras": {"progressbar": "tqdm",},
    "packages": ["rcsbsearch"],
    "scripts": [],
}

setup(**config)
