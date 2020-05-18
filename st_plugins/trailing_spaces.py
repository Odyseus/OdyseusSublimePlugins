"""
Provides both a trailing spaces highlighter and a deletion command.

See README.md for details.

@author: Jean-Denis Vauguet <jd@vauguet.fr>, Oktay Acikalin <ok@ryotic.de>
@license: MIT (http://www.opensource.org/licenses/mit-license.php)
@since: 2011-02-25
"""
from functools import partial

import sublime
import sublime_plugin

from . import settings
from . import settings_utils
from python_utils.sublime_text_utils import events
from python_utils.sublime_text_utils import queue

__all__ = [
    "OdyseusTsDeleteTrailingSpacesCommand",
    "OdyseusTsHighlightTrailingSpacesCommand",
    "OdyseusTsToggleLiveHighlightCommand",
    "OdyseusTsTrailingSpacesListener",
]

_plugin_id = "TrailingSpaces-{}"


class StorageClass():
    def __init__(self):
        self.prev_highlightable = None


Storage = StorageClass()


@events.on("plugin_loaded")
def on_plugin_loaded():
    """On plugin loaded.
    """
    global Storage
    Storage = StorageClass()


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
    return settings.get("trailing_spaces.%s" % s, default)


def find_trailing_spaces(view):
    """Get the regions matching trailing spaces.

    Parameters
    ----------
    view : object
        A Sublime Text view.

    Returns
    -------
    list
        The list of regions which map to trailing spaces and the list of
        regions which are to be highlighted, as a list [matched, highlightable].
    """
    if not view or len(view.sel()) == 0:
        return [None, None]

    include_empty_lines = get_settings("include_empty_lines", True)
    include_current_line = get_settings("include_current_line", False)
    ignored_scopes = "|".join(get_settings("scope_ignore", []))
    regexp = get_settings("regexp") + "$"
    no_empty_lines_regexp = r"(?<=\S)%s$" % regexp

    sel = view.sel()[0]
    line = view.line(sel.b)

    # trailing_regions = view.find_all(regexp if include_empty_lines else no_empty_lines_regexp)

    # filter out ignored scopes
    trailing_regions = [
        region for region in view.find_all(regexp if include_empty_lines else no_empty_lines_regexp)
        if not ignored_scopes or not view.match_selector(region.begin(), ignored_scopes)
    ]

    if include_current_line:
        return [trailing_regions, trailing_regions]
    else:
        current_offender = view.find(
            regexp if include_empty_lines else no_empty_lines_regexp, line.a)
        removal = False if current_offender is None else line.intersects(current_offender)
        highlightable = [i for i in trailing_regions if i !=
                         current_offender] if removal else trailing_regions
        return [trailing_regions, highlightable]


def match_trailing_spaces(view):
    """Find the trailing spaces in the view and flags them as such.

    It will refresh highlighted regions as well. Does not execute if the
    document's size exceeds the file_max_size setting, or if the fired in a view
    which is not a legacy document (helper/build views and so on).

    Parameters
    ----------
    view : object
        A Sublime Text view.

    Returns
    -------
    None
        Halt execution.
    """
    # Silently pass ignored views.
    if ignore_view(view):
        return

    # Silently pass if file is too big.
    if max_size_exceeded(view):
        sublime.status_message("File is too big, trailing spaces handling disabled.")
        return

    (matched, highlightable) = find_trailing_spaces(view)

    if matched is None or highlightable is None:
        return

    highlight_trailing_spaces_regions(view, highlightable)


def ignore_view(view):
    """Checks if the view should be ignored based on a list of syntaxes.

    Parameters
    ----------
    view : object
        A Sublime Text view.

    Returns
    -------
    bool
        True if the view should be ignored, False otherwise.
    """
    if not view or view.is_scratch() or view.settings().get("is_widget"):
        return True

    view_syntax = view.settings().get("syntax").split(
        "/")[-1].lower() if view.settings().get("syntax") else ""

    if not view_syntax:
        return False

    for syntax_ignore in get_settings("syntax_ignore", []):
        if syntax_ignore.lower() in view_syntax:
            return True

    return False


def max_size_exceeded(view):
    """Checks whether the document is bigger than the max_size setting.

    Parameters
    ----------
    view : object
        A Sublime Text view.

    Returns
    -------
    bool
        If file size is too big.
    """
    return view.size() > get_settings("file_max_size", 1048576)


def highlight_trailing_spaces_regions(view, regions):
    """Highlights specified regions as trailing spaces.

    It will use the scope enforced by the state of the toggable highlighting.

    Parameters
    ----------
    view : object
        A Sublime Text view.
    regions : list
        Regions qualified as trailing spaces.
    """
    # NOTE: Prevent unnecessary regions removal/addition. First, because it's a total waste of
    # resources and second because it causes "blinking" when it's constantly removing/adding regions
    # while typing.
    if Storage.prev_highlightable == regions:
        return

    Storage.prev_highlightable = regions
    view.erase_regions(_plugin_id.format("highlighted-regions"))
    view.add_regions(_plugin_id.format("highlighted-regions"),
                     regions,
                     get_settings("highlight_color", "invalid.illegal") or "",
                     "",
                     sublime.HIDE_ON_MINIMAP)


def find_regions_to_delete(view):
    """Finds the trailing spaces regions to be deleted.

    Parameters
    ----------
    view : object
        A Sublime Text view.

    Returns
    -------
    list
        List of regions to be deleted.
    """
    (regions, highlightable) = find_trailing_spaces(view)

    return regions


def delete_trailing_regions(view, edit):
    """Deletes the trailing spaces regions.

    Parameters
    ----------
    view : object
        A Sublime Text view.
    edit : object
        A Sublime Text edit.

    Returns
    -------
    int
        The number of deleted regions.
    """
    regions = find_regions_to_delete(view)

    if regions:
        # Trick: reversing the regions takes care of the growing offset while
        # deleting the successive regions.
        regions.reverse()
        for r in regions:
            view.erase(edit, r)
        return len(regions)
    else:
        return 0


class OdyseusTsTrailingSpacesListener(sublime_plugin.EventListener):
    """Matches and highlights trailing spaces on key events, according to the
    current settings.
    """

    def on_modified_async(self, view):
        """On modified.

        Parameters
        ----------
        view : object
            A Sublime Text view.
        """
        self._ody_match(view)

    def on_selection_modified_async(self, view):
        """On selection modified.

        Parameters
        ----------
        view : object
            A Sublime Text view.
        """
        self._ody_match(view)

    def on_activated_async(self, view):
        """On activated.

        Parameters
        ----------
        view : object
            A Sublime Text view.
        """
        self._ody_match(view)

    def _ody_match(self, view):
        if get_settings("live_highlight", True):
            queue.debounce(
                partial(match_trailing_spaces, view),
                delay=get_settings("highlight_delay", 0),
                key=_plugin_id.format("debounce")
            )


class OdyseusTsDeleteTrailingSpacesCommand(sublime_plugin.TextCommand):
    """Deletes the trailing spaces.
    """

    def run(self, edit):
        """Action to perform when this Sublime Text command is executed.

        Parameters
        ----------
        edit : object
            A Sublime Text edit.

        Returns
        -------
        None
            Halt execution.
        """
        if max_size_exceeded(self.view):
            sublime.status_message("File is too big, trailing spaces handling disabled.")
            return

        deleted = delete_trailing_regions(self.view, edit)

        if deleted:
            if get_settings("save_after_trim") and not get_settings("trim_on_save"):
                sublime.set_timeout(lambda: self.save(self.view), 10)

            message = "Deleted {regions} trailing spaces region{plural}".format(
                regions=deleted,
                plural="s" if deleted > 1 else ""
            )
        else:
            message = "No trailing spaces to delete!"

        sublime.status_message(message)


class OdyseusTsHighlightTrailingSpacesCommand(sublime_plugin.TextCommand):
    """Highlights trailing spaces.
    """

    def run(self, edit):
        """Action to perform when this Sublime Text command is executed.

        Parameters
        ----------
        edit : object
            A Sublime Text edit.

        Returns
        -------
        None
            Halt execution.
        """
        queue.debounce(
            partial(match_trailing_spaces, self.view),
            delay=get_settings("highlight_delay", 0),
            key=_plugin_id.format("debounce")
        )


class OdyseusTsToggleLiveHighlightCommand(settings_utils.SettingsToggleBoolean,
                                          sublime_plugin.ApplicationCommand):
    _ody_key = "trailing_spaces.live_highlight"
    _ody_settings = settings
    _ody_description = "Trailing Spaces - Live Highlight - %s"

    def run(self):
        super().run()

        view = sublime.active_window().active_view()

        if not view:
            return

        if get_settings("live_highlight"):
            match_trailing_spaces(view)
        else:
            view.erase_regions(_plugin_id.format("highlighted-regions"))


if __name__ == "__main__":
    pass
