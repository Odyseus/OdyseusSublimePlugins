#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
*******************************
Sidebar context commands plugin
*******************************

.. contextual-admonition::
    :context: info
    :title: Description

    Plugin to create Sublime Text's sidebar context menu items that execute commands using the selected paths in the sidebar.

.. contextual-admonition::
    :context: info
    :title: Available command

    - ``odyseus_exec_command_on_sidebar_selection``: Possible arguments:

        + ``cmd_id`` (:py:class:`str`) (**Required**): A unique ID for the command. This ID will be used to locate the settings for the command.
        + ``dirs`` (:py:class:`list`): The list of selected folders in the sidebar.
        + ``files`` (:py:class:`list`): The list of selected files in the sidebar.
        + ``paths`` (:py:class:`list`): The list of selected files and folders in the sidebar.

            * The ``dirs``, ``files`` and ``paths`` arguments are populated by Sublime Text when one selects files/folders in the sidebar. Which of the selected paths are used when executing the command depends on the command setting ``path_type``.
            * There is no need to specify the three arguments, just the one that is needed.

- This command is meant to be used only from the sidebar context menu and should be used in menu items definitions in a **Side Bar.sublime-menu** file and *paired* with settings defined in the **OdyseusSublimePlugins.sublime-settings** settings file.
- They work and make use of the sidebar selected paths whether they are files, folders or both depending on configuration.
- Settings for this plugin are prefixed with ``sidebar_context_commands.``. Example:

    .. code-block:: json

        {
            "sidebar_context_commands.odyseus_open_git_gui_sidebar_context": {
                "exec_map": {
                    "linux": [{
                        "cmd": "/usr/bin/git",
                        "args": ["gui"],
                        "exec_once": false,
                        "path_type": "folder"
                    }],
                    "osx": [],
                    "windows": []
                }
            }
        }

    The previous setting definition will affect the following menu item defined in the **Side Bar.sublime-menu** file:

    .. code-block:: javascript

        {
            "caption": "Git Gui",
            "command": "odyseus_exec_command_on_sidebar_selection",
            "args": {
                // Note that the value of "cmd_id" is used as part of the setting definition key
                // ("sidebar_context_commands.odyseus_open_git_gui_sidebar_context").
                "cmd_id": "odyseus_open_git_gui_sidebar_context",
                "dirs": []
            }
        }

- All settings are **optional** except when stated otherwise:

    + ``disabled`` (:py:class:`bool`): This is a convenience setting. If one has several commands defined in ``exec_map``, setting the ``is_visible`` for each command is just annoying. Setting ``disabled`` to **true** is the same as setting ``is_visible`` to **false** on each defined command.
    + ``exec_map`` (:py:class:`dict`) (**Required**): A dictionary with only three (3) keys (``linux``, ``osx``, and ``windows`` - see :ref:`command-executables-note-reference`); all of which are optional. Each of these keys should contain a list of dictionaries which can accept the following options.

        * ``cmd`` (:py:class:`str`) (**Required**): The command to run. It can be an executable name or the full path to an executable. See :ref:`common-variables-substitution-reference`.
        * ``args`` (:py:class:`list`): Arguments to pass to ``cmd``. Special variable ``${selected_sidebar_path}`` will be replaced with path of selected file/folder in sidebar. If ``exec_once`` is **true**, ``${selected_sidebar_path}`` variables defined here will be ignored. See :ref:`common-variables-substitution-reference`.
        * ``exec_once`` (:py:class:`bool`): Whether to execute the command once with all selected paths passed as arguments (if ``pass_path_to_cmd`` is set accordingly to **true** or a string), or run the command for each selected path. If not specified, **false**.
        * ``is_visible`` (:py:class:`bool`, :py:class:`list` or :py:class:`int`): Possible values:

            - A boolean: See :ref:`commands-visibility-note-reference`.
            - A list: A list of strings representing comparisons. Possible comparisons are ``<=`` (less than or equal to), ``>=`` (greater than or equal to), and ``!=`` (not equal to). Example: ``[">=2", "<=3"]`` (the command will be visible only if there are 2 or 3 files/folders selected).

                .. note::

                    I purposely left out the  ``<``, ``=``, and ``>`` comparisons for programmatic reasons (mostly laziness). But either operation can be achieved with the available operations.

            - An integer: The exact number of selected paths on the sidebar that should be selected for the command to be displayed.
            - If not specified: The command will be visible if the option ``allow_multiple`` is set to **true** and any amount of paths are selected in the sidebar. If ``allow_multiple`` is set to **false**, the command will be visible only if one (1) path is selected.

        * ``allow_multiple`` (:py:class:`bool`): Allow the command to displayed when multiple paths are selected in the sidebar. If not specified, **true**.
        * ``report_stdout`` (:py:class:`bool`): After executing the command defined in ``cmd`` on all selected paths, display a file in a new view with the resulting output, if any. If not specified, **false**.
        * ``pass_path_to_cmd`` (:py:class:`bool`): Whether to pass path of selected file/folder as an argument to ``cmd``. If not specified, **false**.
        * ``path_type`` (:py:class:`str`): One of **folder**, **file** or **both**. Used to decide which of the selected items in the sidebar will be used to execute the command defined in ``cmd``. If not specified, **both**.

            - ``folder``: If there are files and folders selected in the sidebar, the **files** will be ignored.
            - ``file``: If there are files and folders selected in the sidebar, the **folders** will be ignored.
            - ``both``: **All** selected files and folders will be used.

        * ``dry_run`` (:py:class:`bool`): Do not execute the command/s, log it/them to console. If not specified, **false**. This will print to Sublime's console the full command/s that will be executed, the directory that will be used as working directory when the command/s is/are executed and the settings that were used to construct the command/s.

How to create new menu items in the sidebar?
============================================

#. Define a new menu entry in the **Side Bar.sublime-menu** file.

    .. code-block:: json

        [{
            "caption": "My menu intem in sidebar context",
            "command": "odyseus_exec_command_on_sidebar_selection",
            "args": {
                "cmd_id": "unique_command_id",
                "files": []
            }
        }]

#. Add the command definition in the **OdyseusSublimePlugins.sublime-settings** settings file.

    .. code-block:: javascript

        {
            "sidebar_context_commands.unique_command_id": {
                "exec_map": {
                    "linux": [
                        // Command definitions.
                    ],
                    "osx": [
                        // Command definitions.
                    ],
                    "windows": [
                        // Command definitions.
                    ]
                }
            }
        }

"""
import json
import operator
import os

from multiprocessing import Process
from threading import Thread

import sublime
import sublime_plugin

from . import display_message_in_panel
from . import logger
from . import plugin_name
from . import settings
from python_utils import cmd_utils
from python_utils import misc_utils
from python_utils.sublime_text_utils import utils

__all__ = [
    "OdyseusExecCommandOnSidebarSelectionCommand"
]

_msg_template = """Working directory: `{cwd}`
Command: `{cmd}`
Command output:
```
{cmd_output}
```"""

_error_template = """Working directory: `{cwd}`
Command `{cmd}`
```
{stderr}
```"""
_operations = [
    "<=", ">=", "!="
]
_all_operations = [
    "<", "=", ">"
].extend(_operations)
_operations_map = {
    "<=": operator.le, ">=": operator.ge, "!=": operator.ne
}
_all_operations_map = misc_utils.merge_dict({
    "<": operator.lt, "=": operator.eq, ">": operator.gt
}, _operations_map)


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
    return settings.get("sidebar_context_commands.%s" % cmd_id, default)


class ThreadCall(Thread):

    def __init__(self, cmd=[], cwd=None):
        self._cmd = cmd
        self._cwd = cwd
        self.command_output = None
        self.error = ""
        Thread.__init__(self)

    def read_output(self, output):
        return str(output, encoding="utf-8")

    def run(self):
        try:
            with cmd_utils.popen(self._cmd, logger=logger, cwd=None) as proc:
                stdout, stderr = proc.communicate()

                if stderr:
                    self.command_output = None
                    self.error = _error_template.format(
                        cwd=str(self._cwd),
                        cmd=" ".join(self._cmd),
                        stderr=self.read_output(stderr)
                    )
                else:
                    self.command_output = _msg_template.format(
                        cwd=str(self._cwd),
                        cmd=" ".join(self._cmd),
                        cmd_output=self.read_output(stdout)
                    )
        except Exception as err:
            self.command_output = None
            self.error = _error_template.format(
                cwd=str(self._cwd),
                cmd=" ".join(self._cmd),
                stderr=str(err)
            )


class OdyseusExecCommandOnSidebarSelectionCommand(sublime_plugin.WindowCommand):
    """Execute a command on the sidebar.
    """

    def run(self, **kwargs):
        """Action to perform when this Sublime Text command is executed.

        Parameters
        ----------
        **kwargs
            Keyword arguments.

        Returns
        -------
        None
            Halt execution.
        """
        cmd_id = kwargs.get("cmd_id")
        cmd_settings = self._ody_get_settings(cmd_id)

        if not cmd_settings or not cmd_settings["cmd"]:
            title = "%s: No command set or found." % self.name()
            msg = "# cmd_id: %s" % str(cmd_id)
            display_message_in_panel(self.window, title=title, body=msg)
            return

        cmd = [utils.substitute_variables(
            utils.get_view_context(None), cmd_settings["cmd"]
        )]
        args = cmd_settings["args"]
        report_stdout = cmd_settings["report_stdout"]
        pass_path_to_cmd = cmd_settings["pass_path_to_cmd"]
        allow_multiple = cmd_settings["allow_multiple"]
        path_type = cmd_settings["path_type"]
        exec_once = cmd_settings["exec_once"]
        working_directory = cmd_settings["working_directory"] if \
            os.path.isdir(cmd_settings["working_directory"]) else \
            None
        self._ody_stdout_storage = []

        if path_type == "folder":
            selected_paths = kwargs.get("dirs", [])
        elif path_type == "file":
            selected_paths = kwargs.get("files", [])
        else:
            selected_paths = kwargs.get("paths", [])

        if selected_paths:
            # exec_func = ThreadCall if report_stdout else Process
            threads = []
            # NOTE: Make a copy of original. It doesn't matter if a change in the original modifies the copy,
            # what matters is that a change in the copy doesn't change the original.
            command = cmd[:]
            command.extend(args)

            for path in selected_paths:
                # Build a single command with all selected paths to run once.
                if exec_once and allow_multiple and pass_path_to_cmd:
                    if isinstance(pass_path_to_cmd, str):
                        command.append(pass_path_to_cmd + path)
                    else:
                        command.append(path)
                else:  # Run command for each selected path.
                    arguments = utils.substitute_variables(
                        utils.get_view_context(None, additional_context={
                            "selected_sidebar_path": path
                        }), args
                    )

                    if pass_path_to_cmd is True:
                        arguments.append(path)

                    if report_stdout:
                        thread = ThreadCall(cmd=cmd + arguments, cwd=working_directory)
                        threads.append(thread)
                        thread.start()

                        self._ody_handle_threads(threads, lambda process,
                                                 last_error: self._ody_handle_output(process, last_error))
                    else:
                        proc = Process(target=self._ody_proc_exec, args=(cmd + arguments,), kwargs={
                            "cmd_id": str(cmd_id),
                            "cmd_settings": cmd_settings,
                            "cwd": path if os.path.isdir(path) else os.path.dirname(path)
                        })
                        proc.start()

            if exec_once and command:
                if report_stdout:
                    thread = ThreadCall(cmd=command, cwd=working_directory)
                    threads.append(thread)
                    thread.start()

                    self._ody_handle_threads(threads, lambda process,
                                             last_error: self._ody_handle_output(process, last_error))
                else:
                    proc = Process(target=self._ody_proc_exec, args=(command,), kwargs={
                        "cmd_id": str(cmd_id),
                        "cmd_settings": cmd_settings,
                        "cwd": working_directory
                    })

                    proc.start()
        else:
            sublime.status_message("No valid path/s selected.")

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

            if thread.command_output is None:
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

    def _ody_handle_output(self, threads, last_error):
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
            display_message_in_panel(self.window, title=title, body=last_error)
        else:
            for thread in threads:
                self._ody_stdout_storage.append(thread.command_output)

        self._ody_display_new_view()

    def _ody_proc_exec(self, *args, cmd_settings={}, cmd_id="None", **kwargs):
        """Execute command.

        Parameters
        ----------
        *args
            Arguments.
        cmd_settings : dict, optional
            Command settings.
        **kwargs
            Keyword arguments.

        Returns
        -------
        None
            Halt execution.
        """
        if cmd_settings["dry_run"]:
            try:
                print("\n".join([self.name(),
                                 "Command that will be executed:",
                                 " ".join(*args),
                                 "Working directory:",
                                 kwargs["cwd"],
                                 "Command settings:",
                                 json.dumps(cmd_settings, indent=4)]))
            except Exception as err:
                display_message_in_panel(self.window, title=self.name(), body=err)

            return

        with cmd_utils.popen(*args, **kwargs) as proc:
            stderr = proc.stderr.read().decode("utf-8").strip()

            if stderr:
                title = "%s: Error: cmd_id = %s" % (self.name(), cmd_id)
                display_message_in_panel(self.window, title=title, body=stderr)

    def _ody_display_new_view(self):
        """Display new view.
        """
        if self._ody_stdout_storage:
            view = self.window.new_file()
            view.set_scratch(True)
            view.set_name("%s report.md" % self.name())

            try:
                view.assign_syntax(
                    "Packages/%s/st_plugins/message_panel/OSP-message_panel.sublime-syntax" % plugin_name
                )
            except Exception as err:
                logger.exception(err)

            view.run_command("append", {
                "characters": "\n".join(self._ody_stdout_storage)
            })

    def _ody_get_defaults(self):
        """Get default settings.

        Returns
        -------
        dict
            Default settings.
        """
        return {
            "cmd": "",
            "args": [],
            "exec_once": False,
            # "auto" is a dummy value that it isn't a bool, list or int used to coerce automatic
            # length calculation.
            "is_visible": "auto",
            "allow_multiple": True,
            "report_stdout": False,
            "pass_path_to_cmd": False,
            "path_type": "both",
            "working_directory": os.path.expanduser("~"),
            "dry_run": False
        }

    def _ody_get_settings(self, cmd_id):
        """Set settings.

        Parameters
        ----------
        cmd_id : str
            Command ID.

        Returns
        -------
        None
            Halt execution.
        """
        if cmd_id is None or get_settings(cmd_id).get("disabled", False):
            return False

        settings_exec_map = get_settings(cmd_id).get("exec_map", {}).get(sublime.platform(), [])

        for _map in settings_exec_map:
            if "cmd" not in _map or _map.get("is_visible", "auto") is False:
                continue

            cmd = utils.substitute_variables(
                utils.get_view_context(None), _map["cmd"])

            if cmd_utils.can_exec(cmd) or cmd_utils.which(cmd):
                return misc_utils.merge_dict(self._ody_get_defaults(), _map)

        return False

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
        cmd_settings = self._ody_get_settings(kwargs.get("cmd_id"))

        if not cmd_settings:
            return False

        path_type = cmd_settings["path_type"]

        if path_type == "folder":
            p = kwargs.get("dirs", [])
        elif path_type == "file":
            p = kwargs.get("files", [])
        else:
            p = kwargs.get("paths", [])

        is_visible = cmd_settings["is_visible"]

        if isinstance(is_visible, bool):
            return is_visible
        elif isinstance(is_visible, (list, int)):
            return is_correct_length(len(p), is_visible)

        return len(p) > 0 if cmd_settings["allow_multiple"] else len(p) == 1


def is_correct_length(val, conditions=[]):
    """Is correct length.

    Parameters
    ----------
    val : int
        The integer value to check.
    conditions : list, int, optional
        List of conditions or integer to check against.

    Returns
    -------
    bool
        If the value is between the desired parameters.
    """
    cnds = []

    if isinstance(conditions, int):
        return val == conditions

    try:
        for o in _operations:
            for c in conditions:
                if o in c:
                    _, c_val = c.split(o)
                    cnds.append(_operations_map[o](val, int(c_val)))
    except Exception as err:
        logger.exception(err)

    return all(cnds)


if __name__ == "__main__":
    pass
