"""Sphinx configuration for FlameIQ documentation."""

import os
import sys

sys.path.insert(0, os.path.abspath("../.."))

# ── Project ───────────────────────────────────────────────────────────────────
project = "FlameIQ"
copyright = "2026, FlameIQ Contributors"
author = "FlameIQ Contributors"
release = "1.0.0"
version = "1.0"

# ── Extensions ────────────────────────────────────────────────────────────────
extensions = [
    "sphinx.ext.autodoc",
    "sphinx.ext.napoleon",
    "sphinx.ext.viewcode",
    "sphinx.ext.intersphinx",
    "sphinx.ext.todo",
    "sphinx.ext.autosummary",
]

# ── Source ────────────────────────────────────────────────────────────────────
templates_path = ["_templates"]
exclude_patterns = ["_build", "Thumbs.db", ".DS_Store"]
source_suffix = ".rst"
master_doc = "index"

# ── HTML Output ───────────────────────────────────────────────────────────────
html_theme = "sphinx_rtd_theme"
html_static_path = ["_static"]

html_theme_options = {
    "logo_only": False,
    "navigation_depth": 4,
    "collapse_navigation": False,
    "sticky_navigation": True,
    "includehidden": True,
    "titles_only": False,
    "prev_next_buttons_location": "both",
}

html_context = {
    "display_github": True,
    "github_user": "flameiq",
    "github_repo": "flameiq-core",
    "github_version": "main",
    "conf_py_path": "/docs/source/",
}

html_show_sourcelink = True
html_show_sphinx = True

# ── autodoc ───────────────────────────────────────────────────────────────────
autodoc_default_options = {
    "members": True,
    "member-order": "bysource",
    "special-members": "__init__, __post_init__",
    "undoc-members": False,
    "show-inheritance": True,
    "inherited-members": False,
}
autodoc_typehints = "description"
autodoc_typehints_format = "short"
autoclass_content = "both"

# ── Napoleon (Google-style docstrings) ────────────────────────────────────────
napoleon_google_docstring = True
napoleon_numpy_docstring = False
napoleon_include_init_with_doc = True
napoleon_include_private_with_doc = False
napoleon_include_special_with_doc = True
napoleon_use_admonition_for_examples = True
napoleon_use_admonition_for_notes = True

# ── intersphinx ───────────────────────────────────────────────────────────────
intersphinx_mapping = {
    "python": ("https://docs.python.org/3.12", None),
}

# ── todo ──────────────────────────────────────────────────────────────────────
todo_include_todos = True
