#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
********************
Message panel plugin
********************

.. contextual-admonition::
    :context: info
    :title: Description

    Plugin to display messages in a Sublime Text panel.

.. contextual-admonition::
    :context: info
    :title: Available commands

    - ``odyseus_display_message_in_panel``: Possible arguments:

        + ``msg`` (:py:class:`str`): The message to display in the panel.

    - ``odyseus_clear_message_panel``
    - ``odyseus_remove_message_panel``
    - ``odyseus_toggle_message_panel``

.. contextual-admonition::
    :context: info
    :title: Notes

    - A custom syntax is used (basically, a Markdown syntax with a limited set of Markdown markup) to highlight the panel view. The syntax is accompanied by a settings file that disables certain features to make the panel view *light on the eyes*.
    - The messages in the panel are time stamped and persistent for the life time of the panel (not across Sublime Text sessions).
    - Certain paths (marked up like Markdown links. e.g. ``[File](/path/to/file)``) are specially handled. They can be opened in Sublime Text by double clicking on them. They will also have a tooltip with the options **Edit file** (same as double clicking on it) and **Launch file** (to open the file in the system's file handler for that file).


Note
----
Borrowed from SublimeLinter.
"""
import os

import sublime
import sublime_plugin

from python_utils import misc_utils
from .. import plugin_name
from python_utils import cmd_utils
from python_utils.sublime_text_utils import events


__all__ = [
    "OdyseusClearMessagePanelCommand",
    "OdyseusDisplayMessageInPanelCommand",
    "OdyseusOpenFileFromPanelListener",
    "OdyseusRemoveMessagePanelCommand",
    "OdyseusToggleMessagePanelCommand",
    "__odyseus_clear_message_panel_content"
]

_panel_id = ""
_panel_name = plugin_name + "MessagePanel"
_output_panel = "output." + _panel_name
# NOTE: The regular expression matches a markdown link. Either on its own
# line or at the end of a heading.
_path_region_regex = r"^(\[File\]\(|#.*?\]\()(.*?)\)$"
_date_region_regex = r"^\*\*\d{4}\-\d{2}\-\d{2} \d{2}:\d{2}:\d{2}\.\d{6}\*\*$"
_panel_syntax = "Packages/%s/st_plugins/message_panel/OSP-message_panel.sublime-syntax" % plugin_name
_tooltip_template = """
<body id="odyseus-message-view-tooltip">
    <div><a href="edit-file">Edit file</a> - <a href="launch-file">Launch file</a></div>
</body>
"""


@events.on("plugin_loaded")
def on_plugin_loaded():
    """On plugin loaded.
    """
    ensure_panel(sublime.active_window())


@events.on("plugin_unloaded")
def on_plugin_unloaded():
    for window in sublime.windows():
        window.destroy_output_panel(_panel_name)


class OdyseusDisplayMessageInPanelCommand(sublime_plugin.WindowCommand):
    """Display message panel.
    """

    def run(self, msg=""):
        """Action to perform when this Sublime Text command is executed.

        Parameters
        ----------
        msg : str, optional
            Message to append to the panel view.
        """
        msg = "**%s**\n%s" % (misc_utils.get_date_time(), msg)
        panel = ensure_panel(self.window)

        scroll_to = panel.size()

        global _panel_id
        _panel_id = panel.id()

        panel.set_read_only(False)
        panel.erase_regions(_output_panel)  # I don't know if these are needed, but just in case.
        panel.erase_regions(_output_panel + "-icons")
        panel.run_command("append", {
            "characters": msg.strip() + "\n"
        })
        path_regions = self._ody_get_modified_paths_regions(panel)
        panel.add_regions(_output_panel, path_regions, "region.bluish",
                          flags=sublime.DRAW_SOLID_UNDERLINE | sublime.DRAW_NO_OUTLINE | sublime.DRAW_NO_FILL)
        panel.add_regions(_output_panel + "-icons", panel.find_all(_date_region_regex),
                          "region.redish", icon="circle", flags=sublime.HIDDEN)
        panel.set_read_only(True)
        panel.show(scroll_to)
        self.window.run_command("show_panel", {
            "panel": _output_panel
        })

    def _ody_get_modified_paths_regions(self, panel):
        """Get modified regions.

        Parameters
        ----------
        panel : object
            A sublime.View object.

        Returns
        -------
        list
            List  of modified regions.
        """
        paths = []
        mod_regions = []
        regions = panel.find_all(_path_region_regex, fmt=r"\2", extractions=paths)

        for i, r in enumerate(regions):
            mod_regions.append(sublime.Region(
                r.end() - len(paths[i]) - 1,
                r.end() - 1
            ))

        return mod_regions


class OdyseusRemoveMessagePanelCommand(sublime_plugin.WindowCommand):
    """Remove message panel.
    """

    def run(self):
        """Action to perform when this Sublime Text command is executed.
        """
        self.window.destroy_output_panel(_panel_name)


class OdyseusClearMessagePanelCommand(sublime_plugin.WindowCommand):
    """Remove message panel.
    """

    def run(self):
        """Action to perform when this Sublime Text command is executed.
        """
        panel = ensure_panel(self.window)
        panel.run_command("__odyseus_clear_message_panel_content")


class OdyseusToggleMessagePanelCommand(sublime_plugin.WindowCommand):
    """Summary
    """

    def run(self):
        """Summary
        """
        ensure_panel(self.window)

        if panel_is_active(self.window):
            self.window.run_command("hide_panel", {"panel": _output_panel})
        else:
            self.window.run_command("show_panel", {"panel": _output_panel})


class OdyseusOpenFileFromPanelListener(sublime_plugin.EventListener):
    """Open file view.

    The panel messages will sometimes have specified the file that generated a message. I wanted
    to be able to directly open those files in Sublime Text by simply double clicking on them.
    I wanted to achieve something similar to what SublimeLinter does (when double clicking on
    an error line on SublimeLinter's panel view, it will move to that file's line), but I
    couldn't figure out how it is done there (it's a very complex plugin!). So, like always, I did
    it in the most naive way that I could come up with. I "hijacked" `on_text_command`
    with a debounce, if a double click is performed inside the assigned region for a path, the
    file will be opened in Sublime Text. This is just a very "hacky" way, but it does what I
    want it to do.

    NOTE
    ----
    I already figured out how SublimeLinter does it. SublimeLinter seems to use the absolutely
    obscure view settings called ``result_file_regex`` and ``result_line_regex`` which are of no
    use to me for what I want to do.
    """

    def on_hover(self, view, point, hover_zone):
        if view and view.id() == _panel_id and hover_zone == sublime.HOVER_TEXT:
            for region in view.get_regions(_output_panel):
                if region.intersects(view.line(point)):
                    self._ody_show_tooltip(view, view.substr(region).strip(), mouse_location=point)
                    break

    def on_text_command(self, view, command_name, args):
        """On text command.

        Parameters
        ----------
        view : object
            A Sublime Text view.
        command_name : str
            Command name.
        args : dict
            Command arguments.
        """
        # Detect double click.
        double_click = command_name == "drag_select" and "by" in args and args["by"] == "words" and \
            view and view.sel() and view.id() == _panel_id

        if double_click:
            self._ody_on_double_click(view)

    def _ody_show_tooltip(self, view, file_path, mouse_location=None):
        """Show tooltip.

        Parameters
        ----------
        view : object
            A Sublime Text view.
        file_path : str
            File path.
        mouse_location : None, int, optional
            Mouse location.
        """
        if mouse_location is None:
            mouse_location = view.sel()[0].begin()

        def on_navigate(href):
            """Summary

            Parameters
            ----------
            href : TYPE
                Description
            """
            if href == "edit-file" or href == "launch-file":
                self._ody_open_file(view, file_path, open_type=href)
                view.hide_popup()

        view.show_popup(
            _tooltip_template,
            flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY,
            location=mouse_location,
            max_width=512,
            on_navigate=on_navigate
        )

    def _ody_on_double_click(self, view):
        """On "double click".

        Parameters
        ----------
        view : object
            A Sublime Text view.
        """
        selection = view.sel()[0]
        cursor = get_cursor_pos(view)

        for region in view.get_regions(_output_panel):
            # The cursor should be inside the region...
            # ...and the selection begin and end should be inside the region.
            if region.begin() <= cursor <= region.end() and \
                    selection.begin() >= region.begin() and selection.end() <= region.end():
                self._ody_open_file(view, view.substr(region).strip(), open_type="edit-file")
                break

    def _ody_open_file(self, view, file_path, open_type="edit-file"):
        if os.path.exists(file_path):
            window = view.window() or sublime.active_window()

            try:
                if open_type == "edit-file":
                    window.open_file(file_path)
                elif open_type == "launch-file":
                    cmd_utils.launch_default_for_file(file_path)
            except Exception as err:
                sublime.error_message(str(err))


def get_cursor_pos(view):
    """Get cursor position.

    Parameters
    ----------
    view : object
        A Sublime Text view.

    Returns
    -------
    int
        Offset from the beginning of the editor buffer.
    """
    return next((s.begin() for s in view.sel()), -1)


def panel_is_active(window):
    """Summary

    Parameters
    ----------
    window : TYPE
        Description

    Returns
    -------
    TYPE
        Description
    """
    return False if not window else window.active_panel() == _output_panel


def ensure_panel(window):
    """Summary

    Parameters
    ----------
    window : TYPE
        Description

    Returns
    -------
    TYPE
        Description
    """
    return get_panel(window) or create_panel(window)


def get_panel(window):
    """Summary

    Parameters
    ----------
    window : TYPE
        Description

    Returns
    -------
    TYPE
        Description
    """
    return window.find_output_panel(_panel_name)


def create_panel(window):
    """Summary

    Parameters
    ----------
    window : TYPE
        Description

    Returns
    -------
    TYPE
        Description
    """
    panel = window.create_output_panel(_panel_name)

    try:  # Try the resource first, in case we're in the middle of an upgrade
        sublime.load_resource(_panel_syntax)
    except Exception:
        return

    panel.assign_syntax(_panel_syntax)
    # Call create_output_panel a second time after assigning the above
    # settings, so that it'll be picked up as a result buffer
    # see: Packages/Default/exec.py#L228-L230
    return window.create_output_panel(_panel_name)


class __odyseus_clear_message_panel_content(sublime_plugin.TextCommand):
    def run(self, edit):
        panel = self.view
        _, y = panel.viewport_position()
        panel.set_read_only(False)
        panel.erase_regions(_output_panel)
        panel.erase_regions(_output_panel + "-icons")
        panel.replace(edit, sublime.Region(0, panel.size()), "")
        panel.set_read_only(True)
        # Avoid https://github.com/SublimeTextIssues/Core/issues/2560
        # Force setting the viewport synchronous by setting it twice.
        panel.set_viewport_position((0, 0), False)
        panel.set_viewport_position((0, y), False)


if __name__ == "__main__":
    pass
