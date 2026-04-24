#!/bin/bash

CYCLONEDDS_ROOT="$(pwd)/cyclonedds"
INSTALL_PREFIX="$CYCLONEDDS_ROOT/install"

# this script installs CycloneDDS in `./cyclonedds`
# and creates a source script to export the CYCLONEDDS_HOME environment variable

git clone https://github.com/eclipse-cyclonedds/cyclonedds "$CYCLONEDDS_ROOT"
cd "$CYCLONEDDS_ROOT"
mkdir "$CYCLONEDDS_ROOT/build" "$INSTALL_PREFIX"
cd "$CYCLONEDDS_ROOT/build"
cmake .. -DCMAKE_INSTALL_PREFIX="$INSTALL_PREFIX"
cmake --build . --config RelWithDebInfo --target install

cat > "$CYCLONEDDS_ROOT/source_cyclonedds.sh" <<EOF
export CYCLONEDDS_HOME="$INSTALL_PREFIX"
export LD_LIBRARY_PATH="\$CYCLONEDDS_HOME/lib:\$LD_LIBRARY_PATH"
EOF
