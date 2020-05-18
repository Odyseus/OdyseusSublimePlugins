#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Based on https://github.com/NicholasBuse/sublime_DeleteBlankLines
"""
import sublime
import sublime_plugin

__all__ = [
    "OdyseusDeleteBlankLinesCommand"
]


class OdyseusDeleteBlankLinesCommand(sublime_plugin.TextCommand):
    def run(self, edit, surplus=False, whole_file=False):
        new_selections = []

        if whole_file:
            self._ody_strip(edit, sublime.Region(0, self.view.size()), surplus)
        else:
            for selection in self.view.sel():
                # Strip blank lines
                new_selections.append(self._ody_strip(edit, selection, surplus))

            # Clear selections since they've been modified.
            self.view.sel().clear()

            for new_sel in new_selections:
                self.view.sel().add(new_sel)

    def _ody_strip(self, edit, selection, surplus):
        # Convert the input range to a string, this represents the original selection.
        orig = self.view.substr(selection)
        lines = orig.splitlines()

        i = 0
        have_blank = False

        while i < len(lines) - 1:
            if lines[i].rstrip() == "":
                if not surplus or have_blank:
                    del lines[i]
                else:
                    i += 1
                have_blank = True
            else:
                have_blank = False
                i += 1

        output = "\n".join(lines)

        self.view.replace(edit, selection, output)

        return sublime.Region(selection.begin(), selection.begin() + len(output))


if __name__ == "__main__":
    pass
