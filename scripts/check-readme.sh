#!/bin/sh
# check-readme.sh: compile and run the README's example, and check what it says it gives.
#
# The README claims this happens before every release. For several releases nothing did
# it, and the example did not compile. Run from the repo root. Exit 0 when the example
# builds, runs and gives `decisions=1`; non-zero otherwise.
set -eu

src=".readme-example.cyr"
bin="$(mktemp)"
trap 'rm -f "$src" "$bin"' EXIT

body="$(awk '/^var s = task_scheduler_new/ { on = 1 } on && /^```/ { exit } on { print "    " $0 }' README.md)"
if [ -z "$body" ]; then
    echo "check-readme: no example found in README.md" >&2
    exit 1
fi

{
    echo 'include "src/lib.cyr"'
    echo 'fn main(): i64 {'
    echo '    alloc_init();'
    echo "$body"
    echo '    syscall(1, 1, "decisions=", 10);'
    echo '    print_num(vec_len(decisions));'
    echo '    syscall(1, 1, "\n", 1);'
    echo '    return 0;'
    echo '}'
    echo 'var r = main();'
    echo 'syscall(60, r);'
} > "$src"

cyrius build "$src" "$bin"
out="$("$bin" 2>/dev/null)"
if [ "$out" != "decisions=1" ]; then
    echo "check-readme: expected decisions=1, got: $out" >&2
    exit 1
fi
echo "check-readme: ok, $out"
