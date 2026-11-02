#!/bin/sh
# placement-differential.sh OLD [NEW] [SEEDS]: run the placement differential against
# two builds and compare their output byte for byte. OLD and NEW are git tags, or
# WORKTREE for the checkout as it is (the default NEW). SEEDS defaults to 3000.
#
# Each build gets the same harness, scripts/placement-differential.cyr: seeded fleets
# and queues through four passes each, with every decision, log line and node state
# printed, then a set of probes. Exits 0 when the outputs are identical; otherwise it
# says how many lines differ and where the first one is.
set -eu
old="$1"; new="${2:-WORKTREE}"; seeds="${3:-3000}"
here="$(pwd)"
work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT

build() {
    dir="$work/$2"
    mkdir -p "$dir"
    if [ "$1" = WORKTREE ]; then
        cp -r VERSION cyrius.cyml cyrius.lock src dist "$dir/"
    else
        git -C "$here" archive "$1" | tar -x -C "$dir"
    fi
    units=1
    if grep -q SAMAY_ACCEL_WHOLE "$dir/src/types.cyr"; then units=1000; fi
    sed -e "s/@FROM@/0/" -e "s/@TO@/$seeds/" -e "s/@UNITS@/$units/" \
        "$here/scripts/placement-differential.cyr" > "$dir/diff.cyr"
    (cd "$dir" && rm -rf lib && mkdir lib && cyrius deps >/dev/null 2>&1 && cyrius build diff.cyr diff >/dev/null 2>&1)
    (cd "$dir" && ./diff > out.txt)
}

build "$old" old
build "$new" new
lines=$(wc -l < "$work/new/out.txt")
if cmp -s "$work/old/out.txt" "$work/new/out.txt"; then
    echo "placement-differential: $old and $new identical over $lines lines"
    exit 0
fi
echo "placement-differential: $old and $new differ in $(diff "$work/old/out.txt" "$work/new/out.txt" | grep -c '^<') of $lines lines"
diff "$work/old/out.txt" "$work/new/out.txt" | head -5
exit 1
