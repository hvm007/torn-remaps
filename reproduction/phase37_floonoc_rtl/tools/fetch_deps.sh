#!/bin/bash
# Fetch FlooNoC and the four dependencies at the revisions used (from FlooNoC's Bender.lock).
# usage: tools/fetch_deps.sh DIR   -> DIR/FlooNoC and DIR/deps/{common_cells,common_verification,tech_cells_generic,axi}
set -e
D=${1:?target directory}; mkdir -p "$D/deps"; cd "$D"
git clone -q https://github.com/pulp-platform/FlooNoC.git && git -C FlooNoC checkout -q 3623659e1a8e3c788bb4bbf572caaf537670192f
for r in common_cells:63b7c50d43e462b59506f69d341ff1e40202866d common_verification:fb1885f48ea46164a10568aeff51884389f67ae3 \
         tech_cells_generic:3a3de73632a06826b1bd9c65a0a2e92b32016845 axi:0ccc838fe06aeeb857eb83c6be9a915c4bf99566; do
  n=${r%%:*}; c=${r#*:}
  git clone -q "https://github.com/pulp-platform/$n.git" "deps/$n" && git -C "deps/$n" checkout -q "$c"
done
echo "export FLOONOC=$PWD/FlooNoC DEPS=$PWD/deps"
echo "floogen: pip install $PWD/FlooNoC   (floogen 0.9.0)"
