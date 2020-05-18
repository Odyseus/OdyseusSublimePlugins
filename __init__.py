#!/usr/bin/python3
# -*- coding: utf-8 -*-
from .st_plugins import OdyseusPluginsToggleLoggingLevelCommand         # noqa
from .st_plugins import ProjectSettingsController                       # noqa
from .st_plugins import SublimeConsoleController                        # noqa
from python_utils.sublime_text_utils import events

# NOTE: Import last.
from .st_plugins.better_find_results import *                           # noqa
from .st_plugins.case_conversion import *                               # noqa
from .st_plugins.code_formatter import *                                # noqa
from .st_plugins.compare_open_files import *                            # noqa
from .st_plugins.delete_blank_lines import *                            # noqa
from .st_plugins.deselect import *                                      # noqa
from .st_plugins.display_numbers import *                               # noqa
from .st_plugins.fix_python_imports import *                            # noqa
from .st_plugins.message_panel import *                                 # noqa
from .st_plugins.password_generator import *                            # noqa
from .st_plugins.run_command_in_all_views import *                      # noqa
from .st_plugins.search_html_pages import *                             # noqa
from .st_plugins.search_with_zeal import *                              # noqa
from .st_plugins.sidebar_context_commands import *                      # noqa
from .st_plugins.text_debugging import *                                # noqa
from .st_plugins.toggle_quotes import *                                 # noqa
from .st_plugins.toggle_words import *                                  # noqa
from .st_plugins.trailing_spaces import *                               # noqa
from .st_plugins.word_highlight import *                                # noqa


def plugin_loaded():
    """On plugin loaded callback.
    """
    events.broadcast("plugin_loaded")


def plugin_unloaded():
    """On plugin unloaded.
    """
    events.broadcast("plugin_unloaded")


if __name__ == "__main__":
    pass
