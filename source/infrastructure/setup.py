# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0


import json
from pathlib import Path

import setuptools

readme_path = Path(__file__).resolve().parent.parent.parent / "README.md"
with open(readme_path) as fp:
    long_description = fp.read()

cdk_json_path = Path(__file__).resolve().parent / "cdk.json"
cdk_json = json.loads(cdk_json_path.read_text())
VERSION = cdk_json["context"]["SOLUTION_VERSION"]


setuptools.setup(
    name="infrastructure",
    version=VERSION,
    description="AWS CDK stack to deploy Audience Uploader from AWS Clean Rooms.",
    long_description=long_description,
    long_description_content_type="text/markdown",
    author="AWS Solutions Builders",
    packages=setuptools.find_packages(),
    install_requires=[
        "aws-cdk-lib>=2.7.0",
        "pip>=21.3",
    ],
    python_requires=">=3.7",
    classifiers=[
        "Development Status :: 4 - Beta",
        "Intended Audience :: Developers",
        "License :: OSI Approved :: Apache Software License",
        "Programming Language :: JavaScript",
        "Programming Language :: Python :: 3 :: Only",
        "Programming Language :: Python :: 3.7",
        "Programming Language :: Python :: 3.8",
        "Programming Language :: Python :: 3.9",
        "Topic :: Software Development :: Code Generators",
        "Topic :: Utilities",
        "Typing :: Typed",
    ],
)
