#!/usr/bin/env python3
# Copyright (c) 2026-present RopeOps contributors
# SPDX-License-Identifier: AGPL-3.0-only
# See the LICENSE file for details.
"""Fail when a PR modifies an upstream (Plane) file not listed in docs/UPSTREAM.md.

Usage: check_core_edits.py <base-ref>      e.g. origin/preview
Only modified, deleted and renamed files are checked; brand-new files are ours.
"""

import fnmatch
import re
import subprocess
import sys

OWNED = [
    "apps/api/ropeops*",
    "apps/api/plane/tests/*",
    ".github/scripts/*",
    "docs/*",
    "*/ropeops/*",
    ".github/workflows/ropeops-*",
]


def listed_files() -> list[str]:
    text = open("docs/UPSTREAM.md", encoding="utf-8").read()
    block = re.search(r"<!-- core-files:start -->(.*?)<!-- core-files:end -->", text, re.S)
    if not block:
        sys.exit("docs/UPSTREAM.md: core-files markers missing")
    return re.findall(r"^\|\s*`([^`]+)`", block.group(1), re.M)


def main(base: str) -> int:
    out = subprocess.run(
        ["git", "diff", "--name-status", "--diff-filter=MDR", f"{base}...HEAD"],
        check=True, capture_output=True, text=True,
    ).stdout
    allowed = OWNED + listed_files()
    bad = []
    for line in out.splitlines():
        parts = line.split("\t")
        for path in parts[1:]:  # for renames both old and new path count
            if not any(fnmatch.fnmatch(path, pat) for pat in allowed):
                bad.append(path)
    if bad:
        print("::error::These upstream files are modified but not listed in docs/UPSTREAM.md:")
        print("\n".join(sorted(set(bad))))
        print("Prefer a new app/hook/component. If a core edit is unavoidable, list it with the reason.")
        return 1
    print("Core-edit check passed.")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1]))
