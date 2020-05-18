#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Better find results.

Based on: https://github.com/aziz/BetterFindBuffer

Copyright (c) 2014 Allen Bargi (https://twitter.com/aziz)

Permission is hereby granted, free of charge, to any person obtaining a copy of
this software and associated documentation files (the "Software"), to deal in the
Software without restriction, including without limitation the rights to use, copy,
modify, merge, publish, distribute, sublicense, and/or sell copies of the Software,
and to permit persons to whom the Software is furnished to do so, subject to the
following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED,
INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR
PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT HOLDERS BE
LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT,
TORT OR OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE
USE OR OTHER DEALINGS IN THE SOFTWARE.
"""
import os
import re

import sublime
import sublime_plugin

from .. import plugin_name

__all__ = [
    "OdyseusBfrFindInFilesOpenFileCommand",
    "OdyseusBfrFindInFilesOpenAllFilesCommand",
    "OdyseusBfrFindInFilesJumpCommand",
    "OdyseusBfrFindInFilesJumpFileCommand",
    "OdyseusBfrFindInFilesJumpMatchCommand",
    "OdyseusBfrTogglePopupHelpCommand",
    "OdyseusBfrFoldAndMoveToNextFileCommand",
    "OdyseusBfrForceSytax"
]

_custom_syntax = "Packages/%s/st_plugins/better_find_results/OSP-Find Results.sublime-syntax" % plugin_name
_popup_html = """<html>
<style>
    h2 {
        margin-top: 0;
        color: var(--orangish);
        font-size: 1.5rem;
    }
    ul {
        margin: 0;
        padding: 5px 20px 5px;
    }
    .shortcut-key {
        font-weight: bold;
        color: var(--greenish);
    }
    code {
        font-size: 1rem;
    }
</style>
<body id="odyseus-better-find-results">
    <h2>Keyboard Shortcuts</h2>
    <ul>
        <li><code><span class="shortcut-key">enter&nbsp;&nbsp;</span>Open the file under the cursor</code></li>
        <li><code><span class="shortcut-key">o&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>Open the file under the cursor</code></li>
        <li><code><span class="shortcut-key">a&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>Open all files</code></li>
        <li><code><span class="shortcut-key">j&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>Jump to next search result</code></li>
        <li><code><span class="shortcut-key">k&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>Jump to previous search result</code></li>
        <li><code><span class="shortcut-key">n&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>Scroll to next file</code></li>
        <li><code><span class="shortcut-key">p&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>Scroll to previous file</code></li>
        <li><code><span class="shortcut-key">f&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>Fold this file and move to the first match on next file</code></li>
        <li><code><span class="shortcut-key">?&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;&nbsp;</span>Show this shortcuts help</code></li>
    </ul>
</body>
</html>
"""


class OdyseusBfrFindInFilesOpenFileCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        for sel in view.sel():
            line_no = self.get_line_no(sel)
            file_name = self.get_file(sel)
            if line_no and file_name:
                file_loc = "%s:%s" % (file_name, line_no)
                view.window().open_file(file_loc, sublime.ENCODED_POSITION)
            elif file_name:
                view.window().open_file(file_name)

    def get_line_no(self, sel):
        view = self.view
        line_text = view.substr(view.line(sel))
        match = re.match(r"\s*(\d+).+", line_text)
        if match:
            return match.group(1)
        return None

    def get_file(self, sel):
        view = self.view
        line = view.line(sel)
        while line.begin() > 0:
            line_text = view.substr(line)
            match = re.match(r"(.+):$", line_text)
            if match:
                if os.path.exists(match.group(1)):
                    return match.group(1)
            line = view.line(line.begin() - 1)
        return None


class OdyseusBfrFindInFilesOpenAllFilesCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        view = self.view
        if view.name() == "Find Results":
            for file_name in self.get_files():
                view.window().open_file(file_name, sublime.ENCODED_POSITION)

    def get_files(self):
        view = self.view
        content = view.substr(sublime.Region(0, view.size()))
        return [match.group(1) for match in re.finditer(r"^([^\s].+):$", content, re.MULTILINE)]


class OdyseusBfrFindInFilesJumpCommand(sublime_plugin.TextCommand):
    def run(self, edit, forward=True, cycle=True):
        caret = self.view.sel()[0]
        matches = self.filter_matches(caret, self.find_matches())
        if forward:
            match = self.find_next_match(caret, matches, cycle)
        else:
            match = self.find_prev_match(caret, matches, cycle)
        if match:
            self.goto_match(match)

    def find_next_match(self, caret, matches, cycle):
        default = matches[0] if cycle and len(matches) else None
        return next((m for m in matches if caret.begin() < m.begin()), default)

    def filter_matches(self, caret, matches):
        footers = self.view.find_by_selector("footer.find-in-files")
        lower_bound = next((f.end() for f in reversed(footers) if f.end() < caret.begin()), 0)
        upper_bound = next((f.end() for f in footers if f.end() > caret.begin()), self.view.size())
        return [m for m in matches if m.begin() > lower_bound and m.begin() < upper_bound]

    def find_prev_match(self, caret, matches, cycle):
        default = matches[-1] if cycle and len(matches) else None
        return next((m for m in reversed(matches) if caret.begin() > m.begin()), default)

    def goto_match(self, match):
        self.view.sel().clear()
        self.view.sel().add(match)
        if self.view.is_folded(self.view.sel()[0]):
            self.view.unfold(self.view.sel()[0])


class OdyseusBfrFindInFilesJumpFileCommand(OdyseusBfrFindInFilesJumpCommand):
    def find_matches(self):
        return self.view.find_by_selector("entity.name.filename.find-in-files")

    def goto_match(self, match):
        v = self.view
        region = sublime.Region(match.begin(), match.begin())
        super().goto_match(region)
        top_offset = v.text_to_layout(region.begin())[1] - v.line_height()
        v.set_viewport_position((0, top_offset), True)


class OdyseusBfrFindInFilesJumpMatchCommand(OdyseusBfrFindInFilesJumpCommand):
    def find_matches(self):
        return self.view.get_regions("match")

    def goto_match(self, match):
        v = self.view
        super().goto_match(match)
        vx, vy = v.viewport_position()
        vw, vh = v.viewport_extent()
        x, y = v.text_to_layout(match.begin())
        h = v.line_height()
        if y < vy or y + h > vy + vh:
            v.show_at_center(match)


class OdyseusBfrTogglePopupHelpCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        popup_max_width = 800
        popup_max_height = 800
        self.view.show_popup(_popup_html, 0, -1, popup_max_width, popup_max_height)


class OdyseusBfrFoldAndMoveToNextFileCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        begin = self.get_begin()
        end = self.get_end()
        self.view.fold(sublime.Region(begin.b + 1, end.a - 1))
        sublime.set_timeout_async(self.move_to_next, 0)

    def move_to_next(self):
        self.view.run_command("find_in_files_jump_file")
        self.view.run_command("find_in_files_jump_match")

    def get_begin(self):
        view = self.view
        if len(view.sel()) == 1:
            line = view.line(view.sel()[0])
            while line.begin() > 0:
                line_text = view.substr(line)
                match = re.match(r"\S(.+):$", line_text)
                if match:
                    return(line)
                line = view.line(line.begin() - 1)
        return None

    def get_end(self):
        view = self.view
        if len(view.sel()) == 1:
            line = view.line(view.sel()[0])
            while line.end() <= view.size():
                line_text = view.substr(line)
                if len(line_text) == 0:
                    return(line)
                line = view.line(line.end() + 1)
        return None


class OdyseusBfrForceSytax(sublime_plugin.EventListener):
    def on_activated_async(self, view):
        if is_find_results(view):
            # NOTE: Do not assign syntax if it's already the desired synmtax.
            if view.settings().get("syntax") != _custom_syntax:
                view.assign_syntax(_custom_syntax)

            view.set_read_only(True)

    def on_deactivated_async(self, view):
        if is_find_results(view):
            view.set_read_only(False)


def is_find_results(view):
    return view and view.settings().get("syntax") and "Find Results" in view.settings().get("syntax")


if __name__ == "__main__":
    pass
