#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
*******************************
Run command in all views plugin
*******************************

.. contextual-admonition::
    :context: info
    :title: Description

    Plugin that allows to execute any Sublime Text command (or those provided by any Sublime Text plugin) on all opened file views.

.. contextual-admonition::
    :context: info
    :title: Available command

    - ``odyseus_run_cmd_in_all_views``: Available arguments:

        + ``cmd`` (:py:class:`str`) (**Required**): The name of a Sublime Text command or that of a command provided by a Sublime Text plugin.
        + ``cmd_args`` (:py:class:`dict`): Arguments passed to the command defined in ``cmd``.
        + ``file_extensions`` (:py:class:`list`): A list of file extensions. The command defined in ``cmd`` will only execute on those opened files that matches these file extensions.
        + ``view_syntaxes`` (:py:class:`list`): A list of file syntaxes. The command defined in ``cmd`` will only execute on those opened files that matches these file syntaxes.
        + ``strict_syntax`` (:py:class:`bool`): If **true**, it will compare exact matches of file syntaxes. If not specified, **false**.

            .. note::

                The arguments ``file_extensions`` and ``view_syntaxes`` are mutually exclusive. Either one or the other can be specified, but not both. If both are specified, only ``file_extensions`` will be used. If neither is specified, a command will run in **all opened files without exceptions**.

- This command should not be used to create commands that can be executed from Sublime's command palette or from keyboard shortcuts. Imagine accidentally executing a command that can modify hundreds of opened files?!
- This command doesn't have configurable settings and can only be used when defined in Sublime menu/command files. Example:

    .. code-block:: json

        [{
            "caption": "Remove trailing spaces from all opened files",
            "command": "odyseus_run_cmd_in_all_views",
            "args": {
                "cmd": "delete_trailing_spaces"
            }
        }]

"""
import sublime  # noqa
import sublime_plugin

from python_utils.sublime_text_utils import utils

__all__ = [
    "OdyseusRunCmdInAllViewsCommand"
]

_error_msg = """{clsname} Error:
Failed to run command: <{cmd}>
Arguments: <{cmd_args}>
View: <{view}>"""


class OdyseusRunCmdInAllViewsCommand(sublime_plugin.WindowCommand):
    """Execute any command (from Sublime text or from other plugins)
    in all currently opened files.

    Parameters
    ----------
    cmd : str
        The command to execute.
    cmd_args : dict, optional
        The arguments to pass to the command **cmd**.
    file_extensions : list, optional
        File extensions on which to run the command **cmd**.

    Extends
    -------
    sublime_plugin.WindowCommand
    """

    def run(self, cmd="", cmd_args={}, file_extensions=[], view_syntaxes=[], strict_syntax=False):
        """Action to perform when this Sublime Text command is executed.

        Parameters
        ----------
        cmd : dict, optional
            A command string, whether it being a Sublime Text command or a Sublime Text plugin command.
        cmd_args : dict, optional
            Arguments to pass to the command to be executed.
        file_extensions : list, optional
            List of file extensions.
        view_syntaxes : list, optional
            List of syntaxes.
        strict_syntax : bool, optional
            Perform equality checks instead of membership checks when checking file syntaxes.

        Raises
        ------
        RuntimeError
            Halt execution.
        """
        if not cmd:
            raise RuntimeError("%s Error: No command was specified!" % self.__class__.__name__)

        for view in self.window.views():
            if file_extensions:
                allow_run = utils.has_right_extension(view, file_extensions)
            elif view_syntaxes:
                allow_run = utils.has_right_syntax(view, view_syntaxes, strict_syntax)
            else:
                # If neither "file_extensions" nor "view_syntaxes" are specified,
                # always run the command on all views.
                allow_run = True

            if allow_run:
                try:
                    view.run_command(cmd, args=cmd_args or None)
                except Exception as err:
                    raise RuntimeError(_error_msg.format(
                        clsname=self.__class__.__name__,
                        cmd=cmd,
                        cmd_args=repr(cmd_args),
                        view=utils.get_file_path(view)
                    )) from err


if __name__ == "__main__":
    pass
