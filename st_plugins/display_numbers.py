#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
Based on: https://github.com/nia40m/sublime-display-nums

MIT License

Copyright (c) 2020 Nikita Sokolov

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
import json
import re

from functools import partial

import sublime
import sublime_plugin

from . import settings
from . import settings_utils
from python_utils.sublime_text_utils import queue

__all__ = [
    "OdyseusDnDisplayNumberListener",
    "OdyseusDnChangeBitCommand",
    "OdyseusDnConvertNumberCommand",
    "OdyseusDnShowNumbersPopupCommand",
    "OdyseusDnSwapEndiannessCommand",
    "OdyseusDnSwapPositionsCommand"
]

_plugin_id = "DisplayNumbers-{}"

split_re = re.compile(r"\B_\B", re.I)
dec_re = re.compile(r"^(0|([1-9][0-9]*))(u|l|ul|lu|ll|ull|llu)?$", re.I)
hex_re = re.compile(r"^0x([0-9a-f]+)(u|l|ul|lu|ll|ull|llu)?$", re.I)
oct_re = re.compile(r"^(0[0-7]+)(u|l|ul|lu|ll|ull|llu)?$", re.I)
bin_re = re.compile(r"^0b([01]+)(u|l|ul|lu|ll|ull|llu)?$", re.I)

space = "&nbsp;"
temp_small_space = "*"
small_space = "<span>" + space + "</span>"

_popup_html = """
<body id="display-numbers-popup">
<style>
    span     {{font-size: 0.35rem;}}
    #swap    {{color: var(--accent);}}
    #bits    {{color: var(--foreground);}}
    #options {{margin-top: 10px;}}
</style>
<div>
    <a href='{{"func": "copy", "data": "{hex}"}}'>C</a>
    <a href='{{"func": "odyseus_dn_convert_number", "data": {{"base":16}}}}'>Hex</a>:&nbsp;{hex}
</div>
<div>
    <a href='{{"func": "copy", "data": "{dec}"}}'>C</a>
    <a href='{{"func": "odyseus_dn_convert_number", "data": {{"base":10}}}}'>Dec</a>:&nbsp;{dec}
</div>
<div>
    <a href='{{"func": "copy", "data": "{oct}"}}'>C</a>
    <a href='{{"func": "odyseus_dn_convert_number", "data": {{"base":8}}}}'>Oct</a>:&nbsp;{oct}
</div>
<div>
    <a href='{{"func": "copy", "data": "{raw_bin}"}}'>C</a>
    <a href='{{"func": "odyseus_dn_convert_number", "data": {{"base":2}}}}'>Bin</a>:&nbsp;{bin}
</div>
<div id="swap">
    <a href='{{"func": "copy", "data": "{raw_pos}"}}'>C</a>
    <a href='{{"func": "odyseus_dn_swap_positions", "data": {{"base":{base}, "num":{num}}}}}'>Swap</a>&nbsp;{pos}
</div>
<div id="options">Swap endianness as
    <a href='{{"func": "odyseus_dn_swap_endianness", "data":{{"bits":16}}}}'>16 bit</a>
    <a href='{{"func": "odyseus_dn_swap_endianness", "data":{{"bits":32}}}}'>32 bit</a>
    <a href='{{"func": "odyseus_dn_swap_endianness", "data":{{"bits":64}}}}'>64 bit</a>
</div>
</body>
"""


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
    return settings.get("display_numbers.%s" % s, default)


def format_str(string, num, separator=" "):
    res = string[-num:]
    string = string[:-num]
    while len(string):
        res = string[-num:] + separator + res
        string = string[:-num]

    return res


def get_bits_positions(curr_bits_in_word, formatted=True):
    positions = ""
    start = 0

    while start < curr_bits_in_word:
        if get_settings("bit_positions_reversed", False):
            positions += "{: <4}".format(start)
        else:
            positions = "{: >4}".format(start) + positions

        start += 4

    if formatted:
        positions = format_str(positions, 2, temp_small_space * 3)
        positions = positions.replace(" ", space).replace(temp_small_space, small_space)

    return positions


def prepare_urls(s, base, num):
    res = ""
    offset = 0

    bit = """<a id="bits" href='{{ "func":"{func}", "data":{{"num":{num}, "base":{base}, "offset":{offset}}}}}'>{char}</a>"""

    for c in s[::-1]:
        if c.isdigit():
            res = bit.format(
                func="odyseus_dn_change_bit", num=num, base=base, offset=offset, char=c
            ) + res

            offset += 1
        else:
            res = c + res

    return res


def parse_number(text):
    # remove underscores in the number
    text = "".join(split_re.split(text))

    match = dec_re.match(text)
    if match:
        return {"number": int(match.group(1), 10), "base": 10}

    match = hex_re.match(text)
    if match:
        return {"number": int(match.group(1), 16), "base": 16}

    match = oct_re.match(text)
    if match:
        return {"number": int(match.group(1), 8), "base": 8}

    match = bin_re.match(text)
    if match:
        return {"number": int(match.group(1), 2), "base": 2}


def create_popup_content(number, base):
    # select max between (bit_length in settings) and (bit_length of selected number aligned to 4)
    curr_bits_in_word = max(get_bits_in_word(),
                            number.bit_length() + ((-number.bit_length()) & 0x3))

    return _popup_html.format(
        num=number,
        base=base,
        hex=format_str("{:x}".format(number), 2),
        dec=format_str("{}".format(number), 3, ","),
        oct=format_str("{:o}".format(number), 3),
        raw_bin=format_str("{:0={}b}".format(number, curr_bits_in_word), 4),
        bin=prepare_urls(
            format_str(
                format_str(
                    "{:0={}b}".format(number, curr_bits_in_word),
                    4,
                    temp_small_space),
                1,
                temp_small_space),
            base,
            number
        ).replace(temp_small_space, small_space),
        raw_pos=get_bits_positions(curr_bits_in_word, formatted=False),
        pos=get_bits_positions(curr_bits_in_word)
    )


def convert_number(num, base):
    if base == 10:
        return "{:d}".format(num)
    elif base == 16:
        return "0x{:x}".format(num)
    elif base == 2:
        return "0b{:b}".format(num)
    else:
        return "0{:o}".format(num)


def get_bits_in_word():
    bytes_in_word = get_settings("bytes_in_word", 4)

    if not isinstance(bytes_in_word, int):
        sublime.status_message("'display_numbers.bytes_in_word' setting must be an integer!")
        return 4 * 8

    return bytes_in_word * 8


class OdyseusDnDisplayNumberListener(sublime_plugin.EventListener):
    def on_text_command(self, view, command_name, args):
        double_click = command_name == "drag_select" and "by" in args and args["by"] == "words" and \
            view and len(view.sel())

        if double_click:
            queue.debounce(
                partial(view.run_command, "odyseus_dn_show_numbers_popup"),
                delay=100,
                key=_plugin_id.format("debounce")
            )


class OdyseusDnShowNumbersPopupCommand(sublime_plugin.TextCommand):
    def run(self, edit):
        if not self.view or not len(self.view.sel()):
            return

        parsed = parse_number(self.view.substr(self.view.sel()[0]).strip())

        if parsed is None:
            return

        html = create_popup_content(parsed["number"], parsed["base"])

        def select_function(href):
            data = json.loads(href)

            if data.get("func") is not None:
                if data.get("func") == "copy":
                    sublime.set_clipboard(data.get("data"))
                    sublime.status_message("Data copied to clipboard")
                else:
                    self.view.run_command(data.get("func"), data.get("data"))

        self.view.show_popup(
            html,
            flags=sublime.HIDE_ON_MOUSE_MOVE_AWAY if
            get_settings("hide_popup_on_mouse_move_away") else 0,
            max_width=1024,
            location=self.view.sel()[0].begin(),
            on_navigate=select_function
        )


class OdyseusDnConvertNumberCommand(sublime_plugin.TextCommand):
    def run(self, edit, base):
        if len(self.view.sel()) > 1:
            return self.view.hide_popup()

        selected_range = self.view.sel()[0]
        selected_number = self.view.substr(selected_range).strip()

        parsed = parse_number(selected_number)
        if parsed is None:
            return self.view.hide_popup()

        self.view.replace(edit, selected_range, convert_number(parsed["number"], base))


class OdyseusDnChangeBitCommand(sublime_plugin.TextCommand):
    def run(self, edit, base, num, offset):
        selected_range = self.view.sel()[0]
        self.view.replace(edit, selected_range, convert_number(num ^ (1 << offset), base))


class OdyseusDnSwapPositionsCommand(settings_utils.SettingsToggleBoolean,
                                    sublime_plugin.TextCommand):
    _ody_key = "display_numbers.bit_positions_reversed"
    _ody_settings = settings
    _ody_description = "Bit positions reversed - %s"
    _ody_true_label = "True"
    _ody_false_label = "False"

    def run(self, edit, base, num):
        super().run()

        self.view.update_popup(create_popup_content(num, base))


class OdyseusDnSwapEndiannessCommand(sublime_plugin.TextCommand):
    def run(self, edit, bits):
        if len(self.view.sel()) > 1:
            return self.view.hide_popup()

        selected_range = self.view.sel()[0]
        selected_number = self.view.substr(selected_range).strip()

        parsed = parse_number(selected_number)
        if parsed is None:
            return self.view.hide_popup()

        bit_len = parsed["number"].bit_length()
        # align bit length to bits
        bit_len = bit_len + ((-bit_len) & (bits - 1))

        bytes_len = bit_len // 8

        number = parsed["number"].to_bytes(bytes_len, byteorder="big")

        bytes_word = bits // 8

        result = []

        for i in range(bytes_word, bytes_len + 1, bytes_word):
            for j in range(0, bytes_word):
                result.append(number[i - j - 1])

        result = int.from_bytes(bytes(result), byteorder="big")

        self.view.replace(edit, selected_range, convert_number(result, parsed["base"]))


if __name__ == "__main__":
    pass
