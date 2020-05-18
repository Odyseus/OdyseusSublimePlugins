#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Render reStructuredText files as HTML and display them in default browser.
    Based on: https://github.com/d0ugal/RstPreview
"""
import string

from random import sample

import sublime_plugin

__all__ = [
    "OdyseusPasswordGeneratorCommand"
]


class OdyseusPasswordGeneratorCommand(sublime_plugin.TextCommand):
    chars = string.ascii_letters + string.digits
    chars_plus_symbols = chars + "!@#$%^&*_-+=|/?:;<>~"

    def run(self, edit, length=30, symbols=True):
        population = self.chars_plus_symbols if symbols else self.chars

        for region in self.view.sel():
            p = "".join(sample(population, length))
            self.view.replace(edit, region, p)


if __name__ == "__main__":
    pass
