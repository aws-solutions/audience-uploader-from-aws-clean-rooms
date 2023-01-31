# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0


import aws_cdk.assertions as assertions
import pytest
from pathlib import Path
from aws_cdk import cloudformation_include as cfn_inc
from aws_cdk.assertions import Template, Match, Capture
import aws_cdk as cdk
from lib.uploader_stack import UploaderStack
from aws_solutions.cdk import CDKSolution

# Create the stack in a fixture - pass the fixture to each test
@pytest.fixture(scope="module")
def synth_nested_template():

    FAKE_CONTEXT = {
        "SOLUTION_ID": "SO0226",
        "SOLUTION_VERSION": "V1.0.0",
        "BUCKET_NAME": "FAKEBUCKETNAME",
        "SOLUTION_NAME": "FAKESOLUTIONNAME",
        "APP_REGISTRY_NAME": "FAKEAPPREGISTRYNAME",
        "VERSION": "v1.0.0",
    }
    app = cdk.App(context=FAKE_CONTEXT)
    solution = CDKSolution(cdk_json_path=Path(__file__).parent.parent.parent.absolute() / "infrastructure/cdk.json")

    uploader_stack = UploaderStack(
        app,
        "uploader",
        stack_name=app.node.try_get_context("STACK_NAME"),
        description=f"Audience Uploader from AWS Clean Rooms Solution CDK stack",
        template_filename="audience-uploader-from-aws-clean-rooms.template",
        synthesizer=solution.synthesizer,
    )
    # these next two lines of code will work once we get the JSON error fixed!
    # snap_uploader = uploader_stack.snap_stack
    glue_stack = uploader_stack.cf_stack.get_nested_stack("GlueStack")
    # web_stack = uploader_stack.cf_stack.get_nested_stack("WebStack")
    # api_stack = uploader_stack.cf_stack.get_nested_stack("ApiStack")

    template = Template.from_stack(glue_stack.stack)
    yield template


# there are two roles for this nested stack
def test_iam_role_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::IAM::Role", 2)

    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "AssumeRolePolicyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Principal": {"Service": ["lambda.amazonaws.com"]},
                        "Action": ["sts:AssumeRole"],
                    }
                ],
            }
        },
    )


def test_lambda_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::Lambda::Function", 1)

    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Handler": "index.lambda_handler",
            "MemorySize": 256,
            "Runtime": "python3.9",
            "Tags": [{"Key": "environment", "Value": Match.any_value()}],
            "Timeout": 900,
        },
    )


def test_glue_job_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::Glue::Job", 1)

    role_arn = Capture()
    artifact_bucket_name = Capture()

    template.has_resource_properties(
        "AWS::Glue::Job",
        {
            "Command": {
                "Name": "glueetl",
                "PythonVersion": "3",
                "ScriptLocation": {
                    "Fn::Join": [
                        "",
                        [
                            {"Fn::Sub": artifact_bucket_name},  # "s3://${ArtifactBucketName}/"
                            {"Fn::FindInMap": ["Glue", "Script", "Filename"]},
                        ],
                    ]
                },
            },
            "Role": {"Fn::GetAtt": role_arn},
            "DefaultArguments": {
                "--job-bookmark-option": "job-bookmark-enable",
                "--job-language": "python",
                "--extra-py-files": "s3://aws-data-wrangler-public-artifacts/releases/2.14.0/awswrangler-2.14.0-py3-none-any.whl",
                "--additional-python-modules": "awswrangler==2.14.0",
                "--source_bucket": {"Fn::Sub": Match.any_value()},  # "${DataBucketName}"
                "--output_bucket": {"Fn::Sub": Match.any_value()},  # "${ArtifactBucketName}"
                "--source_key": "",
                "--pii_fields": "",
            },
            "Description": Match.any_value(),
            "ExecutionProperty": {"MaxConcurrentRuns": 2},
            "GlueVersion": "3.0",
            "MaxRetries": 0,
            "Name": {"Fn::Sub": Match.any_value()},  # "${AWS::StackName}-amc-transformation-job"
            "NumberOfWorkers": 2,
            "WorkerType": "Standard",
        },
    )

    # assert that the user role is correctly created
    assert template.to_json()["Resources"][role_arn.as_string().replace(".Arn", "")]["Type"] == "AWS::IAM::Role"
