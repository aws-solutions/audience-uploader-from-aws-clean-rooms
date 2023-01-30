# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
from aws_cdk.assertions import Template, Match, Capture
import aws_cdk as cdk
from lib.uploader_stack import UploaderStack

# Create the stack in a fixture - pass the fixture to each test
@pytest.fixture(scope="module")
def synth_nested_template():

    FAKE_CONTEXT = {
        "SOLUTION_ID": "SO0226",
        "SOLUTION_VERSION": "V1.0.0",
        "BUCKET_NAME": "FAKEBUCKETNAME",
        "SOLUTION_NAME": "FAKESOLUTIONNAME",
        "APP_REGISTRY_NAME": "FAKEAPPREGISTRYNAME",
    }
    app = cdk.App(context=FAKE_CONTEXT)

    uploader_stack = UploaderStack(
        app,
        "uploader",
        stack_name=app.node.try_get_context("STACK_NAME"),
        description=f"Audience Uploader from AWS Clean Rooms Solution CDK stack",
        template_filename="audience-uploader-from-aws-clean-rooms.template",
    )
    web_stack = uploader_stack.cf_stack.get_nested_stack("WebStack")

    template = Template.from_stack(web_stack.stack)
    yield template


def test_lambda_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::Lambda::Function", 2)

    bucket_execution_role = Capture()
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Role": {"Fn::GetAtt": bucket_execution_role},
            "Handler": "index.handler",
            "Runtime": Match.string_like_regexp("python3.*"),
        },
    )

    # make sure the role was created with the correct name
    assert (
        template.to_json()["Resources"][bucket_execution_role.as_string().replace(".Arn", "")]["Type"]
        == "AWS::IAM::Role"
    )


def test_s3_bucket_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::S3::Bucket", 1)

    template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "AccessControl": "LogDeliveryWrite",
            "BucketEncryption": {
                "ServerSideEncryptionConfiguration": [{"ServerSideEncryptionByDefault": {"SSEAlgorithm": "AES256"}}]
            },
            "BucketName": {"Fn::GetAtt": Match.any_value()},
            "LifecycleConfiguration": {
                "Rules": [
                    {
                        "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1},
                        "ExpirationInDays": 3,
                        "Id": Match.any_value(),
                        "Prefix": "access_logs/",
                        "Status": "Enabled",
                    },
                    {
                        "AbortIncompleteMultipartUpload": {"DaysAfterInitiation": 1},
                        "ExpirationInDays": 3,
                        "Id": Match.any_value(),
                        "Prefix": "cf_logs/",
                        "Status": "Enabled",
                    },
                ]
            },
        },
    )


# Policy to deny all and then one to allow GetObject


def test_bucket_policy_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::S3::BucketPolicy", 1)

    website_bucket = Capture()
    # least privilege
    template.has_resource_properties(
        "AWS::S3::BucketPolicy",
        {
            "Bucket": {"Ref": website_bucket},
            "PolicyDocument": {
                "Statement": [
                    {
                        "Effect": "Allow",
                        "Action": ["s3:GetObject"],
                        "Resource": [{"Fn::Sub": website_bucket}],
                    },
                    {
                        "Effect": "Deny",
                        "Principal": "*",
                        "Action": "*",
                        "Resource": [{"Fn::Sub": website_bucket}, {"Fn::Sub": website_bucket}],
                        "Condition": {"Bool": {"aws:SecureTransport": False}},
                    },
                ]
            },
        },
    )


def test_lambda_permissions_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::Lambda::Permission", 1)

    website_bucket_function = Capture()
    template.has_resource_properties(
        "AWS::Lambda::Permission",
        {
            "Action": "lambda:InvokeFunction",
            "FunctionName": {"Fn::GetAtt": website_bucket_function},
            "Principal": "cloudformation.amazonaws.com",
        },
    )

    # make sure the function was created with the correct name
    assert (
        template.to_json()["Resources"][website_bucket_function.as_string().replace(".Arn", "")]["Type"]
        == "AWS::Lambda::Function"
    )
