#!/usr/bin/python3
# -*- coding: utf-8 -*-
"""NOTE: Everything is inside the ``if __name__ == "__main__"`` comparisson so Sublime doesn't execute it.
"""
if __name__ == "__main__":
    import sys

    from __app__.python_modules.cli import main

    if len(sys.argv) == 1:
        sys.argv.append("--help")

    sys.exit(main())
