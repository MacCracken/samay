#!/usr/bin/env python3
"""mutate.py: break src/ one line at a time, and check the tests notice.

Coverage says a line ran, not that any test would miss it. 1.4.2 had every public
function covered, and 24% of these mutants survived: most of task_scheduler_stats, and
placement could ignore disk altogether.

Each mutant flips a comparison, swaps `return 0` and `return 1`, nudges a `+ 1`, or
deletes a statement, then runs the suite on a copy of the tree. OOM guards and log text
are left alone. A mutant the suite cannot tell apart from the real code survives. Some
survivors can never be told apart: a `0 - 1` sentinel becoming `0 - 2`, a store of zero
into zeroed memory, a return nobody reads. scripts/mutation-baseline.txt lists the ones
already read and accepted, and a survivor not on that list fails the run.

A kill can depend on the per-process hash seed: with two nodes the table can pick the right
answer with the tie-break gone. So a survivor gets more seeds, one kill counts, and a kill
that needed a retry is printed, because a test there is passing by luck.

  scripts/mutate.py                 check against the baseline, exit 1 on a new survivor
  scripts/mutate.py --jobs 8        the same, with 8 workers (default: every core)
  scripts/mutate.py --file src/uuid.cyr  just that file, which takes seconds to minutes
  scripts/mutate.py --write-baseline  accept this run's survivors. Read them first.

Run from the repo root, locally only, never in CI: about 13 minutes on 12 workers, and about 45
on a CI runner.
"""
import argparse
import collections
import concurrent.futures
import os
import re
import shutil
import subprocess
import sys
import tempfile
import threading

FILES = ["src/types.cyr", "src/scheduler.cyr", "src/cronexpr.cyr", "src/cron.cyr",
         "src/training.cyr", "src/json.cyr", "src/uuid.cyr"]
TREE = ["src", "tests", "dist", "lib"]
TOP = ["VERSION", "cyrius.cyml", "cyrius.lock"]
BASELINE = "scripts/mutation-baseline.txt"
TIMEOUT = 60
RETRIES = 2

# Nothing on these lines can be tested, or they are text rather than behaviour.
SKIP = re.compile(r'panic\(|sakshi_|_samay_own|^\s*#|^\s*$|^#derive|str_builder_add|"samay: out of memory')
OPS = [(r"==", "!="), (r"!=", "=="), (r"<=", "<"), (r">=", ">"),
       (r"(?<![<>=!])<(?![<=])", "<="), (r"(?<![<>=!-])>(?![>=])", ">=")]


def code_part(line):
    """The line up to any comment, leaving a # inside a string alone."""
    quoted = False
    for i, c in enumerate(line):
        if c == '"' and (i == 0 or line[i - 1] != "\\"):
            quoted = not quoted
        if c == "#" and not quoted:
            return line[:i]
    return line


def blank_strings(line):
    return re.sub(r'"(\\.|[^"\\])*"', lambda m: "\x00" * len(m.group(0)), line)


def mutants(files):
    """Every (file, line index, kind, replacement line) in `files`."""
    out = []
    for path in files:
        lines = open(path).read().split("\n")
        in_fn = False
        for n, line in enumerate(lines):
            if line.startswith("fn "):
                in_fn = True
            if line.startswith("}"):
                in_fn = False
                continue
            if not in_fn or line.startswith("fn "):
                continue
            code = code_part(line)
            if SKIP.search(code):
                continue
            plain = blank_strings(code)
            for pattern, repl in OPS:
                for m in re.finditer(pattern, plain):
                    out.append((path, n, f"{m.group(0)}->{repl}", line[:m.start()] + repl + line[m.end():]))
            for m in re.finditer(r"return (0|1);", plain):
                other = "1" if m.group(1) == "0" else "0"
                out.append((path, n, f"return {m.group(1)}->{other}", line[:m.start()] + f"return {other};" + line[m.end():]))
            for m in re.finditer(r"([+-]) 1\b", plain):
                repl = "+ 2" if m.group(1) == "+" else "- 2"
                out.append((path, n, f"{m.group(0)}->{repl}", line[:m.start()] + repl + line[m.end():]))
            statement = code.strip()
            if re.match(r"^[A-Za-z_][A-Za-z0-9_]*\(.*\);$", statement) or re.match(r"^[a-z_][a-z0-9_]* = .*;$", statement):
                out.append((path, n, "delete-stmt", ""))
    return out


def key(path, kind, was):
    return f"{path}\t{kind}\t{was.strip()}"


def main():
    parser = argparse.ArgumentParser(description="whole-source mutation check")
    parser.add_argument("--jobs", type=int, default=os.cpu_count() or 2)
    parser.add_argument("--file", choices=FILES, help="mutate only this file")
    parser.add_argument("--write-baseline", action="store_true")
    args = parser.parse_args()
    if args.file and args.write_baseline:
        parser.error("--write-baseline needs a whole run")

    muts = mutants([args.file] if args.file else FILES)
    print(f"{len(muts)} mutants, {args.jobs} workers", flush=True)
    originals = {path: open(path).read() for path in FILES}
    root = tempfile.mkdtemp(prefix="samay-mutate.")
    local = threading.local()
    lock = threading.Lock()
    done = [0]
    survivors = []
    lucky = []

    def worktree():
        if not hasattr(local, "tree"):
            tree = tempfile.mkdtemp(dir=root)
            for name in TOP:
                shutil.copy2(name, tree)
            for name in TREE:
                shutil.copytree(name, os.path.join(tree, name), symlinks=True)
            local.tree = tree
        return local.tree

    def suite(tree):
        try:
            r = subprocess.run(["cyrius", "test", "tests/samay.tcyr"], cwd=tree, capture_output=True, timeout=TIMEOUT)
        except subprocess.TimeoutExpired:
            return "killed"
        text = r.stdout.decode(errors="replace") + r.stderr.decode(errors="replace")
        if "compiler exit" in text:
            return "nocompile"
        return "survived" if r.returncode == 0 and " 0 failed" in text else "killed"

    def run(mut):
        path, n, kind, new = mut
        tree = worktree()
        lines = originals[path].split("\n")
        was = lines[n]
        lines[n] = new
        with open(os.path.join(tree, path), "w") as f:
            f.write("\n".join(lines))
        result = suite(tree)
        retries = 0
        while result == "survived" and retries < RETRIES:
            retries += 1
            result = suite(tree)
        with open(os.path.join(tree, path), "w") as f:
            f.write(originals[path])
        with lock:
            done[0] += 1
            if result == "survived":
                survivors.append(key(path, kind, was))
            elif retries:
                lucky.append(key(path, kind, was))
            if done[0] % 200 == 0:
                print(f"  {done[0]}/{len(muts)}", flush=True)
        return result

    try:
        with concurrent.futures.ThreadPoolExecutor(args.jobs) as pool:
            results = collections.Counter(pool.map(run, muts))
    finally:
        shutil.rmtree(root, ignore_errors=True)

    print(f"killed {results['killed']}, survived {results['survived']}, did not compile {results['nocompile']}")
    if lucky:
        print(f"{len(lucky)} killed only on a retry: a test here depends on the hash seed")
        for line in sorted(lucky):
            print("  " + line)
    if args.write_baseline:
        with open(BASELINE, "w") as f:
            f.write("".join(line + "\n" for line in sorted(survivors)))
        print(f"wrote {len(survivors)} survivors to {BASELINE}")
        return 0

    accepted = collections.Counter(line for line in open(BASELINE).read().splitlines()
                                   if not args.file or line.startswith(args.file + "\t"))
    new = collections.Counter(survivors) - accepted
    gone = accepted - collections.Counter(survivors)
    if gone:
        print(f"{sum(gone.values())} accepted survivor(s) are now killed: refresh the baseline")
    if new:
        print(f"{sum(new.values())} NEW survivor(s): a test should notice these")
        for line in sorted(new):
            print("  " + line)
        return 1
    print("no new survivors")
    return 0


if __name__ == "__main__":
    sys.exit(main())
