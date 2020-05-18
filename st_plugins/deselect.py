#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Deselect.

Based on: https://github.com/glutanimate/sublime-deselect
"""
import sublime
import sublime_plugin

__all__ = [
    "OdyseusDeselectCommand"
]


class OdyseusDeselectCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        end = self.view.sel()[0].b
        pt = sublime.Region(end, end)
        self.view.sel().clear()
        self.view.sel().add(pt)


if __name__ == "__main__":
    pass
