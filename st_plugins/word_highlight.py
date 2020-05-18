#!/usr/bin/python3
# -*- coding: utf-8 -*-
import re

from functools import partial

import sublime
import sublime_plugin

from . import settings
from . import settings_utils
from python_utils.sublime_text_utils import events
from python_utils.sublime_text_utils import queue

__all__ = [
    "OdyseusWhSelectHighlightedNextWordCommand",
    "OdyseusWhSelectHighlightedSkipLastWordCommand",
    "OdyseusWhSelectHighlightedWordsCommand",
    "OdyseusWhToggleLiveHighlightCommand",
    "OdyseusWhWordHighlightClickCommand",
    "OdyseusWhWordHighlightListener"
]

_plugin_id = "WordHighlight-{}"


class StorageClass():
    def __init__(self):
        self.prev_selections = None
        self.prev_regions = None
        self.select_next_word_skiped = 0


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
    return settings.get("word_highlight.%s" % s, default)


def escape_regex(str):
    # Sublime text chokes when regexes contain \', \<, \>, or \`.
    # Call re.escape to escape everything, and then unescape these four.
    str = re.escape(str)
    for c in "'<>`":
        str = str.replace("\\" + c, c)
    return str


def find_regions(view, regions, string, limited_size):
    # It seems as if \b doesn't pay attention to word_separators, but
    # \w does. Hence we use lookaround assertions instead of \b.
    if get_settings("highlight_non_word_characters", False):
        search = escape_regex(string)
    else:
        search = r"(?<!\w)" + escape_regex(string) + r"(?!\w)"

    if not limited_size:
        regions += view.find_all(search, (not get_settings("case_sensitive",
                                                           True)) * sublime.IGNORECASE)
    else:
        chars = get_settings("when_file_size_limit_search_this_num_of_characters", 20000)
        visible_region = view.visible_region()
        begin = 0 if visible_region.begin() - chars < 0 else visible_region.begin() - chars
        end = visible_region.end() + chars
        from_point = begin
        while True:
            region = view.find(search, from_point)
            if region:
                regions.append(region)
                if region.end() > end:
                    break
                else:
                    from_point = region.end()
            else:
                break
    return regions


def delayed_highlight(view, regions, occurrences_message, limited_size):
    view.add_regions(
        _plugin_id.format("regions"),
        regions,
        get_settings("color_scope_name", "comment"),
        get_settings(
            "icon_type_on_gutter",
            "dot") if get_settings(
            "mark_occurrences_on_gutter",
            False) else "",
        get_settings("hide_on_minimap", True) * sublime.HIDE_ON_MINIMAP |
        get_settings("draw_no_fill", False) * sublime.DRAW_NO_FILL |
        get_settings("draw_no_outline", True) * sublime.DRAW_NO_OUTLINE |
        get_settings("draw_solid_underline", True) * sublime.DRAW_SOLID_UNDERLINE)

    if get_settings("show_word_highlight_status_bar_message", False):
        view.set_status(_plugin_id.format("status"),
                        ", ".join(list(set(occurrences_message))) +
                        (" found on a limited portion of the document " if limited_size else ""))


def highlight_occurences(view):
    if not get_settings("highlight_when_selection_is_empty",
                        False) and not view.has_non_empty_selection_region():
        view.erase_status(_plugin_id.format("status"))
        view.erase_regions(_plugin_id.format("regions"))
        Storage.prev_regions = None
        Storage.prev_selections = None
        return
    # todo: The list cast below can go away when Sublime 3's Selection class implements __str__
    prev_selections = str(list(view.sel()))

    if Storage.prev_selections == prev_selections:
        return
    else:
        Storage.prev_selections = prev_selections

    if view.size() <= get_settings("file_size_limit", 4194304):
        limited_size = False
    else:
        limited_size = True

    # print "running"+ str(time.time())

    regions = []
    processed_words = []
    occurrences_message = []
    occurrences_count = 0
    word_separators = view.settings().get("word_separators", "")
    for sel in view.sel():
        if get_settings("highlight_when_selection_is_empty", False) and sel.empty():
            string = view.substr(view.word(sel)).strip()
            if string not in processed_words:
                processed_words.append(string)
                if string and all([c not in word_separators for c in string]):
                    regions = find_regions(view, regions, string, limited_size)
                if not get_settings("highlight_word_under_cursor_when_selection_is_empty", False):
                    for s in view.sel():
                        regions = [r for r in regions if not r.contains(s)]
        elif not sel.empty() and get_settings("highlight_non_word_characters", False):
            string = view.substr(sel)
            if string and string not in processed_words:
                processed_words.append(string)
                regions = find_regions(view, regions, string, limited_size)
        elif not sel.empty():
            word = view.word(sel)
            if word.end() == sel.end() and word.begin() == sel.begin():
                string = view.substr(word).strip()
                if string not in processed_words:
                    processed_words.append(string)
                    if string and all([c not in word_separators for c in string]):
                        regions = find_regions(view, regions, string, limited_size)

        occurrences = len(regions) - occurrences_count
        if occurrences > 0:
            occurrences_message.append('"' + string + '" ' + str(occurrences) + " ")
            occurrences_count = occurrences_count + occurrences

    if Storage.prev_regions != regions:
        view.erase_regions(_plugin_id.format("regions"))
        if regions:
            queue.debounce(
                partial(delayed_highlight,
                        view,
                        regions,
                        occurrences_message,
                        limited_size),
                delay=get_settings("highlight_delay", 0),
                key=_plugin_id.format("debounce")
            )
        else:
            view.erase_status(_plugin_id.format("status"))

        Storage.prev_regions = regions


class OdyseusWhSelectHighlightedWordsCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        wh = self.view.get_regions(_plugin_id.format("regions"))
        for w in wh:
            self.view.sel().add(w)


class OdyseusWhSelectHighlightedNextWordCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        sel = [s for s in self.view.sel()]
        sel.reverse()
        if sel:
            word = sel[0]
            wh = self.view.get_regions(_plugin_id.format("regions"))
            for w in wh:
                if w.end() > word.end() and w.end() > Storage.select_next_word_skiped:
                    self.view.sel().add(w)
                    self.view.show(w)
                    Storage.select_next_word_skiped = w.end()
                    break


class OdyseusWhSelectHighlightedSkipLastWordCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        sel = [s for s in self.view.sel()]
        sel.reverse()
        if sel and len(sel) > 1:
            self.view.sel().subtract(sel[0])
            Storage.select_next_word_skiped = sel[0].end()


class OdyseusWhWordHighlightClickCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        Storage.select_next_word_skiped = 0
        view = self.view
        if get_settings("live_highlight") and not view.settings().get("is_widget"):
            highlight_occurences(view)


class OdyseusWhWordHighlightListener(sublime_plugin.EventListener):
    def on_activated_async(self, view):
        Storage.prev_selections = None
        Storage.select_next_word_skiped = 0

        if not view.is_loading() and not get_settings("live_highlight"):
            view.erase_regions(_plugin_id.format("regions"))

    def on_selection_modified_async(self, view):
        if view and len(view.sel()) and get_settings(
                "live_highlight") and not view.settings().get("is_widget"):
            queue.debounce(
                partial(highlight_occurences, view),
                delay=get_settings("highlight_delay", 0),
                key=_plugin_id.format("debounce")
            )


class OdyseusWhToggleLiveHighlightCommand(settings_utils.SettingsToggleBoolean,
                                          sublime_plugin.ApplicationCommand):
    _ody_key = "word_highlight.live_highlight"
    _ody_settings = settings
    _ody_description = "Word Highlight - Live highlight - %s"

    def run(self):
        super().run()

        view = sublime.active_window().active_view()

        if not view:
            return

        if get_settings("live_highlight"):
            highlight_occurences(view)
        else:
            view.erase_regions(_plugin_id.format("regions"))


if __name__ == "__main__":
    pass
