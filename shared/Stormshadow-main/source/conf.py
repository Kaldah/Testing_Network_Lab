# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'StormShadow'
copyright = '2025, Corentin COUSTY'
author = 'Corentin COUSTY'
release = '1.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = [
    'sphinx.ext.autodoc',      # automatically pull docstrings
    'sphinx.ext.autosummary',  # generate summary tables automatically
    'sphinx.ext.napoleon',     # support Google/NumPy-style docstrings
    'sphinx.ext.viewcode',     # add links to highlighted source code
    'sphinx.ext.intersphinx',  # cross-link to external docs
    'myst_parser',             # allow Markdown in docs
    'sphinx_copybutton',       # copy button for code blocks
]

templates_path = ['_templates']
exclude_patterns = []

# Autodoc / Napoleon / Autosummary settings for clean API pages
autosummary_generate = True
autodoc_member_order = 'bysource'
autodoc_typehints = 'description'  # show types in the description
add_module_names = False  # don't prefix objects with full module path
autodoc_default_options = {
    'members': True,
    'undoc-members': True,
    'show-inheritance': True,
}

napoleon_google_docstring = True
napoleon_numpy_docstring = True
napoleon_use_param = True
napoleon_use_rtype = False
napoleon_preprocess_types = True



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'furo'
html_static_path = ['_static']
html_title = 'StormShadow Documentation'
html_css_files = [
    'css/custom.css',  # optional extra tweaks
]

# Pygments (syntax highlighting) style
pygments_style = 'friendly'
pygments_dark_style = 'native'

# Theme options (Furo) to add brand color accents
from typing import Any, Dict, Tuple, Optional
html_theme_options: Dict[str, Any] = {
    "light_logo": None,
    "dark_logo": None,
    # Define CSS variables for light/dark modes
    "light_css_variables": {
        "color-brand-primary": "#0ea5a6",
        "color-brand-content": "#0b7285",
        "color-background-primary": "#ffffff",
    },
    "dark_css_variables": {
        "color-brand-primary": "#25c3c3",
        "color-brand-content": "#2dd4d4",
        "color-background-primary": "#0b1316",
    },
}

# Show class signature separately from the class name for readability
autodoc_class_signature = 'separated'

import os
import sys
sys.path.insert(0, os.path.abspath('..'))  # one level up from source/

# Intersphinx mappings for popular projects referenced in code
intersphinx_mapping: Dict[str, Tuple[str, Optional[str]]] = {
    'python': ('https://docs.python.org/3', None),
}

