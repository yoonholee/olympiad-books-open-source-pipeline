#!/usr/bin/env bash
set -euo pipefail

DIR="$(cd "$(dirname "$0")" && pwd)"
SRC="$DIR/src"
mkdir -p "$SRC"

clone() {
    local name="$1" url="$2"
    if [ -d "$SRC/$name" ]; then
        echo "  SKIP (exists): $name"
    else
        echo "  Cloning $name..."
        git clone --depth 1 "$url" "$SRC/$name"
    fi
}

clone napkin         https://github.com/vEnhance/napkin.git
clone sundstrom-textbook https://github.com/gvsuoer/sundstrom-textbook.git
clone ecm            https://github.com/oscarlevin/ecm.git
clone discrete-book  https://github.com/oscarlevin/discrete-book.git
clone aata           https://github.com/twjudson/aata.git
clone applied-combinatorics https://github.com/mitchkeller/applied-combinatorics.git
clone bogart         https://github.com/OpenMathBooks/bogart.git
clone fcla           https://github.com/rbeezer/fcla.git
clone ent            https://github.com/williamstein/ent.git
clone ra             https://github.com/jirilebl/ra.git
clone IBL-IntroToProof https://github.com/dcernst/IBL-IntroToProof.git
clone OpenLogic      https://github.com/OpenLogicProject/OpenLogic.git

echo "Done. All sources in $SRC/"
