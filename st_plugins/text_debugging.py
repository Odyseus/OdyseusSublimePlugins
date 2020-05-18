#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Copyright (c) 2014, Colin T.A. Gray
All rights reserved.

Redistribution and use in source and binary forms, with or without
modification, are permitted provided that the following conditions are met:

1. Redistributions of source code must retain the above copyright notice, this
   list of conditions and the following disclaimer.
2. Redistributions in binary form must reproduce the above copyright notice,
   this list of conditions and the following disclaimer in the documentation
   and/or other materials provided with the distribution.

THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
(INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
(INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.

The views and conclusions contained in the software and documentation are those
of the authors and should not be interpreted as representing official policies,
either expressed or implied, of this project.
"""
import os
import re

import sublime
import sublime_plugin

__all__ = [
    "OdyseusTextDebuggingCommand",
    "OdyseusTextDebuggingJavaScriptCommand",
    "OdyseusTextDebuggingPythonCommand"
]


def indent_at(view, region):
    line_start = view.line(region).begin()
    line_indent = view.rowcol(region.a)[1]

    return view.substr(sublime.Region(line_start, line_start + line_indent))


class OdyseusTextDebuggingCommand(sublime_plugin.TextCommand):
    def run(self, edit, **kwargs):
        if not len(self.view.sel()):
            return

        location = self.view.sel()[0].begin()
        if self.view.score_selector(location, "source.python"):
            self.view.run_command("odyseus_text_debugging_python", kwargs)
        elif self.view.score_selector(location, "source.js"):
            self.view.run_command("odyseus_text_debugging_java_script", kwargs)
        elif self.view.score_selector(location, "source.php"):
            self.view.run_command("odyseus_text_debugging_php", kwargs)
        else:
            sublime.status_message("No support for the current language grammar.")


class OdyseusTextDebuggingPythonCommand(sublime_plugin.TextCommand):
    def run(self, edit, puts="print"):
        error = None
        empty_regions = []
        debug = ""
        debug_vars = []
        regions = list(self.view.sel())
        for region in regions:
            if not region:
                empty_regions.append(region)
            else:
                s = self.view.substr(region)
                if debug:
                    debug += "\n"
                debug += "{s}: {{{count}!r}}".format(s=s, count=1 + len(debug_vars))
                debug_vars.append(s)
                self.view.sel().subtract(region)

        if not empty_regions:
            sublime.status_message("You must place an empty cursor somewhere")
            return

        # any edits that are performed will happen in reverse; this makes it
        # easy to keep region.a and region.b pointing to the correct locations
        def get_end(region):
            return region.end()
        empty_regions.sort(key=get_end, reverse=True)

        if self.view.file_name():
            name = os.path.basename(self.view.file_name())
        elif self.view.name():
            name = self.view.name()
        else:
            name = "Untitled"

        if debug:
            output = puts + \
                '("""=============== {name} at line {{0}} ==============='.format(name=name)
            output += "\n" + debug + "\n"
            output += '""".format(__import__(\'sys\')._getframe().f_lineno - {lines}, '.format(
                lines=1 + len(debug_vars))
            for var in debug_vars:
                output += var.strip() + ', '
            output += '))'
        else:
            output = puts + \
                '("=============== {name} at line {{0}} ===============".format(__import__(\'sys\')._getframe().f_lineno))'.format(
                    name=name)

        for empty in empty_regions:
            self.view.insert(edit, empty.a, output)

        if error:
            sublime.status_message(error)


class OdyseusTextDebuggingJavaScriptCommand(sublime_plugin.TextCommand):
    def run(self, edit, puts="console.log"):
        error = None
        empty_regions = []
        debugs = []
        regions = list(self.view.sel())
        for region in regions:
            if not region:
                empty_regions.append(region)
            else:
                s = self.view.substr(region)
                if re.match(r"^\w+$", s):
                    debugs.append(s)
                else:
                    debugs.append("'{s_escaped}': {s}".format(s=s, s_escaped=s.replace("'", "\\'")))
                self.view.sel().subtract(region)

        # any edits that are performed will happen in reverse; this makes it
        # easy to keep region.a and region.b pointing to the correct locations
        def get_end(region):
            return region.end()
        empty_regions.sort(key=get_end, reverse=True)

        if not empty_regions:
            sublime.status_message("You must place an empty cursor somewhere")
        else:
            if self.view.file_name():
                name = os.path.basename(self.view.file_name())
            elif self.view.name():
                name = self.view.name()
            else:
                name = "Untitled"

            output = puts + \
                "('=============== {name} at line line_no ===============');\n".format(name=name)
            if debugs:
                output += puts + "({ "
                first = True
                for debug in debugs:
                    if not first:
                        output += ", "
                    first = False
                    output += debug
                output += " })\n"
            output = output[:-1]

            for empty in empty_regions:
                indent = indent_at(self.view, empty)
                line_no = self.view.rowcol(empty.a)[0] + 1
                line_output = output.replace(
                    "\n", "\n{0}".format(indent)).replace(
                    "line_no", str(line_no))
                self.view.insert(edit, empty.a, line_output)

        if error:
            sublime.status_message(error)


if __name__ == "__main__":
    pass
