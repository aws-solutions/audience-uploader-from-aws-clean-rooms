#!/bin/bash

deployment_dir="$PWD"
open_source_dir="$deployment_dir/open-source/"

echo "rm -rf $open_source_dir"
rm -rf "$open_source_dir"/
echo "mkdir -p $open_source_dir"
mkdir -p "$open_source_dir"
touch "$open_source_dir/.placeholder"