#!/usr/bin/python3
# -*- coding: utf-8 -*-
r"""
**********************
Case conversion plugin
**********************

.. contextual-admonition::
    :context: info
    :title: Description

    Case conversion plugin.

.. contextual-admonition::
    :context: info
    :title: Available commands

    - ``odyseus_toggle_snake_camel_pascal``: Toggle selections case between snake/camel/pascal case. Possible arguments:

        + ``detect_acronyms``: See :ref:`plugin settings <case-convertion-setting-reference>`.
        + ``use_list``: See :ref:`plugin settings <case-convertion-setting-reference>`.
        + ``acronyms``: See :ref:`plugin settings <case-convertion-setting-reference>`.

    - ``odyseus_convert_case``: Convert selections case. Possible arguments:

        + ``case_func`` (:py:class:`str`) (**Required**): A function name. It must be the name of an existent function on the ``case_conversion`` module. See :ref:`Available case conversion functions <available-case-conversion-functions-reference>`.
        + ``detect_acronyms``: See :ref:`plugin settings <case-convertion-setting-reference>`.
        + ``use_list``: See :ref:`plugin settings <case-convertion-setting-reference>`.
        + ``acronyms``: See :ref:`plugin settings <case-convertion-setting-reference>`.

.. contextual-admonition::
    :context: info
    :title: Mentions

    Plugin based on `Case Conversion <https://github.com/jdavisclark/CaseConversion>`__.

.. _case-convertion-setting-reference:

- Settings for this plugin are prefixed with ``case_conversion.``. All of these settings can be overridden when defining commands/menus by specifying command arguments with the same name as a setting. Possible options:

    + ``detect_acronyms`` (:py:class:`bool`) (Default: **true**): Will cause certain words in variable names to be marked as acronyms, making them upper-case ("URL") instead of capitalized ("Url"). When variables are parsed, upper-case letters count as word boundaries. That means words which would be considered acronyms are instead separated into individual letters. For example, converting "BaseURL" to snake_case will produce "base_u_r_l". If ``detect_acronyms`` is enabled, runs of single upper-case characters will be combined into single words. How these are detected depends on the ``use_acronyms_list`` setting. In general, this means "BaseURL" would be converted into "base_url". If ``detect_acronyms`` is disabled, no attempts to combine upper-case characters will be made.
    + ``use_acronyms_list`` (:py:class:`bool`) (Default: **false**): causes a more robust way to detect acronyms to be used, by searching for words from a predefined list. If ``use_acronyms_list`` is disabled, then a basic detection method is used. That is, runs of upper-case letters are detected and combined into single words. There are two drawbacks to this. The first is that two supposed acronyms that are adjacent will be counted as one word (e.g. "GetHTTPURLPath" would be divided into [Get, HTTPURL, Path]). The second drawback is that acronyms converted to lower-case cannot be converted back to their original upper-case. For example, "BaseURL" to "base_url" to "BaseUrl". If ``use_acronyms_list`` is enabled, then each run of upper-case letters is compared with words in the `acronyms` list, and any matches are counted as words. This means adjacent acronyms will be detected (e.g. "GetHTTPURLPath" will be divided into [Get, HTTP, URL, Path]). Acronyms are also detected among words, so converting from lower-case will produce correctly upper-cased acronyms. For example, "BaseURL" to "base_url" to "BaseURL".
    + ``acronyms`` (:py:class:`list`): is a list of words that are to be considered acronyms. Valid acronyms contain only upper and lower-case letters, and digits. Invalid words are ignored, and valid words are converted to upper-case. Order matters; words earlier in the list will be selected before words later in the list. For example, if "UI" were to be put before "GUI", then "GUI" would never be selected, because the "UI" in "GUI" would always be selected first. Note that if the list is empty, no acronyms will be detected, so variables will be treated as if ``detect_acronyms`` was disabled.
    + ``case_func`` (:py:class:`str`) (**Required** for and only used by command/menu definitions of the ``odyseus_convert_case``): This is the name of a function that will perform the case conversion. See :ref:`Available case conversion functions <available-case-conversion-functions-reference>`.

How to use?
===========

- By defining commands/menus in **.sublime-menu**, **.sublime-commands** or **.sublime-keymap** files:

    + Toggle snake/camel/pascal case keyboard shortcut:

        .. code-block:: json

            [{
                "keys": ["ctrl+k", "ctrl+s"],
                "command": "odyseus_toggle_snake_camel_pascal"
            }]

    + Convert to dash case command/menu definition:

        .. code-block:: json

            [{
                "caption": "Convert to dash case",
                "command": "odyseus_convert_case",
                "args": {
                    "case_func": "dashcase",
                    "detect_acronyms": false
                }
            }]

.. _available-case-conversion-functions-reference:

.. contextual-admonition::
    :context: info
    :title: Available case conversion functions

    - ``backslashcase``: Return text in backslash\\case style.
    - ``camelcase``: Return text in camelCase style.
    - ``constcase``: Return text in CONST_CASE style (aka SCREAMING_SNAKE_CASE).
    - ``dashcase``: Return text in dash-case style (aka kebab-case, spinal-case).
    - ``dotcase``: Return text in dot.case style.
    - ``kebabcase``: Same as ``dashcase``.
    - ``pascalcase``: Return text in PascalCase style (a.k.a. MixedCase).
    - ``screaming_snakecase``: Same as ``constcase``.
    - ``separate_words``: Return text in "separate words" style.
    - ``slashcase``: Return text in slash/case style.
    - ``snakecase``: Return text in snake_case style.
    - ``spinalcase``: Same as ``dashcase``.

"""
import sublime  # noqa
import sublime_plugin

from python_utils import case_conversion
from . import display_message_in_panel
from . import settings


__all__ = [
    "OdyseusConvertCaseCommand",
    "OdyseusToggleSnakeCamelPascalCommand"
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
    return settings.get("case_conversion.%s" % s, default)


def toggle_case(text, detect_acronyms, acronyms):
    """Toggle text case.

    Parameters
    ----------
    text : str
        Text to convert.
    detect_acronyms : bool
        Detect acronyms.
    acronyms : list
        List of acronyms.

    Returns
    -------
    str
        Converted case text.
    """
    words, case, sep = case_conversion.parse_case(text, detect_acronyms, acronyms)

    if case == "pascal" and not sep:
        return case_conversion.snakecase(text, detect_acronyms, acronyms)
    elif case == "lower" and sep == "_":
        return case_conversion.camelcase(text, detect_acronyms, acronyms)
    elif case == "camel" and not sep:
        return case_conversion.pascalcase(text, detect_acronyms, acronyms)
    else:
        return text


def run_on_selections(view, edit, func, detect_acronyms=None, use_list=None, acronyms=None):
    """Run conversion function on selections.

    Parameters
    ----------
    view : sublime.View
        sublime.View object.
    edit : sublime.Edit
        sublime.Edit object.
    func : object, str
        Function or function name that will convert the text case. If ``func`` is a string, it must
        be the name of an existent function on the ``case_conversion`` module.
    detect_acronyms : None, optional
        Detect acronyms.
    use_list : None, optional
        Use acronyms list.
    acronyms : None, optional
        List of acronyms.
    """
    if isinstance(func, str):
        try:
            case_func = getattr(case_conversion, func)
        except AttributeError:
            raise AttributeError("No valid case function defined. <%s>" % func)
    else:
        case_func = func

    if not case_func:
        raise RuntimeError("No case function defined.")

    detect_acronyms = detect_acronyms if detect_acronyms is not None else get_settings(
        "detect_acronyms", True)
    use_list = use_list if use_list is not None else get_settings("use_acronyms_list", False)

    if use_list:
        acronyms = acronyms if acronyms is not None else get_settings("acronyms", [])
    else:
        acronyms = False

    for s in view.sel():
        try:
            region = s if s else view.word(s)

            text = view.substr(region)
            # Preserve leading and trailing whitespace
            leading = text[:len(text) - len(text.lstrip())]
            trailing = text[len(text.rstrip()):]
            new_text = leading + case_func(text.strip(), detect_acronyms, acronyms) + trailing

            if new_text != text:
                view.replace(edit, region, new_text)
        except Exception as err:
            title = "run_on_selections: Error"
            display_message_in_panel(title=title, body=err)


class OdyseusToggleSnakeCamelPascalCommand(sublime_plugin.TextCommand):
    """Toggle selections case between snake/camel/pascal case.
    """

    def run(self, edit, detect_acronyms=None, use_list=None, acronyms=None):
        """Action to perform when this Sublime Text command is executed.

        Parameters
        ----------
        edit : sublime.Edit
            sublime.Edit object.
        detect_acronyms : None, bool, optional
            Detect acronyms.
        use_list : None, bool, optional
            Use acronyms list.
        acronyms : None, list, optional
            List of acronyms.
        """
        run_on_selections(self.view, edit, toggle_case,
                          detect_acronyms=detect_acronyms,
                          use_list=use_list,
                          acronyms=acronyms)


class OdyseusConvertCaseCommand(sublime_plugin.TextCommand):
    """Convert case of selections.
    """

    def run(self, edit, case_func=None, detect_acronyms=None, use_list=None, acronyms=None):
        """Action to perform when this Sublime Text command is executed.

        Parameters
        ----------
        edit : sublime.Edit
            sublime.Edit object.
        case_func : None, str, optional
            A case function found in the ``case_conversion`` module.
        detect_acronyms : None, bool, optional
            Detect acronyms.
        use_list : None, bool, optional
            Use acronyms list.
        acronyms : None, list, optional
            List of acronyms.
        """
        try:
            run_on_selections(self.view, edit, case_func,
                              detect_acronyms=detect_acronyms,
                              use_list=use_list,
                              acronyms=acronyms)
        except Exception as err:
            title = "%s: Error" % self.__class__.__name__
            display_message_in_panel(title=title, body=err)


if __name__ == "__main__":
    pass
