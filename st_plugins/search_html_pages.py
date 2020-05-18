#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
************************
Search HTML pages plugin
************************

.. contextual-admonition::
    :context: info
    :title: Description

    Plugin to open a URL to a web page that supports queries.

.. contextual-admonition::
    :context: info
    :title: Available command

    - ``odyseus_search_html_pages`` Possible arguments:

        + ``base_url`` (:py:class:`str`) (**Required**): Base URL to which to add search queries.
        + ``params`` (:py:class:`dict`) (**Required**): Additional parameters to pass as URL queries. One of the parameters should be the query containing the variable ``${search_term}`` that will be replaced by search terms.
        + ``is_visible`` (:py:class:`bool`, :py:class:`str` or :py:class:`list`): Possible values:

            * A boolean: See :ref:`commands-visibility-note-reference`.
            * A string: A case insensitive name (partial match (e.g. **python**) or syntax file name (e.g. **Python.sublime-syntax**)) of a file view's syntax.
            * A list of strings: A list of view syntaxes. It follows the same logic as setting a single string, but it allows to match several syntaxes.
        + ``cmd_id`` (:py:class:`str`): This key is only used/needed if one wants to define arguments for a command through the plugin settings.

- These commands are meant to be used from the command palette (if they are defined in a **.sublime-commands** file), from context menu items (if they are defined in a **Context.sublime-menu** file) or from a keyboard shortcut (if they are defined in a **.sublime-keymap** file).
- They work on currently selected text in the current file's view, as many there may be, whether they are actual selections (the search term will be the exact selection) or cursor positions (the search term will be the detected word at cursor position).
- For each selection a new browser tab will be opened with each selection as search terms.

How to use?
===========

- By defining commands/menus in **.sublime-menu**, **.sublime-commands** or **.sublime-keymap** files:

    .. code-block:: json

        [{
            "caption": "Search Selections on Python Docs (on-line)",
            "command": "odyseus_search_html_pages",
            "args": {
                "base_url": "https://docs.python.org/3/search.html",
                "params": {
                    "q": "${search_term}",
                    "check_keywords": "yes"
                },
                "is_visible": "python"
            }
        }]

- By creating a setting, making the commands/menus definitions even simpler. Settings for this plugin are prefixed with ``search_html_pages.``.

    + Given the previous example, this is how it would be defined in a setting:

        .. code-block:: json

            {
                "search_html_pages.odyseus_search_python_docs_online": {
                    "base_url": "https://docs.python.org/3/search.html",
                    "params": {
                        "q": "${search_term}",
                        "check_keywords": "yes"
                    },
                    "is_visible": "python"
                }
            }

    + And it will be defined as follows in a **.sublime-menu**, **.sublime-commands** or **.sublime-keymap** file:

        .. code-block:: javascript

            [{
                "caption": "Search Selections on Python Docs (on-line)",
                "command": "odyseus_search_html_pages",
                "args": {
                    // Note that the value of "cmd_id" is used as part of the setting definition key
                    // ("search_html_pages.odyseus_search_python_docs_online").
                    "cmd_id": "odyseus_search_python_docs_online"
                }
            }]

.. contextual-admonition::
    :context: info
    :title: Another example

    .. code-block:: javascript

        [{
            "caption": "My DuckDuckGo Search",
            "command": "odyseus_search_html_pages",
            "args": {
                "base_url": "https://duckduckgo.com",
                "params": {
                    "q": "${search_term}",
                    "kae": "d"                          // DuckDuckGo dark theme.
                },
                "is_visible": true                      // Command always visible.
            }
        }]

"""
import re
import urllib
import webbrowser

from threading import Thread

import sublime
import sublime_plugin

from . import display_message_in_panel
from . import logger
from . import settings
from python_utils.sublime_text_utils import utils


__all__ = [
    "OdyseusSearchHtmlPagesCommand"
]


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
    if cmd_id is None:
        return default

    return settings.get("search_html_pages.%s" % cmd_id, default)


class OdyseusSearchHtmlPagesCommand(sublime_plugin.TextCommand):
    """Command to perform a search of the selected text on any HTML page that supports URL queries.
    """

    def run(self, edit, **kwargs):
        """Action to perform when this Sublime Text command is executed.

        Parameters
        ----------
        edit : sublime.Edit
            sublime.Edit object.
        **kwargs
            Keyword arguments.

        Raises
        ------
        Exception
            An error occurred (Duh!).
        """
        cmd_id = kwargs.get("cmd_id")
        clsname = cmd_id or self.__class__.__name__
        try:
            base_url = self._ody_get_option(kwargs.get("base_url"), "base_url", cmd_id=cmd_id)
            params = self._ody_get_option(kwargs.get("params"), "params", cmd_id=cmd_id)

            if not base_url or not params:
                raise Exception("No base URL or parameters specified.")

            selections = utils.get_selections(self.view)

            if selections is not None:
                threads = []

                for search_term in selections:
                    search_term = re.sub(r"\s+", " ", search_term)

                    if len(search_term) == 0:
                        logger.warning("%s: You did not select text." % clsname)
                    else:
                        url_to_open = urllib.parse.urlparse("%s?%s" % (
                            base_url, urllib.parse.urlencode(utils.substitute_variables({
                                "search_term": urllib.parse.quote_plus(search_term)
                            }, params)))).geturl()

                        sublime.status_message("%s: Performing search on the keyword, '%s'" % (
                            clsname, search_term))

                        t = Thread(target=webbrowser.open, args=(url_to_open,), kwargs={
                            "new": 2,
                            "autoraise": True
                        })
                        t.start()
                        threads.append(t)

                        for thread in threads:
                            if thread is not None and thread.isAlive():
                                thread.join()
            else:
                sublime.status_message("%s Info: Text was not selected." % clsname)
        except Exception as err:
            title = "%s Error:" % clsname
            display_message_in_panel(self.view, title=title, body=err)

    def _ody_get_option(self, param, option, default="", cmd_id=None):
        """Get option.

        Parameters
        ----------
        param : None, bool, str, dict
            The value of an option passed as function parameter.
        option : str
            The name of an option as defined in the plugin settings file.
        default : str, optional
            Default value for option in case that param nor settings were defined.
        cmd_id : None, optional
            A string used as ID to get settings from the plugin settings file.

        Returns
        -------
        bool, str, dict
            The value for an option.
        """
        return param if param is not None else get_settings(cmd_id).get(option, default)

    def is_visible(self, **kwargs):
        """Set command visibility.

        Parameters
        ----------
        **kwargs
            Keyword arguments.

        Returns
        -------
        bool
            If it should be visible.
        """
        is_visible = self._ody_get_option(kwargs.get("is_visible"), "is_visible",
                                          default=True, cmd_id=kwargs.get("cmd_id"))

        if isinstance(is_visible, bool):
            return is_visible
        else:
            return utils.has_right_syntax(
                self.view, view_syntaxes=is_visible, strict=False)


if __name__ == "__main__":
    pass
