#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
*************
General notes
*************

Commands added by plugins
=========================

All internal commands, classes, class' methods are prefixed with my nickname (Odyseus) or a variation of it to prevent clashes with other plugins or with Sublime's own Python code.

Plugin settings
===============

All plugin's settings can be overridden at project level. Plugin settings should be stored in a project settings inside a key called ``odyseus_plugins``. Example:

    .. code-block:: javascript

        "settings": {
            "odyseus_plugins": {
                // Plugin settings as found in OdyseusSublimePlugins.sublime-settings.
            }
        }

.. _commands-visibility-note-reference:

Commands visibility options
===========================

These options (normally called simply ``is_visible``) set the visibility of the commands (context menu item, command palette, etc.). It could be a boolean or a string.

- ``false``: Never display the command. Useful to hide default commands that one might not want to use nor to occupy space in a menu.
- ``true``: Ignore any command logic and display the command.
- Any other value of any type: Display command depending on the command's logic. How the value of the setting will be used to set a command visibility differs from command to command. Read the commands documentations below for details.

.. _command-executables-note-reference:

Command executables settings
============================

Settings storing executables (normally called simply ``exec_map``) are defined as dictionaries containing platform names (``linux``, ``osx``, and ``windows``). Example:

.. code-block:: javascript

    "search_with_zeal.exec_map": {
        "linux": [
            "/usr/bin/zeal"
        ],
        "osx": [],
        "windows": [
            "C:\\Program Files\\Zeal\\zeal.exe"
        ]
    }

- The command that will be executed will depend on the platform in which Sublime Text is used.
- Each of these platform settings is a list that can contain one or more command definitions. Depending on the plugin, commands could be defined as simple strings (a command name or path), or more complex definitions.
- Upon execution, a plugin will check for all commands existence in a system and execute the first one that checked as existent.

.. _common-variables-substitution-reference:

Variables substitution
======================

Some plugins' settings might make use of certain variables that can be replaced at run time. This can be very convenient for defining relative paths to executables, relative paths to configuration files, etc.

In addition to the following common variables set by Sublime Text, system environment variables are also expanded (see :py:class:`os.environ` and :py:class:`os.path.expanduser`).

A plugin can also define and use extra variables. See each plugin's documentation for details.

- ``${packages}``: The absolute path of the **Packages** folder inside a Sublime Text configuration directory.
- ``${file}``: The absolute path of a file's view. **(*)**
- ``${file_path}``: The absolute path of the folder containing a file's view. **(*)**
- ``${project_folder}``: A project's root folder. **(*)**

.. warning::

    **(*)** If a suitable path can't be ascertained, the variables will not be replaced.

"""
import os

import sublime
import sublime_plugin

root_folder = os.path.realpath(os.path.abspath(os.path.join(
    os.path.normpath(os.path.join(os.path.dirname(__file__), os.pardir)))))

from python_utils import log_system
from python_utils.sublime_text_utils import events
from python_utils.sublime_text_utils import logger as logger_utils
from python_utils.sublime_text_utils import settings as settings_utils
from python_utils.sublime_text_utils import utils


plugin_name = "OdyseusSublimePlugins"
_log_file = log_system.generate_log_path(storage_dir=os.path.join(root_folder, "tmp", "plugin_logs"),
                                         prefix="LOG")

logger = logger_utils.SublimeLogger(logger_name=plugin_name, log_file=_log_file)
settings = settings_utils.Settings(name_space=plugin_name, logger=logger)


def set_logging_level():
    try:
        logger.set_logging_level(logging_level=settings.get("general.logging_level", "ERROR"))
    except Exception as err:
        print(err)


@events.on("plugin_loaded")
def on_plugin_loaded():
    """On plugin loaded.
    """
    settings.load()
    set_logging_level()


@events.on("plugin_unloaded")
def on_plugin_unloaded():
    settings.unobserve()
    events.off(on_settings_changed)


@events.on("settings_changed")
def on_settings_changed(settings, **kwargs):
    if settings.has_changed("general.logging_level"):
        set_logging_level()


class ProjectSettingsController(utils.ProjectSettingsController,
                                sublime_plugin.EventListener):
    """Reload settings when project settings are changed.
    """

    def _on_post_save_async_callback(self):
        settings.load()


class SublimeConsoleController(utils.SublimeConsoleController,
                               sublime_plugin.EventListener):
    """Keep Sublime Text console always open on debug mode.
    """

    def _ody_display_console(self, view):
        if settings.get("general.persist_console"):
            super()._ody_display_console(view)


class OdyseusPluginsToggleLoggingLevelCommand(settings_utils.SettingsToggleList,
                                              sublime_plugin.WindowCommand):
    _ody_key = "general.logging_level"
    _ody_settings = settings
    _ody_description = "OdyseusPlugins - Logging level - %s"
    _ody_values_list = ["ERROR", "INFO", "DEBUG"]


def display_message_in_panel(view_or_window=None, title="", body="", file_path="", debug=False):
    if debug and settings.get("general.logging_level", "ERROR").lower() != "debug":
        return

    file_path = file_path
    msg = []

    if view_or_window is None:
        window = sublime.active_window()
    elif isinstance(view_or_window, sublime.View):
        window = view_or_window.window()
        file_path = utils.get_file_path(view_or_window)
    else:
        window = view_or_window

    if title:
        msg.append("# %s%s" % ("DEBUG::" if debug else "", str(title)))

    if file_path:
        msg.append("[File](%s)" % file_path)

    # Merge title and file path into the same item.
    # https://stackoverflow.com/a/1142879 <3
    if title and file_path:
        msg[:] = [" - ".join(msg[:])]

    if body:
        msg.append("\n%s\n" % str(body))

    if title and body:
        getattr(logger, "debug" if debug else "error")("%s\n%s" % (str(title), str(body)))

    if msg:
        msg = "\n".join(msg)

        if window:
            window.run_command("odyseus_display_message_in_panel", {"msg": "%s\n***" % msg})
        else:
            sublime.error_message(msg)


if __name__ == "__main__":
    pass
