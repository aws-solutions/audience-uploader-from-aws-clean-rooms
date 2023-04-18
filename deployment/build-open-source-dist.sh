#!/bin/bash
#
# This assumes all of the OS-level configuration has been completed and git repo has already been cloned
#
# This script should be run from the repo's deployment directory
# cd deployment
# ./build-open-source-dist.sh
#

source_template_dir="$PWD"
dist_dir="$source_template_dir/open-source"
placeholder="$dist_dir/placeholder.txt"

echo "------------------------------------------------------------------------------"
echo "[Init] Clean old open-source folder"
echo "------------------------------------------------------------------------------"

set -xeuo pipefail

rm -rf $dist_dir
mkdir -p $dist_dir
touch $placeholder
