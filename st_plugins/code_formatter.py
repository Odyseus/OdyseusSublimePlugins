#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
*********************
Code formatter plugin
*********************

.. contextual-admonition::
    :context: info
    :title: Description

    Plugin to format code using external |CLI| tools.

.. contextual-admonition::
    :context: warning
    :title: Dependencies

    This plugin uses external |CLI| tools that can accept text read from **STDIN** and can output text to **STDOUT**.

.. contextual-admonition::
    :context: info
    :title: Mentions

    This plugin uses parts of several other plugins:

    - `Sublime EsFormatter <https://github.com/piuccio/sublime-esformatter>`__: |CLI| threaded execution is largely based on this plugin.
    - `JsFormat <https://github.com/jdavisclark/JsFormat>`__: Code merging is slightly based on this plugin.

.. contextual-admonition::
    :context: info
    :title: Available command

    - ``odyseus_code_formatter``: Possible arguments:

        + ``cmd_id`` (:py:class:`str`) (**Required**): A unique ID for the command. This ID will be used to locate the settings for the command.
        + ``save`` (:py:class:`bool`): Save file after formatting it.
        + ``ignore_selection`` (:py:class:`bool`): If set to **true**, the entire file will be formatted whether there are selections or not in the current file's view.

- This plugin is meant to be used from anywere in Sublime Text where a command can be defined and be *paired* with settings defined in the **OdyseusSublimePlugins.sublime-settings** settings file.
- Settings for this plugin are prefixed with ``code_formatter.``. Example:

    .. code-block:: json

        {
            "code_formatter.odyseus_js_beautify": {
                "exec_map": {
                    "linux": [{
                        "cmd": "/usr/local/bin/js-beautify",
                        "args": [
                            "--stdin",
                            "--operator-position=before-newline",
                            "--brace-style=collapse",
                            "-"
                        ]
                    }],
                    "osx": [],
                    "windows": []
                },
                "whole_file_not_allowed": "html",
                "is_visible": [
                    "javascript",
                    "html"
                ]
            }
        }

    The previous setting definition will affect the following keyboard shortcut:

    .. code-block:: javascript

        // Command defined as a keyboard shortcut.
        [{
            "keys": ["ctrl+alt+f"],
            "command": "odyseus_code_formatter",
            "args": {
                // Note that the value of "cmd_id" is used as part of the setting definition key
                // ("code_formatter.odyseus_js_beautify").
                "cmd_id": "odyseus_js_beautify",
                "save": true,                    // If one would want to save the file after formatting.
                "ignore_selection": true         // If one would want to always format the entire file.
            },
            "context": [{
                "key": "selector",
                "operator": "equal",
                "operand": "source.js"
            }]
        }]

- All settings are **optional** except when stated otherwise:

    + ``disabled`` (:py:class:`bool`): This is a convenience setting. If one has several commands defined in ``exec_map``, setting the ``is_visible`` for each command is just annoying. Setting ``disabled`` to **true** is the same as setting ``is_visible`` to **false** on each defined command.
    + ``exec_map`` (:py:class:`dict`) (**Required**): A dictionary with only three (3) keys (``linux``, ``osx``, and ``windows`` - see :ref:`command-executables-note-reference`); all of which are optional. Each of these keys should contain a list of dictionaries which can accept the following options.

        * ``cmd`` (:py:class:`str`) (**Required**): The command to run. It can be an executable name or the full path to an executable. See :ref:`common-variables-substitution-reference`.
        * ``args`` (:py:class:`list`): Arguments to pass to ``cmd``. See :ref:`common-variables-substitution-reference`.

    + ``whole_file_not_allowed`` (:py:class:`str` or :py:class:`list`): This setting is used to prevent formatting an entire file. Possible values:

        * A string or list of strings: If the current file's view matches a file syntax specified in this setting, formatting the whole file will be negated (see ``is_visible`` for details on defining syntaxes).

    + ``is_visible`` (:py:class:`bool`, :py:class:`str` or :py:class:`list`): Possible values:

        * A boolean: See :ref:`commands-visibility-note-reference`.
        * A string: A case insensitive name (partial match (e.g. **javascript**) or syntax file name (e.g. **JavaScript.sublime-syntax**)) of a file view's syntax.
        * A list of strings: A list of view syntaxes. It follows the same logic as setting a single string, but it allows to match several syntaxes.

"""
import os
import re
import threading

import sublime
import sublime_plugin

from . import display_message_in_panel
from . import logger
from . import settings
from python_utils import cmd_utils
from python_utils import misc_utils
from python_utils.sublime_text_utils import merge_utils
from python_utils.sublime_text_utils import utils


__all__ = [
    "OdyseusCodeFormatterCommand",
    "OdyseusUpdateContentCommand"
]

_error_template = """Working directory: `{cwd}`
Command `{cmd}`
```
{stderr}
```"""


def get_settings(cmd_id, default={}):
    """Get settings.

    Parameters
    ----------
    cmd_id : str
        Part of the key in the settings file that stores the settings for a plugin.
    default : dict, optional
        Default value in case the key storing a value isn't found.

    Returns
    -------
    dict
        This plugin settings.
    """
    return settings.get("code_formatter.%s" % cmd_id, default)


class ThreadCall(threading.Thread):
    """Thread.

    Attributes
    ----------
    error : str
        Error message.
    formatted_content : bool, str
        Formatted content.
    region : sublime.Region
        A Sublime Text region.
    text_content : str
        Text to pass to command for formatting.
    """

    def __init__(self, view, text_content, region=None, cmd_settings={}):
        """Initialization.

        Parameters
        ----------
        text_content : str
            Text to pass to command for formatting.
        region : None, sublime.Region, optional
            A Sublime Text region.
        cmd_settings : dict, optional
            Command settings.
        """
        self._view = view
        self._cmd_settings = cmd_settings

        self._file_path = utils.get_file_path(view)

        self._cmd = [cmd_settings.get("cmd", "")]
        self._cmd.extend(cmd_settings.get("args", []))
        self._cwd = cmd_settings.get("cwd") or \
            (os.path.dirname(self._file_path) if self._file_path else None)

        self.text_content = text_content.encode("utf-8")
        self.region = region
        self.formatted_content = None
        self.error = ""
        threading.Thread.__init__(self)

    def read_output(self, output):
        """Read output.

        Parameters
        ----------
        output : bytes
            stdout/stderr returned by subprocess.Popen.

        Returns
        -------
        str
            Encoded output,
        """
        return str(output, encoding="utf-8")

    def run(self):
        """Run thread.

        Raises
        ------
        RuntimeError
            Missing command.
        """
        try:
            if not self._cmd:
                msg = "No command defined."
                sublime.status_message(msg)
                raise RuntimeError(msg)

            # NOTE: Some CLI tools will throw errors when passing empty STDINs (mostly will print
            # usage). But since the errors are displayed in a popup, not executing the command
            # will avoid annoying popups display.
            if not self.text_content.strip():
                msg = "Empty STDIN."
                sublime.status_message(msg)
                raise RuntimeError(msg)

            sublime.status_message("Formatting file...")

            title = "OdyseusCodeFormatterCommand::ThreadCall"
            debug_msg = "\n".join([
                "Command ID: `%s`" % self._cmd_settings.get("cmd_id", "None"),
                "Working directory: `%s`" % self._cwd,
                "Command: `%s`" % " ".join(self._cmd)
            ])
            display_message_in_panel(self._view, title=title,
                                     body=debug_msg, file_path=self._file_path, debug=True)
            logger.debug("%s\n%s\n%s" % (title, self._file_path, debug_msg))

            with cmd_utils.popen(self._cmd,
                                 logger=logger,
                                 bufsize=160 * len(self.text_content),
                                 cwd=self._cwd) as proc:
                stdout, stderr = proc.communicate(self.text_content)

                if stderr:
                    self.formatted_content = False
                    self.error = _error_template.format(
                        cwd=self._cwd,
                        cmd=" ".join(self._cmd),
                        stderr=self.read_output(stderr)
                    )
                else:
                    self.formatted_content = self.read_output(stdout)

                    if self.region:
                        self.formatted_content = re.sub(
                            r"(\r|\r\n|\n)\Z", "", self.formatted_content)
        except Exception as err:
            self.formatted_content = False
            self.error = _error_template.format(
                cwd=self._cwd,
                cmd=" ".join(self._cmd),
                stderr=str(err)
            )


class OdyseusCodeFormatterCommand(sublime_plugin.TextCommand):
    """Code formatter.
    """

    def run(self, edit, **kwargs):
        """Action to perform when this Sublime Text command is executed.

        Parameters
        ----------
        edit : sublime.Edit
            sublime.Edit object.
        **kwargs
            Keyword arguments.

        Returns
        -------
        None
            Halt execution.
        """
        cmd_settings = self._ody_get_cmd_settings(kwargs.get("cmd_id"))

        if not cmd_settings:  # It might have "disabled" set to true.
            return

        if not cmd_settings["cmd"]:
            title = "%s: No command set or found." % self.__class__.__name__
            msg = "cmd_id: `%s`" % kwargs.get("cmd_id", "None")
            display_message_in_panel(self.view, title=title, body=msg)
            return

        # Store some extra data into cmd_settings so I don't have to pass a million parameters.
        cmd_settings["cmd_id"] = kwargs.get("cmd_id")

        if kwargs.get("ignore_selection", False) or \
            len(self.view.sel()) == 1 and self.view.sel()[0].empty() and \
                self._ody_format_whole_file_allowed(kwargs.get("cmd_id")):
            # Only one caret and no text selected, format the whole file
            text_content = self.view.substr(sublime.Region(0, self.view.size()))
            thread = ThreadCall(self.view, text_content, cmd_settings=cmd_settings)
            thread.start()
            self._ody_handle_thread(thread, lambda: self._ody_replace_file(
                thread, kwargs.get("save", False)))
        else:
            # Format each and every selection block
            threads = []
            for selection in self.view.sel():
                # Take only the user selection
                text_content = self.view.substr(selection)

                if text_content:
                    thread = ThreadCall(
                        self.view,
                        text_content,
                        region=selection,
                        cmd_settings=cmd_settings)
                    threads.append(thread)
                    thread.start()

            self._ody_handle_threads(threads, lambda process,
                                     last_error: self._ody_replace_selections(process, last_error))

    def _ody_replace_file(self, thread, save=False):
        """Replace the entire file content with the formatted text.

        Parameters
        ----------
        thread : ThreadCall
            Thread.
        save : bool, optional
            Whether to save file after being formatted.

        Returns
        -------
        None
            Halt execution. Do not make modifications if there are no changes.
        """
        if thread.text_content == thread.formatted_content.encode("utf-8"):
            sublime.status_message("No formatting required")
            return

        sublime.status_message("File formatted")

        self.view.run_command("odyseus_update_content", {
            "text": thread.formatted_content
        })

        if save:
            self.view.run_command("save")

    def _ody_replace_selections(self, threads, last_error):
        """Replace the content of a list of selections.

        This is called when there are multiple cursors or a selection of text

        Parameters
        ----------
        threads : list
            List of threads.
        last_error : str
            Error message.
        """
        if last_error:
            title = "%s Error:" % self.__class__.__name__
            display_message_in_panel(self.view, title=title, body=last_error)
        else:
            # Modify the selections from top to bottom to account for different text length
            offset = 0
            regions = []
            for thread in sorted(threads, key=lambda t: t.region.begin()):
                if thread.text_content == thread.formatted_content.encode("utf-8"):
                    continue

                if offset:
                    region = [thread.region.begin() + offset,
                              thread.region.end() + offset, thread.formatted_content]
                else:
                    region = [thread.region.begin(), thread.region.end(), thread.formatted_content]

                offset += len(thread.formatted_content) - len(thread.text_content)
                regions.append(region)

            if regions:
                self.view.run_command("odyseus_update_content", {
                    "regions": regions
                })
                sublime.status_message("Selections formatted")
            else:
                sublime.status_message("Nothing to format")

    def _ody_handle_thread(self, thread, callback):
        """Handle thread.

        Parameters
        ----------
        thread : ThreadCall
            Thread.
        callback : method
            Method to call if a thread execution was successful.
        """
        if thread and thread.is_alive():
            sublime.set_timeout(lambda: self._ody_handle_thread(thread, callback), 100)
        elif thread and thread.formatted_content is not False:
            callback()
        else:
            title = "%s Error:" % self.__class__.__name__
            display_message_in_panel(self.view, title=title, body=thread.error)

    def _ody_handle_threads(self, threads, callback, process=False, last_error=None):
        """Handle threads.

        Parameters
        ----------
        threads : list
            List of threads.
        callback : method
            Method to call if a thread execution was successful.
        process : bool, list, optional
            List of successfully executed threads ready to process.
        last_error : None, str, optional
            Error message.
        """
        next_threads = []
        if process is False:
            process = []

        for thread in threads:
            if thread.is_alive():
                next_threads.append(thread)
                continue

            if thread.formatted_content is False:
                # This thread failed
                last_error = thread.error
                continue

            # Thread completed correctly
            process.append(thread)

        if len(next_threads):
            # Some more threads to wait
            sublime.set_timeout(lambda: self._ody_handle_threads(
                next_threads, callback, process, last_error), 100)
        else:
            callback(process, last_error)

    def _ody_cmd_get_defaults(self):
        """Get default settings.

        Returns
        -------
        dict
            Default settings.
        """
        return {
            "cmd": "",
            "args": []
        }

    def _ody_get_cmd_settings(self, cmd_id):
        """Set settings.

        Parameters
        ----------
        cmd_id : str
            Command ID.

        Returns
        -------
        bool
            Halt execution.
        dict
            Command definition of an existent command.
        """
        if cmd_id is None or get_settings(cmd_id).get("disabled", False):
            return False

        settings_exec_map = utils.substitute_variables(
            utils.get_view_context(self.view),
            get_settings(cmd_id).get("exec_map", {}).get(sublime.platform(), [])
        )

        for _map in settings_exec_map:
            if "cmd" not in _map or not _map["cmd"]:
                continue

            # NOTE: The cmd_utils.can_exec is to not require the command to exist in PATH.
            # Let's see how it goes.
            if cmd_utils.can_exec(_map["cmd"]) or cmd_utils.which(_map["cmd"]):
                return misc_utils.merge_dict(self._ody_cmd_get_defaults(), _map)

        return False

    def _ody_format_whole_file_allowed(self, cmd_id):
        """Format whole file allowed.

        Parameters
        ----------
        cmd_id : str, optional
            Command ID.

        Returns
        -------
        bool
            If it is allowed to format the whole content of a file.
        """
        whole_file_not_allowed = get_settings(cmd_id).get("whole_file_not_allowed", False)

        if isinstance(whole_file_not_allowed, bool):
            return not whole_file_not_allowed
        else:
            return not utils.has_right_syntax(
                self.view, view_syntaxes=whole_file_not_allowed)

    def is_visible(self, **kwargs):
        """Set command visibility.

        Parameters
        ----------
        **kwargs
            Keyword arguments.

        Returns
        -------
        bool
            If the command should be visible.
        """
        cmd_settings = self._ody_get_cmd_settings(kwargs.get("cmd_id"))

        if not cmd_settings:  # It might have "disabled" set to true.
            return False

        is_visible = get_settings(kwargs.get("cmd_id")).get("is_visible", True)

        if isinstance(is_visible, bool):
            return is_visible
        else:
            return utils.has_right_syntax(self.view, view_syntaxes=is_visible)


class OdyseusUpdateContentCommand(sublime_plugin.TextCommand):
    """Update content.
    """

    def run(self, edit, text=None, regions=None):
        """Action to perform when this Sublime Text command is executed.

        Parameters
        ----------
        edit : sublime.Edit
            sublime.Edit object.
        text : None, str, optional
            Text to replace view content with.
        regions : None, sublime.Region, optional
            Sublime Text regions.
        """
        if text:
            self._ody_replace_whole_view(edit, text)
        elif regions:
            for region in regions:
                self.view.replace(edit, sublime.Region(region[0], region[1]), region[2])

    def _ody_replace_whole_view(self, edit, text):
        """Replace whole view.

        Parameters
        ----------
        edit : sublime.Edit
            sublime.Edit object.
        text : None, str, optional
            Text to replace view content with.
        """
        settings = self.view.settings()
        region = sublime.Region(0, self.view.size())
        code = self.view.substr(region)

        if settings.get("ensure_newline_at_eof_on_save") and not text.endswith("\n"):
            text = text + "\n"

        _, err = merge_utils.merge_code(self.view, edit, code, text)

        if err:
            title = "# %s Error: Merge failure:" % self.__class__.__name__
            display_message_in_panel(self.view, title=title, body=err)


if __name__ == "__main__":
    pass
