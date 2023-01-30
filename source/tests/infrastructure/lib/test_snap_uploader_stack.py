# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
import aws_cdk as cdk
from aws_cdk.assertions import Template, Capture, Match
from lib.uploader_stack import UploaderStack

construct_id = "TestSnapNestedStack"

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
    snap_uploader = uploader_stack.snap_stack

    template = Template.from_stack(snap_uploader)
    yield template

# Segment Uploader code test
def test_nested_stack_lambda_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::Lambda::Function", 2)

    snap_uploader_segment_role = Capture()
    solutions_layer = Capture()

    # users to segment - the other one is MetricsFunction
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Role": {
                "Fn::GetAtt": [
                    snap_uploader_segment_role,
                    "Arn"
                ]
            },
            "Description": "activate users to segment",
            "Environment": {
                "Variables": {
                    "REFRESH_SECRET_NAME": Match.any_value(),
                    "CRED_SECRET_NAME": Match.any_value(),
                    "SOLUTION_ID": Match.any_value(),
                    "SOLUTION_VERSION": Match.any_value()
                }
            },
            "Handler": "lambda_handler.lambda_handler",
            "Layers": [
                {
                    "Fn::Join": [
                        "",
                        [
                            "arn:aws:lambda:",
                            {
                                "Ref": "AWS::Region"
                            },
                            Match.any_value()
                        ]
                    ]
                },
                {
                    "Ref": solutions_layer
                },
                {
                    "Fn::Join": [
                        "",
                        [
                            "arn:aws:lambda:",
                            {
                                "Ref": "AWS::Region"
                            },
                            Match.any_value()
                        ]
                    ]
                }
            ],
            "MemorySize": 256,
            "Runtime": "python3.9",
            "Timeout": 900,
            "TracingConfig": {
                "Mode": "Active"
            }
        }
    )

    # make sure the role was created with the correct name
    assert (
        template.to_json()["Resources"][snap_uploader_segment_role.as_string()]["Type"]
        == "AWS::IAM::Role"
    )

    # make sure the layer was created with the correct name
    assert (
        template.to_json()["Resources"][solutions_layer.as_string()]["Type"]
        == "AWS::Lambda::LayerVersion"
    )

# make sure the dlq is created
def test_resource_sqs_queue(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::SQS::Queue", 1)  # dead letter queue

    kms_key_id = Capture()

    # Policy for the queue decrypt
    template.has_resource_properties(
        "AWS::SQS::Queue",
        {
            "KmsMasterKeyId": {
                "Fn::GetAtt": [
                    kms_key_id,
                    "Arn"
                ]
            },
        }
    )

    # make sure the kms key was created with the correct name
    assert (
        template.to_json()["Resources"][kms_key_id.as_string()]["Type"]
        == "AWS::KMS::Key"
    )

# make sure the IAM policy is created properly
# this policy is to decrypt the queue messages
# make sure that the policy only shows up once
def test_iam_policy_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::IAM::Policy", 1)

    key_id = Capture()
    dlq_id = Capture()
    role_id = Capture()

    # Policy for the queue decrypt
    template.has_resource_properties(
        "AWS::IAM::Policy",
        {
            "PolicyDocument": {
                "Statement": [
                    {
                        "Action": [
                            "xray:PutTraceSegments",
                            "xray:PutTelemetryRecords"
                        ],
                        "Effect": "Allow",
                        "Resource": "*"
                    },
                    {
                        "Action": [
                            "sqs:SendMessage",
                            "sqs:GetQueueAttributes",
                            "sqs:GetQueueUrl"
                        ],
                        "Effect": "Allow",
                        "Resource": {
                            "Fn::GetAtt": [
                                dlq_id,
                                "Arn"
                            ]
                        }
                    },
                    {
                        "Action": [
                            "kms:Decrypt",
                            "kms:Encrypt",
                            "kms:ReEncrypt*",
                            "kms:GenerateDataKey*"
                        ],
                        "Effect": "Allow",
                        "Resource": {
                            "Fn::GetAtt": [
                                key_id,
                                "Arn"
                            ]
                        }
                    },
                    {
                        "Action": [
                            "S3:ListBucket",
                            "S3:GetObjectTagging",
                            "S3:GetObject",
                            "S3:PutBucketNotification"
                        ],
                        "Effect": "Allow",
                        "Resource": "arn:aws:s3:::uploader-etl-artifacts*"
                    },
                    {
                        "Action": "kms:Decrypt",
                        "Effect": "Allow",
                        "Resource": "*"
                    },
                    {
                        "Action": [
                            "secretsmanager:GetSecretValue",
                            "secretsmanager:DescribeSecret"
                        ],
                        "Effect": "Allow",
                        "Resource":
                                {
                                "Ref": Match.any_value()
                                }
                    },
                    {
                        "Action": [
                            "secretsmanager:GetSecretValue",
                            "secretsmanager:DescribeSecret"
                        ],
                        "Effect": "Allow",
                        "Resource":
                                {
                                "Ref": Match.any_value()
                                }
                    },
                    {
                        "Action": [
                            "secretsmanager:PutSecretValue",
                            "secretsmanager:UpdateSecret"
                        ],
                        "Effect": "Allow",
                        "Resource": {
                            "Ref": Match.any_value()
                        }
                    },
                    {
                        "Action": [
                            "sqs:ReceiveMessage",
                            "sqs:ChangeMessageVisibility",
                            "sqs:GetQueueUrl",
                            "sqs:DeleteMessage",
                            "sqs:GetQueueAttributes"
                        ],
                        "Effect": "Allow",
                        "Resource": {
                            "Ref": "SQSArn"
                        }
                    }
                ],
                "Version": "2012-10-17"
            },
            "PolicyName": Match.any_value() , # "snapuploadersegmentRoleDefaultPolicy1A530ACE",
            "Roles": [
                {
                    "Ref": role_id
                }
            ]
            
        }
    )

    # make sure the key was created with the correct name
    assert (
        template.to_json()["Resources"][key_id.as_string()]["Type"]
        == "AWS::KMS::Key"
    )

    # make sure the dead letter queue was created with the correct name
    assert (
        template.to_json()["Resources"][dlq_id.as_string()]["Type"]
        == "AWS::SQS::Queue"
    )

    # make sure the role was created with the correct name
    assert (
        template.to_json()["Resources"][role_id.as_string()]["Type"]
        == "AWS::IAM::Role"
    )
# assert invoke config creation
def test_lambda_event_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::Lambda::EventInvokeConfig", 1)

    dlq_id = Capture()
    lambda_function_name = Capture()

    template.has_resource_properties(
        "AWS::Lambda::EventInvokeConfig",
        {
            "FunctionName": {
                "Ref": lambda_function_name
            },
            "Qualifier": "$LATEST",
            "DestinationConfig": {
                "OnFailure": {
                    "Destination": {
                        "Fn::GetAtt": [
                            dlq_id, 
                            "Arn"
                        ]
                    }
                }
            }
        }
    )

    # make sure the dead letter queue was created with the correct name
    assert (
        template.to_json()["Resources"][dlq_id.as_string()]["Type"]
        == "AWS::SQS::Queue"
    )

    # make sure the lambda function was created with the correct name
    assert (
        template.to_json()["Resources"][lambda_function_name.as_string()]["Type"]
        == "AWS::Lambda::Function"
    )

# # assert the source mapping
def test_lambda_event_source_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::Lambda::EventSourceMapping", 1)

    snap_uploader_segment = Capture()
    template.has_resource_properties(
        "AWS::Lambda::EventSourceMapping",
        {
            "FunctionName": {
                "Ref": snap_uploader_segment 
            },
            "BatchSize": 1,
            "EventSourceArn": {
                "Ref": "SQSArn"
            }
        }
     )

    # make sure the lambda function was created with the correct name
    assert (
        template.to_json()["Resources"][snap_uploader_segment.as_string()]["Type"]
        == "AWS::Lambda::Function"
    )
