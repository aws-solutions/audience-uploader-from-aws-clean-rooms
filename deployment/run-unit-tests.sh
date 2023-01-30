#!/bin/bash
# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

#
# This assumes all of the OS-level configuration has been completed and git repo has already been cloned
#
# This script should be run from the repo's deployment directory
# cd deployment
# ./run-unit-tests.sh
#

[ "$DEBUG" == 'true' ] && set -x
set -e

# Get reference for all important folders
template_dir="$PWD"
source_dir="$(cd $template_dir/../source; pwd -P)"
root_dir="$template_dir/.."
mkdir -p "$template_dir/cfn-templates"

echo "------------------------------------------------------------------------------"
echo "[Init] Clean old folders"
echo "------------------------------------------------------------------------------"

cd $root_dir
if [ -d ".venv" ]; then
  rm -rf ".venv"
fi

echo "------------------------------------------------------------------------------"
echo "Copy templates for unit tests"
echo "------------------------------------------------------------------------------"
cp "$template_dir/uploader-from-clean-rooms.yaml" "$template_dir/cfn-templates/uploader-from-clean-rooms.yaml"
cp "$template_dir/uploader-from-clean-rooms-glue.yaml" "$template_dir/cfn-templates/uploader-from-clean-rooms-glue.yaml"
cp "$template_dir/uploader-from-clean-rooms-auth.yaml" "$template_dir/cfn-templates/uploader-from-clean-rooms-auth.yaml"
cp "$template_dir/uploader-from-clean-rooms-web.yaml" "$template_dir/cfn-templates/uploader-from-clean-rooms-web.yaml"

echo "------------------------------------------------------------------------------"
echo "[Env] Create virtual environment and install dependencies"
echo "------------------------------------------------------------------------------"

virtualenv .venv
source .venv/bin/activate

cd $source_dir
pip install --upgrade pip
pip install -r $source_dir/requirements-dev.txt
cd -

echo "------------------------------------------------------------------------------"
echo "Audience Uploader from AWS Clean Rooms API Stack"
echo "------------------------------------------------------------------------------"

echo "Building API Lambda handler"
cd "$source_dir/api" || exit 1
[ -e dist ] && rm -rf dist
mkdir -p dist
if ! [ -x "$(command -v chalice)" ]; then
  echo 'Chalice is not installed. It is required for this solution. Exiting.'
  exit 1
fi

# Remove chalice deployments to force redeploy when there are changes to configuration only
# Otherwise, chalice will use the existing deployment package
[ -e .chalice/deployments ] && rm -rf .chalice/deployments

echo "Running chalice..."
chalice package --merge-template external_resources.json dist
echo "Finished running chalice."
echo "cp ./dist/sam.json $template_dir/cfn-templates/uploader-from-clean-rooms-api.yaml"
cp dist/sam.json "$template_dir/cfn-templates/uploader-from-clean-rooms-api.yaml"
if [ $? -ne 0 ]; then
  echo "ERROR: Failed to build  api template"
  exit 1
fi
rm -rf ./dist

echo "------------------------------------------------------------------------------"
echo "[Test] Run pytest with coverage"
echo "------------------------------------------------------------------------------"
cd $source_dir
# setup coverage report path
coverage_report_path=$source_dir/tests/coverage-reports/source.coverage.xml
echo "coverage report path set to $coverage_report_path"

pytest --cov --cov-report term-missing --cov-report term --cov-report "xml:$coverage_report_path"

# The pytest --cov with its parameters and .coveragerc generates a xml cov-report with `coverage/sources` list
# with absolute path for the source directories. To avoid dependencies of tools (such as SonarQube) on different
# absolute paths for source directories, this substitution is used to convert each absolute source directory
# path to the corresponding project relative path. The $source_dir holds the absolute path for source directory.
sed -i -e "s,<source>$source_dir,<source>source,g" $coverage_report_path

# deactivate the virtual environment
deactivate

cd $template_dir