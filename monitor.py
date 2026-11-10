#!/usr/bin/env python3
"""Convenience launcher:  python3 monitor.py [options]

Same as  python3 -m health_monitor [options]
"""

import sys

from health_monitor.__main__ import main

if __name__ == "__main__":
    sys.exit(main())
