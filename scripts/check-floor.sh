#!/bin/sh
# check-floor.sh: build and test on the oldest toolchain samay claims to support.
#
# The floor is `cyrius_floor` in cyrius.cyml, or the first argument. This re-vendors from
# an empty lib/ at samay's pinned deps, because the lib/ in the tree belongs to the
# current pin, and it works on a copy, so the checkout is left alone. Run from the repo
# root. Exit 0 when the demo builds and every test passes on that toolchain.
set -eu

floor="${1:-$(sed -n 's/^cyrius_floor = "\(.*\)"/\1/p' cyrius.cyml)}"
if [ -z "$floor" ]; then
    echo "check-floor: no cyrius_floor in cyrius.cyml" >&2
    exit 1
fi

work="$(mktemp -d)"
trap 'rm -rf "$work"' EXIT
cp -r VERSION cyrius.cyml src tests dist "$work/"
mkdir "$work/lib"
cd "$work"
sed -i "s/^cyrius = .*/cyrius = \"$floor\"/" cyrius.cyml

echo "check-floor: cyrius $floor"
cyrius deps
cyrius build src/main.cyr samay-floor
cyrius test tests/samay.tcyr
