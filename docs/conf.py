# Configuration file for the Sphinx documentation builder.
#
# This file only contains a selection of the most common options. For a full
# list see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Path setup --------------------------------------------------------------

# If extensions (or modules to document with autodoc) are in another directory,
# add these directories to sys.path here. If the directory is relative to the
# documentation root, use os.path.abspath to make it absolute, like shown here.
#
import os
import sys
from recommonmark.transform import AutoStructify
import m2r

sys.path.insert(0, os.path.abspath(".."))
import rcsbsearch  # noqa: E402

# -- Project information -----------------------------------------------------

project = "rcsbsearch"
copyright = "2020, Spencer Bliven"
author = "Spencer Bliven"

# The version info for the project you're documenting, acts as replacement for
# |version| and |release|, also used in various other places throughout the
# built documents.
#
# The short X.Y version.
version = rcsbsearch.__version__
# The full version, including alpha/beta/rc tagss
release = rcsbsearch.__version__


# -- General configuration ---------------------------------------------------

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.coverage",
    "sphinx.ext.napoleon",
    "recommonmark",
    "sphinx_markdown_tables",
]
# source_suffix = [".rst", ".md"]  # Redundant with newer sphinx versions

# Add any paths that contain templates here, relative to this directory.
templates_path = ["_templates"]

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
html_theme = "sphinx_rtd_theme"


# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ["_static"]


# app setup hook

# We use commonmark+sphinx_markdown_tables for .md files and m2r for docstrings. This
# is inconsistent, but I couldn't get table support with other combinations.

# https://stackoverflow.com/a/56428123/81658
def docstring(app, what, name, obj, options, lines):
    "Use m2r for docstring parsing"
    md = "\n".join(lines)

    # Parse md -> rst with m2r
    rst = m2r.convert(md)

    lines.clear()
    lines.extend(rst.splitlines())


def setup(app):
    app.connect("autodoc-process-docstring", docstring)
    app.add_config_value(
        "recommonmark_config",
        {
            # 'url_resolver': lambda url: github_doc_root + url,
            "enable_auto_toc_tree": True,
            "auto_toc_tree_section": "Contents",
            "enable_math": False,
            "enable_inline_math": False,
            "enable_eval_rst": True,
        },
        True,
    )
    app.add_transform(AutoStructify)
