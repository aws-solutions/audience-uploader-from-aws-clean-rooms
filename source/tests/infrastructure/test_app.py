# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0


import json
import os
from pathlib import Path
from unittest import mock

import pytest

from infrastructure.app import build_app
from infrastructure.app import solution as cdk_solution


@pytest.fixture
def cdk_json():
    path = Path(__file__).parents[2] / "infrastructure" / "cdk.json"
    return json.loads(path.read_text())


@mock.patch.dict(os.environ, {"BUCKET_NAME": "FAKEBUCKET"})
def test_deploy(cdk_json):
    """Ensures the template generates as expected and contains the correct metadata and mappings"""
    bucket_name = os.environ["BUCKET_NAME"]
    cdk_solution.reset()

    synth = build_app({"BUCKET_NAME": bucket_name})
    stack = synth.get_stack_by_name("uploader")

    assert stack.template["Metadata"]["aws:solutions:templatename"] == "audience-uploader-from-aws-clean-rooms.template"
    assert stack.template["Metadata"]["aws:solutions:solution_id"] == cdk_json["context"]["SOLUTION_ID"]
    assert stack.template["Metadata"]["aws:solutions:solution_version"] == cdk_json["context"]["SOLUTION_VERSION"]

    assert stack.template["Mappings"]["Solution"]["Data"]["ID"] == cdk_json["context"]["SOLUTION_ID"]
    assert stack.template["Mappings"]["Solution"]["Data"]["Version"] == cdk_json["context"]["SOLUTION_VERSION"]

    assert stack.template["Mappings"]["SourceCode"]["General"]["S3Bucket"] == bucket_name
    assert (
        stack.template["Mappings"]["SourceCode"]["General"]["KeyPrefix"]
        == f"{cdk_json['context']['SOLUTION_NAME']}/{cdk_json['context']['SOLUTION_VERSION']}"
    )
