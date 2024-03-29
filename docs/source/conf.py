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
sys.path.insert(0, os.path.abspath('../../'))


# -- Project information -----------------------------------------------------

project = 'shapeflow'
copyright = '2020, Yury Bondarenko'
author = 'Yury Bondarenko'

# The full version, including alpha/beta/rc tags
release = '0.4.3'


# -- General configuration ---------------------------------------------------


master_doc = 'index'

# Add any Sphinx extension module names here, as strings. They can be
# extensions coming with Sphinx (named 'sphinx.ext.*') or your custom
# ones.

import sphinx_rtd_theme

extensions = [
    'sphinx.ext.napoleon',
    'sphinx.ext.autodoc',
    'sphinx.ext.viewcode',
    'sphinx.ext.todo',
    'sphinx.ext.githubpages',
    'sphinx.ext.autosummary',
    'sphinxcontrib.autodoc_pydantic',
    'sphinx_rtd_theme',
]

# Complain about broken links
nitpicky = True

# Add any paths that contain templates here, relative to this directory.
templates_path = ['_templates']

# List of patterns, relative to source directory, that match files and
# directories to ignore when looking for source files.
# This pattern also affects html_static_path and html_extra_path.
exclude_patterns = []  #type: ignore

autodoc_member_order = 'bysource'
autosummary_generate = True

autodoc_pydantic_model_show_json = True
autodoc_pydantic_model_show_config_summary = False
autodoc_pydantic_model_show_config_member = False
autodoc_pydantic_model_show_validator_summary = False
autodoc_pydantic_model_show_field_summary = False
autodoc_pydantic_model_undoc_members = True
autodoc_pydantic_model_signature_prefix = "class"
autodoc_pydantic_validator_list_fields = True
autodoc_pydantic_config_signature_prefix = "class"
autodoc_pydantic_model_member_order = "bysource"


# -- autodoc configuration ---------------------------------------------------


# -- Options for HTML output -------------------------------------------------

# The theme to use for HTML and HTML Help pages.  See the documentation for
# a list of builtin themes.
#
# import sphinx_glpi_theme

html_theme = "sphinx_rtd_theme"
html_logo = "assets/shapeflow-white-text.svg"
html_theme_options = {
    'logo_only': True,
    'display_version': True,
    'prev_next_buttons_location': 'both',
}

# html_theme_path = sphinx_glpi_theme.get_html_themes_path()

# Add any paths that contain custom static files (such as style sheets) here,
# relative to this directory. They are copied after the builtin static files,
# so a file named "default.css" will overwrite the builtin "default.css".
html_static_path = ['assets']

html_css_files = [
    'custom.css'
]

html_context = {
    "display_github": True, # Integrate GitHub
    "github_user": "ybnd", # Username
    "github_repo": "https://github.com/ybnd/shapeflow", # Repo name
    "github_master": "version", # Version
    "conf_py_path": "/source/", # Path in the checkout to the docs root
}
