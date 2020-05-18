#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
*************************
Compare open files plugin
*************************

.. contextual-admonition::
    :context: info
    :title: Description

    Plugin to compare opened files with an external program.

.. contextual-admonition::
    :context: info
    :title: Available commands

    - ``odyseus_compare_two_files``: Compare two opened files.
    - ``odyseus_compare_three_files``: Compare three opened files.

- The files selection is automatic. Just focus the tabs of the 2/3 files that one wants to compare and immediately execute the proper command from the command palette (or a keyboard shortcut).
- Settings for this plugin are prefixed with ``compare_open_files.``. Available option:

    + ``exec_map`` (:py:class:`dict`): See :ref:`command-executables-note-reference`.

"""
import os

import sublime
import sublime_plugin

from . import display_message_in_panel
from . import settings
from python_utils import cmd_utils
from python_utils.sublime_text_utils import utils

__all__ = [
    "OdyseusCompareFileListener",
    "OdyseusCompareThreeFilesCommand",
    "OdyseusCompareTwoFilesCommand"
]
_file_a = None
_file_b = None
_file_c = None
_recording = False

_selected_files_base_error_msg = """You must have activated **{number}** files to compare.
Please select **{number}** tabs to compare and try again."""


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
    return settings.get("compare_open_files.%s" % s, default)


def record_active_file(last_file, reset=False):
    """Record active file-

    Parameters
    ----------
    last_file : str
        The path to the file from the last active view.
    reset : bool, optional
        Set all the stored file paths to None.

    Returns
    -------
    None
        Halt function execution.
    """
    global _recording
    global _file_a
    global _file_b
    global _file_c

    if _recording:
        return

    _recording = True

    _file_c = None if reset else _file_b
    _file_b = None if reset else _file_a
    _file_a = None if reset else last_file

    _recording = False


def run_comparison(three_way_comparison, cls_name):
    """Run comparison.

    Parameters
    ----------
    three_way_comparison : bool
        Whether to compare three files or just two.
    """
    diff_exec = utils.get_executable_from_settings(
        None, get_settings("exec_map").get(sublime.platform(), []))

    selected_files_error_msg = _selected_files_base_error_msg.format(
        number="THREE" if three_way_comparison else "TWO"
    )
    cwd = os.path.dirname(diff_exec)
    cwd = cwd if os.path.isdir(cwd) else os.path.expanduser("~")
    correct_files_lenght = True

    if diff_exec:
        if three_way_comparison:
            if all([_file_a is not None, _file_b is not None, _file_c is not None]):
                cmd_utils.popen([diff_exec, _file_a, _file_b, _file_c], cwd=cwd)
            else:
                correct_files_lenght = False
        else:
            if all([_file_a is not None, _file_b is not None]):
                cmd_utils.popen([diff_exec, _file_a, _file_b], cwd=cwd)
            else:
                correct_files_lenght = False

        if not correct_files_lenght:
            title = "%s Error:" % cls_name
            display_message_in_panel(title=title, body=selected_files_error_msg)
        else:
            record_active_file("", reset=True)
    else:
        title = "%s Error:" % cls_name
        msg = "Please try again after you have command line tools installed."
        display_message_in_panel(title=title, body=msg)


class OdyseusCompareTwoFilesCommand(sublime_plugin.ApplicationCommand):
    """Command to compare two files.
    """

    def run(self):
        """Action to perform when this Sublime Text command is executed.
        """
        run_comparison(three_way_comparison=False, cls_name=self.__class__.__name__)


class OdyseusCompareThreeFilesCommand(sublime_plugin.ApplicationCommand):
    """Command to compare three files.
    """

    def run(self):
        """Action to perform when this Sublime Text command is executed.
        """
        run_comparison(three_way_comparison=True, cls_name=self.__class__.__name__)


class OdyseusCompareFileListener(sublime_plugin.EventListener):
    """Event listener for when a view is activated.
    """

    def on_activated(self, view):
        """Action to perform when a view is activated.

        Parameters
        ----------
        view : object
            A Sublime Text view.
        """
        filename = utils.get_file_path(view)

        if filename and filename != _file_a:
            record_active_file(view.file_name())


if __name__ == "__main__":
    pass
