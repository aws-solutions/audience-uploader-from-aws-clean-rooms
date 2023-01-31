# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0


import setuptools


setuptools.setup(
    name="chalicelib",
    version="2.0.0",
    description="Audience Uploader from AWS Clean Rooms - Lambda Functions",
    author="AWS Solutions Builders",
    packages=setuptools.find_packages(exclude=("shared",)),
    package_data={"": ["*.json", "*.yaml"]},
    include_package_data=True,
    python_requires=">=3.7",
    install_requires=["chalice"],
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