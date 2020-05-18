#!/usr/bin/python3
# -*- coding: utf-8 -*-
import sublime
import sublime_plugin

from . import display_message_in_panel
from . import logger
from . import settings
from python_utils import fix_imports
from python_utils.sublime_text_utils import merge_utils
from python_utils.sublime_text_utils import utils

__all__ = [
    "OdyseusFixPythonImportsCommand"
]


def get_settings(s, default={}):
    """Get settings.

    Parameters
    ----------
    s : str
        Part of the key in the settings file that stores the settings for a plugin.
    default : dict, optional
        Default value in case the key storing a value isn't found.

    Returns
    -------
    dict
        This plugin settings.
    """
    return settings.get("fix_python_imports.%s" % s, default)


class OdyseusFixPythonImportsCommand(sublime_plugin.TextCommand):

    def run(self, edit):
        if not utils.has_right_syntax(self.view, view_syntaxes="python"):
            return

        replace_region = self.view.line(sublime.Region(0, self.view.size()))
        source = self.view.substr(replace_region)

        logger.debug("Reorganizing file")
        split_import_statements = get_settings("split_import_statements", True)
        sort_import_statements = get_settings("sort_import_statements", True)
        logger.debug("Options")
        logger.debug("split_import_statements = {!r}".format(split_import_statements))
        logger.debug("sort_import_statements = {!r}".format(sort_import_statements))

        _res, fixed = fix_imports.FixImports().sortImportGroups(
            "filename", source,
            splitImportStatements=split_import_statements,
            sortImportStatements=sort_import_statements
        )
        _is_dirty, err = merge_utils.merge_code(self.view, edit, source, fixed)

        if err:
            title = "# %s Error: Merge failure:" % self.__class__.__name__
            display_message_in_panel(self.view, title=title, body=err)
            raise


if __name__ == "__main__":
    pass
