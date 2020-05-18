#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""Script to convert HTML markup into HTML5.

I use it mainly to convert HTML4 to HTML5 and to correctly mark up HTML that do not use closing
tags. I would like to "meet" the ones that decided that it's OK to use the latter aberration!!!

It's a script because it uses a third-party Python module and because who in the f*ck uses Python 3.3!?!?!?
Only Sublime Text, that's who!!!! FFS!!!

Attributes
----------
docopt_doc : str
    Used to store/define the docstring that will be passed to docopt as the "doc" argument.
root_folder : str
    The main folder containing the application and from which to import shared modules.
"""
try:
    import html5lib
except (ImportError, SystemError):
    raise SystemExit("Required <html5lib> Python module not found.")

__appname__ = "HTML5 converter"
__version__ = "Ω"

import os
import sys


root_folder = os.path.realpath(os.path.abspath(os.path.join(
    os.path.normpath(os.path.join(os.path.dirname(__file__), os.pardir)))))

sys.path.insert(0, root_folder)

from __app__.python_modules.python_utils.docopt import docopt

_args_map = {
    "--quote-attr-values": "quote_attr_values",
    "--quote-char": "quote_char",
    "--omit-optional-tags": "omit_optional_tags",
    "--minimize-boolean-attributes": "minimize_boolean_attributes",
    "--use-trailing-solidus": "use_trailing_solidus",
    "--space-before-trailing-solidus": "space_before_trailing_solidus",
    "--escape-lt-in-attrs": "escape_lt_in_attrs",
    "--escape-rcdata": "escape_rcdata",
    "--resolve-entities": "resolve_entities",
    "--alphabetical-attributes": "alphabetical_attributes",
    "--inject-meta-charset": "inject_meta_charset",
    "--strip-whitespace": "strip_whitespace",
    "--sanitize": "sanitize"
}

docopt_doc = """{appname} {version}

Convert HTML markup into HTML5.
It only accepts input from STDIN and outputs into STDOUT.

Usage:
    html5_converter.py [--doctype-declaration=<doctype>]
                       [--quote-attr-values=<value>]
                       [--quote-char=<char>]
                       [--omit-optional-tags]
                       [--minimize-boolean-attributes]
                       [--use-trailing-solidus]
                       [--space-before-trailing-solidus]
                       [--escape-lt-in-attrs]
                       [--escape-rcdata]
                       [--resolve-entities]
                       [--alphabetical-attributes]
                       [--inject-meta-charset]
                       [--strip-whitespace]
                       [--sanitize]

Options:

-h, --help
    Show this screen.

--version
    Show application version.

--doctype-declaration=<doctype>
    Description. [Default: <!DOCTYPE html>]

--quote-attr-values=<value>
    Whether to quote attribute values that don't require quoting per legacy
    browser behavior (``legacy``), when required by the standard
    (``spec``), or always (``always``). [Default: legacy]

--quote-char=<char>
    Use given quote character for attribute quoting. Defaults to ``"`` which
    will use double quotes unless attribute value contains a double quote,
    in which case single quotes are used. [Default: "]

--omit-optional-tags
    Omit start/end tags that are optional.

--minimize-boolean-attributes
    Shortens boolean attributes to give just the attribute value, for example:
    **<input disabled="disabled">** becomes **<input disabled>**.

--use-trailing-solidus
    Includes a close-tag slash at the end of the start tag of void elements
    (empty elements whose end tag is forbidden). E.g. ``<hr/>``.

--space-before-trailing-solidus
    Places a space immediately before the closing slash in a tag using a
    trailing solidus. E.g. ``<hr />``. Requires ``--use-trailing-solidus``.

--escape-lt-in-attrs
    Whether or not to escape ``<`` in attribute values.

--escape-rcdata
    Whether to escape characters that need to be escaped within normal elements
    within rcdata elements such as style.

--resolve-entities
    Whether to resolve named character entities that appear in the source tree.
    The XML predefined entities &lt; &gt; &amp; &quot; &apos; are unaffected
    by this setting.

--alphabetical-attributes
    Reorder attributes to be in alphabetical order.

--inject-meta-charset
    Whether or not to inject the meta charset.

--strip-whitespace
    Whether to remove semantically meaningless whitespace. (This compresses all
    whitespace to a single space except within ``pre``.)

--sanitize
    Strip all unsafe or unknown constructs from output.
    See :py:class:`html5lib.filters.sanitizer.Filter`.


""".format(appname=__appname__,
           version=__version__)

if __name__ == "__main__":
    args = docopt(docopt_doc, version="%s %s" % (__appname__, __version__))
    serializer_args = {val: args[key] for key, val in _args_map.items()}

    html_output = []

    try:
        if sys.stdin.isatty():
            raise RuntimeError("No STDIN passed.")

        html_data = sys.stdin.read().strip()

        if not html_data:
            raise RuntimeError("STDIN is empty.")

        element = html5lib.parse(html_data)
        walker = html5lib.getTreeWalker("etree")
        stream = walker(element)
        serializer = html5lib.serializer.HTMLSerializer(**serializer_args)
        output = serializer.serialize(stream)

        for item in output:
            html_output.append(item)
    except Exception as err:
        raise SystemExit(err)

    if html_output:
        if args["--doctype-declaration"]:
            html_output.insert(0, args["--doctype-declaration"])
            html_output.insert(1, "\n")

        sys.stdout.write("".join(html_output))

    raise SystemExit(0)
