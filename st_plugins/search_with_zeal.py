#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
***********************
Search with Zeal plugin
***********************

.. contextual-admonition::
    :context: info
    :title: Description

    Plugin that makes possible to search on Zeal from Sublime Text.

.. contextual-admonition::
    :context: warning
    :title: Dependencies

    - Zeal: An off-line documentation browser.

        + `Download instructions <https://zealdocs.org>`__.
        + `GitHub repository <https://github.com/zealdocs/zeal>`__.

.. contextual-admonition::
    :context: info
    :title: Mentions

    Plugin based on `Zeal for Sublime Text <https://github.com/vaanwd/Zeal>`__.

.. contextual-admonition::
    :context: info
    :title: Available commands

    - ``odyseus_search_with_zeal_selection``: Command to search the current file view's selection on Zeal.
    - ``odyseus_search_with_zeal``: This command will display a Sublime quick panel from which one can type queries to search on Zeal.

- Settings for this plugin are prefixed with ``search_with_zeal.``. Possible options:

    + ``exec_map`` (:py:class:`dict`): See :ref:`command-executables-note-reference` and :ref:`common-variables-substitution-reference`.
    + ``search_selection_is_visible`` (:py:class:`bool` or :py:class:`str`) (Default: ``auto``): See :ref:`commands-visibility-note-reference`.

        * ``auto``: The command will be visible if the detected language on the current file view matches with one of the languages defined in the ``language_mapping`` option (specifically the ``lang`` key).

    + ``sort_mapping`` (:py:class:`bool`) (Default: ``true``): Whether to sort the languages when there are more than one entry matching the same language. This allows to display the language selector menu with its items sorted alphabetically.
    + ``language_mapping`` (:py:class:`dict`): A dictionary of dictionaries. Each dictionary should be uniquely named with a name that identifies a programing language and contain only two keys named ``lang`` and ``zeal_lang``.

        * ``lang`` (:py:class:`dict`): This is the current file view language detected by the plugin. If there are more than one entry with the same language in the language map, a Sublime Text quick panel will be displayed with the list of all languages whose ``lang`` key is the same, giving the choice to select in which Zeal *docset* the search will be performed.
        * ``zeal_lang`` (:py:class:`dict`): This is the name of an installed Zeal *docset*. This string will be part of the search term passed to Zeal's |CLI|.

        * Examples:

            .. code-block:: javascript

                // Basic explanation.
                "search_with_zeal.language_mapping": {
                    "Programing language display name": {
                        "lang": "detected_view_language",
                        "zeal_lang": "zeal_docset_name"
                    },
                }

            .. code-block:: javascript

                // - The command "Search selection on Zeal" will be visible on file views with
                //    "python" as the detected language.
                // - Upon executing the command with a selection, a Sublime Text quick panel will
                //    be displayed with two items (Python and Django).
                //
                // If Python is selected, the query performed on Zeal will be "python:selection".
                // If Django is selected, the query performed on Zeal will be "django:selection".
                "search_with_zeal.language_mapping": {
                    "Python": {
                        "lang": "python",
                        "zeal_lang": "python"
                    },
                    "Django": {
                        "lang": "python",
                        "zeal_lang": "django"
                    }
                }

            .. code-block:: javascript

                // This example will not display a quick panel. The search query performed on
                // Zeal will simply be "python,django:selection".
                "search_with_zeal.language_mapping": {
                    "Python": {
                        "lang": "python",
                        "zeal_lang": "python,django"
                    }
                }

Based on https://github.com/vaanwd/Zeal.

Attributes
----------
language : str
    Detected language.
"""
import os

import sublime
import sublime_plugin

from . import display_message_in_panel
from . import logger
from . import settings
from python_utils import cmd_utils
from python_utils.sublime_text_utils import utils

__all__ = [
    "OdyseusSearchWithZealCommand",
    "OdyseusSearchWithZealSelectionCommand"
]

language = None
_bad_characters = [
    "/", "\\", ":", "\n", "{", "}", "(", ")",
    "<", ">", "[", "]", "|", "?", "*", " ",
    '""', "'",
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
    return settings.get("search_with_zeal.%s" % s, default)


def get_language_from_scope(view):
    """Get language from scope.

    Parameters
    ----------
    view : object
        A Sublime Text view.

    Returns
    -------
    str
        Detected language.
    """
    scopes = view.scope_name(view.sel()[0].begin()).split()
    scope = scopes[0].strip()
    getlang = scope.split(".")
    lang = getlang[-1]
    # Some languages like CmakeEditor is cmakeeditor keyword
    lang = lang.split()[0]

    if lang == "basic":
        lang = getlang[-2]

    if lang == "html":
        if "php" in getlang:
            lang = "php"
        elif "js" in getlang:
            lang = "javascript"
        elif "css" in getlang:
            lang = "css"

    if lang == "js":
        lang = "javascript"

    if "source.css.less" in scope:
        lang = "less"

    if "source.scss" in scope:
        lang = "scss"

    if "source.sass" in scope:
        lang = "sass"

    if "source.actionscript.2" in scope:
        lang = "actionscript"

    if "source.cmake" in scope:
        lang = "cmake"

    if "source.python" in scope:
        lang = "python"

    del getlang

    return lang


def get_css_class_or_id(view):
    """Get CSS class or ID.

    Parameters
    ----------
    view : object
        A Sublime Text view.

    Returns
    -------
    str
        CSS class or ID.
    """
    cur_pos = view.sel()[0].a
    scope_reg = view.extract_scope(cur_pos)

    def get_sym(pos):
        """Summary

        Parameters
        ----------
        pos : TYPE
            Description

        Returns
        -------
        TYPE
            Description
        """
        sym = view.substr(sublime.Region(pos, pos + 1))
        return sym

    rule_type = set([".", "#"])
    delims = set([
        " ", '"', "'", "<", ">", "(", ")", "/", "\n", ":",
    ])
    all_delims = rule_type | delims
    left = cur_pos

    while get_sym(left) in delims:
        left -= 1

    while left > scope_reg.a and get_sym(left) not in all_delims:
        left -= 1

    if get_sym(left) in all_delims:
        left += 1

    right = cur_pos

    while right < scope_reg.b and get_sym(right) not in all_delims:
        right += 1

    return view.substr(sublime.Region(left, right))


def selection_erlang(view):
    """Summary

    Parameters
    ----------
    view : TYPE
        Description

    Returns
    -------
    TYPE
        Description
    """
    cur_pos = view.sel()[0].a
    scope_reg = view.line(cur_pos)

    def get_sym(pos):
        """Summary

        Parameters
        ----------
        pos : TYPE
            Description

        Returns
        -------
        TYPE
            Description
        """
        sym = view.substr(sublime.Region(pos, pos + 1))
        return sym

    rule_type = set([".", "#"])
    delims = set([
        " ", '"', "'", "<", ">", "(", ")", "/", "\n",
    ])
    all_delims = rule_type | delims
    left = cur_pos

    while get_sym(left) in delims:
        left -= 1

    while left > scope_reg.a and get_sym(left) not in all_delims:
        left -= 1

    if get_sym(left) in all_delims:
        left += 1

    right = cur_pos

    while right < scope_reg.b and get_sym(right) not in all_delims:
        right += 1

    return view.substr(sublime.Region(left, right))


def get_word(view):
    """Summary

    Parameters
    ----------
    view : TYPE
        Description

    Returns
    -------
    TYPE
        Description
    """
    word = None
    if language == "css" or language == "scss" or language == "sass" or language == "less":
        word = get_css_class_or_id(view)
    elif language == "erlang":
        word = selection_erlang(view)
    else:
        word = utils.get_selections(view, bad_chars=_bad_characters)

    return word[0] if isinstance(word, list) else word


def open_zeal(view, lang, text, join_command=False):
    """Open Zeal.

    Parameters
    ----------
    lang : str
        Description
    text : str
        Description
    join_command : bool, optional
        Description
    """
    zeal_exec = utils.get_executable_from_settings(
        view, get_settings("exec_map").get(sublime.platform(), []))

    if zeal_exec:
        try:
            cwd = os.path.dirname(zeal_exec)
            cwd = cwd if os.path.isdir(cwd) else os.path.expanduser("~")

            cmd = [zeal_exec]

            if join_command or lang is None or lang == "":  # When launching Zeal with "SearchWithZealCommand".
                cmd.append(text)
            else:  # When launching Zeal with "OdyseusSearchWithZealSelectionCommand".
                cmd.append("%s:%s" % (lang, text))

            cmd_utils.popen(cmd, cwd=cwd)
        except Exception as err:
            logger.error(err)
            display_message_in_panel(title="SearchWithZeal: Error", body=err)
    else:
        display_message_in_panel(title="Could not find Zeal's executable.")


class OdyseusSearchWithZealSelectionCommand(sublime_plugin.TextCommand):
    """Search selection with Zeal.

    Attributes
    ----------
    selected_item : TYPE
        Description
    """

    def run(self, edit, **kwargs):
        """Summary

        Parameters
        ----------
        edit : TYPE
            Description
        **kwargs
            Description
        """
        global language
        language = get_language_from_scope(self.view)
        text = ""

        for region in self.view.sel():
            if region.empty():
                text = self.view.word(region)

            text = self.view.substr(region)

            if text == "":
                text = get_word(self.view)

            if text is None:
                sublime.status_message("No word was selected.")
            else:
                items = dict()
                popup_list = []

                for title, opt in get_settings("language_mapping").items():
                    if opt["lang"] == language:
                        items[title] = opt

                if len(items) > 1:
                    srt = None

                    if get_settings("sort_mapping", False):
                        import operator
                        srt = sorted(items.items(), key=operator.itemgetter(0))
                    else:
                        srt = items.items()

                    for title, opt in srt:
                        popup_list.append([title, "Language: %s" % (opt["lang"])])
                elif len(items) == 1:
                    open_zeal(self.view, list(items.values())[0]["zeal_lang"], text)
                else:
                    sublime.status_message(
                        "No Zeal mapping was found for %s language." % (language))

            def callback(idx):
                """Summary

                Parameters
                ----------
                idx : TYPE
                    Description

                Returns
                -------
                TYPE
                    Description
                """
                if idx == -1:
                    return

                self.selected_item = popup_list[idx]
                open_zeal(self.view, items[self.selected_item[0]]["zeal_lang"], text)

            if text:
                if len(kwargs) == 0:
                    self.view.window().show_quick_panel(popup_list, callback, sublime.MONOSPACE_FONT)
                elif len(kwargs) != 0:
                    self.selected_item = kwargs["title"]
                    open_zeal(self.view, items[self.selected_item]["zeal_lang"], text)

    def is_visible(self):
        """Set command visibility.

        Returns
        -------
        bool
            If it should be visible.
        """
        is_visible = get_settings("search_selection_is_visible", "auto")
        lang = get_language_from_scope(self.view.window().active_view()).lower()
        logger.debug("Search with Zeal plugin detected language: %s" % lang)

        if isinstance(is_visible, bool):
            return is_visible
        else:
            for val in get_settings("language_mapping").values():
                if lang == val["lang"]:
                    return True

        return False


class OdyseusSearchWithZealCommand(sublime_plugin.TextCommand):
    """Search with Zeal.

    Attributes
    ----------
    last_text : str
        Description
    view_panel : TYPE
        Description
    """
    last_text = ""

    def run(self, edit):
        """Summary

        Parameters
        ----------
        edit : TYPE
            Description
        """
        view = self.view
        self.view_panel = view.window().show_input_panel(
            "Search in Zeal for:", self.last_text, self._ody_after_input, self._ody_on_change, None)
        self.view_panel.set_name("zeal_command_bar")

    def _ody_after_input(self, text):
        """Summary

        Parameters
        ----------
        text : TYPE
            Description

        Returns
        -------
        TYPE
            Description
        """
        if not text.strip():
            self.last_text = ""
            sublime.status_message("No text was entered")

            return
        else:
            open_zeal(self.view, "", text, True)

    def _ody_on_change(self, text):
        """Summary

        Parameters
        ----------
        text : TYPE
            Description

        Returns
        -------
        TYPE
            Description
        """
        if not text.strip():
            return

        self.last_text = text.strip()


if __name__ == "__main__":
    pass
