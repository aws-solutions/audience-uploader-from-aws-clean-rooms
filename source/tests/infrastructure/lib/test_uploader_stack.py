# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
import aws_cdk as cdk
from aws_cdk.assertions import Template, Capture, Match
from lib.uploader_stack import UploaderStack

construct_id = "TestUploaderStack"

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
    template = Template.from_stack(uploader_stack)
    yield template

# assert KMS Key creation - we'll check that it's used later in these tests
def test_kms_key_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::KMS::Key", 1)

    template.has_resource_properties(
        "AWS::KMS::Key",
        {
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
                    },
                    {
                        "Action": [
                            "kms:Decrypt",
                            "kms:Encrypt",
                            "kms:ReEncrypt*",
                            "kms:GenerateDataKey*"
                        ],
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "events.amazonaws.com"
                        },
                        "Resource": "*"
                    }
                ],
                "Version": "2012-10-17"
            }
        }
    )

# assert queue creation
def test_sqs_queue_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::SQS::Queue", 1)

    kms_key_id = Capture()
    template.has_resource_properties(
        "AWS::SQS::Queue",
        {
            "KmsDataKeyReusePeriodSeconds": 86400,
            "KmsMasterKeyId": {
                "Fn::GetAtt": [
                    kms_key_id,
                    "Arn"
                ]
            },
            "VisibilityTimeout": 5400
        }
    )

    # make sure the key was created with the correct name
    assert (
        template.to_json()["Resources"][kms_key_id.as_string()]["Type"]
        == "AWS::KMS::Key"
    )

    # make sure the key is only used in the queue that we're checking
    assert ( template.to_json()["Resources"][kms_key_id.as_string()].count == 1)

# assert queue policy creation
def test_sqs_queue_policy_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::SQS::QueuePolicy", 1)

    event_bridge_queue_name = Capture()
    template.has_resource_properties(
        "AWS::SQS::QueuePolicy",
        {
            "PolicyDocument": {
                "Statement": [
                    {
                        "Action": [
                            "sqs:SendMessage",
                            "sqs:GetQueueAttributes",
                            "sqs:GetQueueUrl"
                        ],
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "events.amazonaws.com"
                        },
                        "Resource": {
                            "Fn::GetAtt": [
                                event_bridge_queue_name,
                                "Arn"
                            ]
                        }
                    }
                ],
                "Version": "2012-10-17"
            },
            "Queues": [
                {
                    "Ref": event_bridge_queue_name
                }
            ]
        }
    )

    # make sure the queue policy was associated with the correct queue
    assert (
        template.to_json()["Resources"][event_bridge_queue_name.as_string()]["Type"]
        == "AWS::SQS::Queue"
    )

# assert event rule creation
def test_event_rule_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::Events::Rule", 1)

    event_bridge_name = Capture()

    template.has_resource_properties(
        "AWS::Events::Rule",
        {
            "EventPattern": {
                "account": [
                    {
                        "Ref": "AWS::AccountId"
                    }
                ],
                "detail": {
                    "bucket": {
                        "name": [
                            {
                                "prefix": "uploader-etl-artifacts"
                            }
                        ]
                    }
                },
                "detail-type": [
                    "Object Created"
                ],
                "region": [
                    {
                        "Ref": "AWS::Region"
                    }
                ],
                "source": [
                    "aws.s3"
                ]
            },
            "State": "ENABLED",
            "Targets": [
                {
                    "Arn": {
                        "Fn::GetAtt": [
                            event_bridge_name,
                            "Arn"
                        ]
                    },
                    "Id": {
                        "Fn::GetAtt": [
                            event_bridge_name,
                            "QueueName"
                        ]
                    }
                }
            ]
        }
    )

    # make sure the queue rule was associated with the correct queue
    assert (
        template.to_json()["Resources"][event_bridge_name.as_string()]["Type"]
        == "AWS::SQS::Queue"
    )

# assert bucket creation
def test_s3_buckets_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::S3::Bucket", 2)

    # Check public access and ecryption settings
    template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "AccessControl": "LogDeliveryWrite",
            "BucketEncryption": {
                "ServerSideEncryptionConfiguration": [
                    {
                        "ServerSideEncryptionByDefault": {
                            "SSEAlgorithm": "AES256"
                        }
                    }
                ]
            },
            "PublicAccessBlockConfiguration": {
                "BlockPublicAcls": True,
                "BlockPublicPolicy": True,
                "IgnorePublicAcls": True,
                "RestrictPublicBuckets": True
            },
        }
    )

    # Check lifecycle and expiration rules
    template.has_resource_properties(
        "AWS::S3::Bucket",
        {
            "LifecycleConfiguration": {
                "Rules": [
                    {
                        "AbortIncompleteMultipartUpload": {
                            "DaysAfterInitiation": 1
                        },
                        "ExpirationInDays": 3,
                        "Id": Match.any_value(),
                        "Prefix": "access_logs/",
                        "Status": "Enabled"
                    }
                ]
            },
        }
    )

# assert lambda permissions creation
def test_lambda_permissions_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::Lambda::Permission", 1)

    lambda_arn = Capture()
    template.has_resource_properties(
        "AWS::Lambda::Permission",
        {
            "Action": "lambda:InvokeFunction",
            "FunctionName": {
                "Fn::GetAtt": lambda_arn
            },
        }
    )

    # make sure the key was created with the correct name
    assert (
        template.to_json()["Resources"][lambda_arn.as_string().replace(".Arn", "")]["Type"]
        == "AWS::Lambda::Function"
    )

    # make sure the key is only used in the queue that we're checking
    #assert ( template.to_json()["Resources"][lambda_arn.as_string().repl].count == 1)


# assert six stack creation - they each have their own test files
def test_sqs_queue_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::CloudFormation::Stack", 6)
    # Glue, Web, Auth, API, Tiktok, and Snap

#   "GlueStack": {
#    "Type": "AWS::CloudFormation::Stack",

#   "ApiStack": {
#    "Type": "AWS::CloudFormation::Stack",

#   "AuthStack": {
#    "Type": "AWS::CloudFormation::Stack",

#   "WebStack": {
#    "Type": "AWS::CloudFormation::Stack",

#   "SnapUploaderStackNestedStackSnapUploaderStackNestedStackResourceF9D8CDAD": {
#    "Type": "AWS::CloudFormation::Stack",

#   "TiktokUploaderStackNestedStackTiktokUploaderStackNestedStackResourceA2B0C72E": {
#    "Type": "AWS::CloudFormation::Stack",

# assert iam role creation
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
                        "Principal": {
                            "Service": [
                                "lambda.amazonaws.com"
                            ]
                        },
                        "Action": [
                            "sts:AssumeRole"
                        ]
                    }
                ]
            },
            "Path": "/",
            "Policies": [
                {
                    "PolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": [
                                    "logs:CreateLogGroup",
                                    "logs:CreateLogStream",
                                    "logs:PutLogEvents"
                                ],
                                "Resource": [
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:aws:logs:",
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
                                ]
                            },
                            {
                                "Effect": "Allow",
                                "Action": [
                                    "s3:DeleteObject"
                                ],
                                "Resource": [
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:aws:s3:::",
                                                {
                                                    "Ref": "ArtifactLogsBucket"
                                                },
                                                "/*"
                                            ]
                                        ]
                                    }
                                ]
                            },
                            {
                                "Effect": "Allow",
                                "Action": [
                                    "s3:ListBucket"
                                ],
                                "Resource": [
                                    {
                                        "Fn::Join": [
                                            "",
                                            [
                                                "arn:aws:s3:::",
                                                {
                                                    "Ref": "ArtifactLogsBucket"
                                                }
                                            ]
                                        ]
                                    }
                                ]
                            }
                        ]
                    },
                    "PolicyName": "root"
                }
            ],
        }
    )

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
                ],
                "Version": "2012-10-17"
            },
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
                        ],
                        "Version": "2012-10-17"
                    },
                    "PolicyName": "LambdaFunctionServiceRolePolicy"
                }
            ]
         }
    )


# assert lambdas creation
def test_lambda_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::Lambda::Function", 2)

    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Role": {
                "Fn::GetAtt": Match.any_value()
            },
            "Handler": "index.handler",
            "Runtime": "python3.9",
        }
    )

    metrics_role = Capture()
    template.has_resource_properties(
        "AWS::Lambda::Function",
        {

            "Role": {
                "Fn::GetAtt": [
                    metrics_role,
                    "Arn"
                ]
            },
            "Handler": "metrics.handler",
            "Runtime": "python3.7"
        }
    )

    # make sure the key was created with the correct name
    assert (
        template.to_json()["Resources"][metrics_role.as_string()]["Type"]
        == "AWS::IAM::Role"
    )
