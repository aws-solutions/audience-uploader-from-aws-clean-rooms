# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
import aws_cdk as cdk
from aws_cdk.assertions import Template, Capture, Match
from lib.uploader_stack import UploaderStack


# Create the stack in a fixture - pass the fixture to each test
@pytest.fixture(scope="module")
def template():
    FAKE_CONTEXT = {
        "SOLUTION_ID": "SO0226",
        "SOLUTION_VERSION": "v1.0.0",
        "BUCKET_NAME": "FAKEBUCKETNAME",
        "SOLUTION_NAME": "FAKESOLUTIONNAME",
        "APP_REGISTRY_NAME": "FAKEAPPREGISTRYNAME"
    }
    app = cdk.App(context=FAKE_CONTEXT)

    uploader_stack = UploaderStack(
        app,
        "uploader",
        stack_name=app.node.try_get_context("STACK_NAME"),
        description=f"Audience Uploader from AWS Clean Rooms Solution CDK stack",
        template_filename="uploader.template",
    )
    tiktok_uploader = uploader_stack.tiktok_stack

    synth_nested_template = Template.from_stack(tiktok_uploader)
    yield synth_nested_template


def test_kms_key_creation(template):
    template.resource_count_is("AWS::KMS::Key", 1)

    template.has_resource(
        "AWS::KMS::Key",
        {
            "Properties": {
                "KeyPolicy": {
                    "Statement": [
                        {
                            "Action": "kms:*",
                            "Effect": "Allow",
                            "Principal": {
                                "AWS": {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:",
                                            {
                                                "Ref": "AWS::Partition"
                                            },
                                            ":iam::",
                                            {
                                                "Ref": "AWS::AccountId"
                                            },
                                            ":root"
                                        ]
                                    ]
                                }
                            },
                            "Resource": "*"
                        }
                    ]
                },
                "EnableKeyRotation": True
            },
            "UpdateReplacePolicy": "Retain",
            "DeletionPolicy": "Retain"
        },
    )


def test_custom_data_creation(template):
    template.resource_count_is("Custom::AnonymousData", 1)

    template.has_resource_properties(
        "Custom::AnonymousData",
        {
            "ServiceToken": {
                "Fn::GetAtt": [
                    Match.any_value(),
                    "Arn"
                ]
            },
            "Solution": "FAKESOLUTIONNAME",
            "Region": {
                "Ref": "AWS::Region"
            }
        }
    )


def test_sqs_lambda_creation(template):
    key_name = Capture()

    template.resource_count_is("AWS::SQS::Queue", 1)
    template.has_resource_properties(
        "AWS::SQS::Queue",
        {
            "KmsMasterKeyId": {
                "Fn::GetAtt": [
                    key_name,
                    "Arn"
                ]
            }
        },
    )

    s3_bucket_name = Capture()
    s3_key = Capture()

    template.resource_count_is("AWS::Lambda::LayerVersion", 1)
    template.has_resource_properties(
        "AWS::Lambda::LayerVersion",
        {
            "Content": {
                "S3Bucket": {
                    "Fn::Sub": s3_bucket_name
                },
                "S3Key": s3_key

            }
        },
    )
    assert s3_key.as_string().endswith(".zip")

    sqs_lambda_name = Capture()
    sqs_queue_name = Capture()

    template.resource_count_is("AWS::Lambda::EventInvokeConfig", 1)
    template.has_resource_properties(
        "AWS::Lambda::EventInvokeConfig",
        {
            "FunctionName": {
                "Ref": sqs_lambda_name
            },
            "Qualifier": "$LATEST",
            "DestinationConfig": {
                "OnFailure": {
                    "Destination": {
                        "Fn::GetAtt": [
                            sqs_queue_name,
                            "Arn"
                        ]
                    }
                }
            }
        }
    )

    template.resource_count_is("AWS::Lambda::EventSourceMapping", 1)
    template.has_resource_properties(
        "AWS::Lambda::EventSourceMapping",
        {
            "FunctionName": {
                "Ref": sqs_lambda_name.as_string()
            },
            "BatchSize": 1,
            "EventSourceArn": {
                "Ref": "SQSArn"
            }
        },
    )

    sqs_role_policy_name = Capture()
    sqs_role_name = Capture()

    template.resource_count_is("AWS::IAM::Policy", 1)
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
                                sqs_queue_name.as_string(),
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
                                key_name.as_string(),
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
                        "Resource": Match.any_value()
                    },
                    {
                        "Action": [
                            "secretsmanager:PutSecretValue",
                            "secretsmanager:UpdateSecret"
                        ],
                        "Effect": "Allow",
                        "Resource": Match.any_value()
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
            "PolicyName": sqs_role_policy_name,
            "Roles": [
                {
                    "Ref": sqs_role_name
                }
            ]
        },
    )

    template.resource_count_is("AWS::IAM::Role", 2)
    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "AssumeRolePolicyDocument": {
                "Statement": [
                    {
                        "Action": "sts:AssumeRole",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "lambda.amazonaws.com"
                        }
                    }
                ]
            },
            "ManagedPolicyArns": [
                {
                    "Fn::Join": [
                        "",
                        [
                            "arn:",
                            {
                                "Ref": "AWS::Partition"
                            },
                            ":iam::aws:policy/CloudWatchLambdaInsightsExecutionRolePolicy"
                        ]
                    ]
                }
            ],
            "Policies": [
                {
                    "PolicyDocument": {
                        "Statement": [
                            {
                                "Action": [
                                    "logs:CreateLogGroup",
                                    "logs:CreateLogStream",
                                    "logs:PutLogEvents"
                                ],
                                "Effect": "Allow",
                                "Resource": {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:",
                                            {
                                                "Ref": "AWS::Partition"
                                            },
                                            ":logs:",
                                            {
                                                "Ref": "AWS::Region"
                                            },
                                            ":",
                                            {
                                                "Ref": "AWS::AccountId"
                                            },
                                            ":log-group:/aws/lambda/*"
                                        ]
                                    ]
                                }
                            }
                        ]
                    }
                }
            ]
        },
    )

    template.resource_count_is("AWS::Lambda::Function", 2)
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Code": {
                "S3Bucket": {
                    "Fn::Sub": s3_bucket_name.as_string()
                }
            },
            "Role": {
                "Fn::GetAtt": [
                    sqs_role_name.as_string(),
                    "Arn"
                ]
            },
            "Environment": {
                "Variables": {
                    "CRED_SECRET_NAME": Match.any_value()
                }
            },
            "Handler": "lambda_handler.lambda_handler",
            "MemorySize": 256,
            "Runtime": "python3.9",
            "Timeout": 900,
            "TracingConfig": {
                "Mode": "Active"
            }
        }
    )

    template.has_resource(
        "AWS::Lambda::Function",
        {
            "DependsOn": [
                sqs_role_policy_name.as_string(),
                sqs_role_name.as_string()
            ]
        }
    )


def test_metrics_lambda_creation(template):
    s3_bucket_name = Capture()
    s3_key = Capture()

    template.resource_count_is("AWS::Lambda::LayerVersion", 1)
    template.has_resource_properties(
        "AWS::Lambda::LayerVersion",
        {
            "Content": {
                "S3Bucket": {
                    "Fn::Sub": s3_bucket_name
                },
                "S3Key": s3_key

            }
        },
    )
    assert s3_key.as_string().endswith(".zip")

    template.resource_count_is("AWS::IAM::Role", 2)
    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "AssumeRolePolicyDocument": {
                "Statement": [
                    {
                        "Action": "sts:AssumeRole",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "lambda.amazonaws.com"
                        }
                    }
                ]
            },
            "ManagedPolicyArns": Match.absent(),
            "Policies": [
                {
                    "PolicyDocument": {
                        "Statement": [
                            {
                                "Action": [
                                    "logs:CreateLogGroup",
                                    "logs:CreateLogStream",
                                    "logs:PutLogEvents"
                                ],
                                "Effect": "Allow",
                                "Resource": {
                                    "Fn::Join": [
                                        "",
                                        [
                                            "arn:",
                                            {
                                                "Ref": "AWS::Partition"
                                            },
                                            ":logs:",
                                            {
                                                "Ref": "AWS::Region"
                                            },
                                            ":",
                                            {
                                                "Ref": "AWS::AccountId"
                                            },
                                            ":log-group:/aws/lambda/*"
                                        ]
                                    ]
                                }
                            }
                        ]
                    }
                }
            ]
        },
    )

    metrics_role_name = Capture()

    template.resource_count_is("AWS::Lambda::Function", 2)
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Code": {
                "S3Bucket": {
                    "Fn::Sub": s3_bucket_name.as_string()
                }
            },
            "Role": {
                "Fn::GetAtt": [
                    metrics_role_name,
                    "Arn"
                ]
            },
            "Handler": "metrics.handler",
            "Runtime": "python3.7",
        }
    )

    template.has_resource(
        "AWS::Lambda::Function",
        {
            "DependsOn": [
                metrics_role_name.as_string()
            ]
        }
    )
    assert metrics_role_name.as_string().startswith("MetricsMetricsFunctionRole")
