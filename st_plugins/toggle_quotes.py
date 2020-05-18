#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Toggle quotes.

Based on: https://github.com/spadgos/sublime-ToggleQuotes
"""
import re

import sublime
import sublime_plugin

__all__ = [
    "OdyseusToggleQuotesCommand"
]

_re_quotes = re.compile("^(['\"`])(.*)\\1$")
_quote_list = ["'", "\"", "`"]


class OdyseusToggleQuotesCommand(sublime_plugin.TextCommand):
    def run(self, edit, **kwargs):
        if len(self.view.sel()) and self.view.sel()[0].size() == 0:
            self.view.run_command("expand_selection", {"to": "scope"})

        for sel in self.view.sel():
            try:
                text = self.view.substr(sel)
                res = _re_quotes.match(text)

                if not res:
                    #  the current selection doesn't begin and end with a quote.
                    #  let's expand the selection one character each direction and try again
                    sel = sublime.Region(sel.begin() - 1, sel.end() + 1)
                    text = self.view.substr(sel)
                    res = _re_quotes.match(text)
                    if not res:
                        #  still no match... skip it!
                        continue

                old_quotes = res.group(1)

                new_quotes = kwargs.get("force_quote") or _quote_list[(
                    _quote_list.index(old_quotes) + 1) % len(_quote_list)]

                text = res.group(2)
                text = text.replace(new_quotes, "\\" + new_quotes)
                text = text.replace("\\" + old_quotes, old_quotes)
                text = new_quotes + text + new_quotes
                self.view.replace(edit, sel, text)
            except Exception as err:
                raise err


if __name__ == "__main__":
    pass


# 'te\'st'
# 'te"st'
# 'test'
# 'te\'st'
# 'te"st'
# 'te"st'
# "te'st"
# `te"s't`
