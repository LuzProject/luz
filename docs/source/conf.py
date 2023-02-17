# Configuration file for the Sphinx documentation builder.
#
# For the full list of built-in configuration values, see the documentation:
# https://www.sphinx-doc.org/en/master/usage/configuration.html

# -- Project information -----------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#project-information

project = 'Luz'
copyright = '2023, Jaidan'
author = 'Jaidan'
release = '1.0.0'

# -- General configuration ---------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#general-configuration

extensions = ['sphinx_copybutton']
copybutton_prompt_text = "$ "
templates_path = ['_templates']
exclude_patterns = []



# -- Options for HTML output -------------------------------------------------
# https://www.sphinx-doc.org/en/master/usage/configuration.html#options-for-html-output

html_theme = 'furo'

html_theme_options = {
    "sidebar_hide_name": True,
    "navigation_with_keys": True,
    "light_logo": "img/logo-light.png",
    "dark_logo": "img/logo-dark.png",
}

html_css_files = [
    'css/style.css',
]

html_static_path = ['_static']