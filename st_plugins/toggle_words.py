#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Deselect.

Based on: https://github.com/gordio/ToggleWords

MIT License

Copyright (c) 2016 Oleg Gordienko

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
import re

import sublime
import sublime_plugin

from . import settings

__all__ = [
    "OdyseusToggleWordCommand"
]

_plugin_name = "ToggleWords"


class OdyseusToggleWordCommand(sublime_plugin.TextCommand):

    def run(self, view):
        words_dict = settings.get("toggle_words", [])

        if not words_dict:
            return

        for region in self.view.sel():
            if region.a != region.b:
                text_region = region
                cursor_pos = -1
            else:
                text_region = self.view.word(region)
                cursor_pos = region.a

            self._ody_toggle_word(view, text_region, words_dict, cursor_pos)

    def _ody_toggle_word(self, view, region, words_dict, cursor_pos=-1):
        editor_word = self.view.substr(region)
        toggle_groups = words_dict

        for toggle_group in toggle_groups:
            toggle_group_word_count = len(toggle_group)
            # toggle_group.sort(key=len, reverse=True)

            for cur_word in range(0, toggle_group_word_count):
                next_word = (cur_word + 1) % toggle_group_word_count

                if cursor_pos != -1:  # selected == false
                    lineRegion = self.view.line(region)
                    line = self.view.substr(lineRegion)
                    lineBegin = lineRegion.a

                    for line_finding in re.finditer(
                            re.escape(toggle_group[cur_word]), line, flags=re.IGNORECASE):
                        lf_a = line_finding.span()[0]
                        lf_b = line_finding.span()[1]
                        finding_region = sublime.Region(lineBegin + lf_a, lineBegin + lf_b)
                        if finding_region.contains(cursor_pos):
                            editor_word = self.view.substr(finding_region)
                            region = finding_region

                if editor_word == toggle_group[cur_word]:
                    self.view.replace(view, region, toggle_group[next_word])
                    return
                if editor_word == toggle_group[cur_word].lower():
                    self.view.replace(view, region, toggle_group[next_word].lower())
                    return
                if editor_word == toggle_group[cur_word].capitalize():
                    self.view.replace(view, region, toggle_group[next_word].capitalize())
                    return
                if editor_word == toggle_group[cur_word].upper():
                    self.view.replace(view, region, toggle_group[next_word].upper())
                    return

        sublime.status_message(
            "{0}: Can't find toggles for '{1}'".format(_plugin_name, editor_word)
        )


if __name__ == "__main__":
    pass
