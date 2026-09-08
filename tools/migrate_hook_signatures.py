#!/usr/bin/env python
# coding: utf-8

"""
Migrate TaskArrayFunction hook signatures from the columnflow v0.2.x API to v0.3.1.

columnflow v0.3.1 calls the hooks with a `task` argument:

    columnar_util.py:2986   self.requires_func(task=task, reqs=reqs[self.cls_name])

so every `*_requires` and `*_setup` in the analysis needs `task` in its
signature, and every `*_init` needs `**kwargs`. Without it you get
`TypeError: <name>_requires() got an unexpected keyword argument 'task'` at
dependency-scheduling time -- late, and one file per run.

`**kwargs` is added everywhere, including where it is unused, so the next
signature addition upstream is absorbed instead of breaking the same way again.

Type annotations are deliberately NOT added to `task`: most of these files do
not import `law`, and the annotation is documentation rather than enforcement.

Usage:
    python tools/migrate_hook_signatures.py --dry-run    # show what would change
    python tools/migrate_hook_signatures.py              # apply
"""

from __future__ import annotations

import argparse
import pathlib
import re
import sys


# Hooks that gained a `task` argument. It goes first, right after `self`.
TASK_HOOKS = ("_requires", "_setup")

# Hooks that only need **kwargs. `task` is not passed to init in v0.3.1 --
# that is what the new `post_init` hook is for.
KWARGS_ONLY_HOOKS = ("_init",)

# law Task methods that happen to end with one of the suffixes above but are
# NOT TaskArrayFunction hooks. Rewriting these would break the law workflow API.
EXCLUDE_NAMES = frozenset({
    "workflow_requires",
    "requires",
    "setup",
    "init",
})


def split_params(sig: str) -> list[str]:
    """Split a parameter list on top-level commas, respecting brackets."""
    parts, depth, current = [], 0, ""
    for ch in sig:
        if ch in "[({":
            depth += 1
        elif ch in "])}":
            depth -= 1
        if ch == "," and depth == 0:
            parts.append(current)
            current = ""
        else:
            current += ch
    if current.strip():
        parts.append(current)
    return [p.strip() for p in parts if p.strip()]


def migrate_signature(params: list[str], add_task: bool) -> tuple[list[str], bool]:
    """Return the new parameter list and whether anything changed."""
    names = [p.split(":")[0].split("=")[0].strip().lstrip("*") for p in params]
    changed = False

    if add_task and "task" not in names:
        # insert directly after self, matching the upstream ordering
        params = [params[0], "task"] + params[1:]
        changed = True

    if not any(p.startswith("**") for p in params):
        params = params + ["**kwargs"]
        changed = True

    return params, changed


def process(path: pathlib.Path, dry_run: bool) -> list[str]:
    text = path.read_text()
    report = []

    # match `def <name>(<params>) -> <ret>:` across lines, non-greedy on params
    pattern = re.compile(
        r"(?P<indent>[ \t]*)def (?P<name>\w+)\((?P<params>.*?)\)(?P<ret>\s*->\s*[^\n:]+)?:",
        re.S,
    )

    out, last = [], 0
    for m in pattern.finditer(text):
        name = m.group("name")
        if name in EXCLUDE_NAMES:
            continue
        add_task = name.endswith(TASK_HOOKS)
        kwargs_only = name.endswith(KWARGS_ONLY_HOOKS)
        if not (add_task or kwargs_only):
            continue

        params = split_params(m.group("params"))
        if not params or params[0].split(":")[0].strip() != "self":
            # not a hook (module-level helper, or a law Task method)
            continue

        new_params, changed = migrate_signature(params, add_task)
        if not changed:
            continue

        indent = m.group("indent")
        ret = m.group("ret") or ""
        # always write multi-line: these signatures are long once task is added
        body = ",\n".join(f"{indent}    {p}" for p in new_params)
        replacement = f"{indent}def {name}(\n{body},\n{indent}){ret}:"

        out.append(text[last:m.start()])
        out.append(replacement)
        last = m.end()
        report.append(f"  {name}: {', '.join(params)}  ->  {', '.join(new_params)}")

    if not report:
        return []

    out.append(text[last:])
    new_text = "".join(out)

    # self.task no longer exists inside the hooks; the argument replaces it
    new_text, n_self_task = re.subn(r"\bself\.task\b", "task", new_text)
    if n_self_task:
        report.append(f"  ({n_self_task} occurrence(s) of self.task -> task)")

    if not dry_run:
        path.write_text(new_text)

    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.split("\n")[1])
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--root", default="azh")
    args = parser.parse_args(argv)

    root = pathlib.Path(args.root)
    if not root.is_dir():
        print(f"no such directory: {root}", file=sys.stderr)
        return 1

    total = 0
    for path in sorted(root.rglob("*.py")):
        report = process(path, args.dry_run)
        if report:
            print(f"{path}")
            print("\n".join(report))
            total += len([r for r in report if not r.startswith("  (")])

    verb = "would change" if args.dry_run else "changed"
    print(f"\n{verb} {total} hook signature(s)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
