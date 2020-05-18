#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""
"""
try:
    import xmltodict
except (ImportError, SystemError):
    raise SystemExit("Required <xmltodict> Python module not found.")

import argparse
import json
import os


def read_xml(input_path):
    snippet = False
    with open(input_path, "r", encoding="UTF-8") as input_file:
        try:
            snippet = xmltodict.parse(input_file.read())["snippet"]
        except Exception as err:
            print(err)

    return snippet


def format_snippet(snippet_json):
    description = snippet_json.get("description", "")
    return (snippet_json.get("scope", False), {
        "trigger": "%s%s" % (snippet_json.get("tabTrigger", ""),
                             "\t" + description if description else ""),
        "contents": snippet_json.get("content", "")
    })


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("folder_path", type=str)

    args = parser.parse_args()
    snippet_files = []
    snippets_json = {}

    if os.path.isdir(args.folder_path):
        snippet_files = [os.path.join(args.folder_path, fp) for fp in os.listdir(
            args.folder_path) if fp.endswith(".sublime-snippet")]
    else:
        raise SystemExit("Path is not a folder:\n%s" % args.folder_path)

    for s in snippet_files:
        scope, completion = format_snippet(read_xml(s))

        if scope and completion.get("trigger") and completion.get("contents"):
            if scope not in snippets_json:
                snippets_json[scope] = []

            snippets_json[scope].append(completion)

    print(json.dumps(snippets_json, indent=4, separators=(",", ": ")))

    raise SystemExit(0)
