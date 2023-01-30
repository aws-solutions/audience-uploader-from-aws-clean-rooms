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
        "SOLUTION_VERSION": "v1.0.0",
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
    auth_stack = uploader_stack.cf_stack.get_nested_stack("AuthStack")

    template = Template.from_stack(auth_stack.stack)
    yield template


def test_cognito_userpool_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::Cognito::UserPool", 1)

    template.has_resource_properties(
        "AWS::Cognito::UserPool",
        {
            "AdminCreateUserConfig": {
                "AllowAdminCreateUserOnly": True,
                "InviteMessageTemplate": {
                    "EmailMessage": {"Fn::Join": ["", [Match.any_value()]]},
                    "EmailSubject": Match.any_value(),
                },
            }
        },
    )


def test_cognito_userpoolclient_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::Cognito::UserPoolClient", 1)

    # get the user pool ID to cross reference
    user_pool_id = Capture()
    template.has_resource_properties("AWS::Cognito::UserPoolClient", {"UserPoolId": {"Ref": user_pool_id}})

    # assert that the pool id is used correctly in the pool group
    template.has_resource_properties(
        "AWS::Cognito::UserPoolGroup",
        {
            "UserPoolId": {"Ref": user_pool_id.as_string()},
        },
    )


def test_cognito_userpooluser_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::Cognito::UserPoolUser", 1)

    # get the user pool ID to cross reference
    user_pool_id = Capture()
    user_name = Capture()
    group_name = Capture()

    template.has_resource_properties(
        "AWS::Cognito::UserPoolUser",
        {
            "UserPoolId": {"Ref": user_pool_id},
            "DesiredDeliveryMediums": ["EMAIL"],
            "UserAttributes": [{"Name": "email", "Value": {"Ref": Match.any_value()}}],
            "Username": {"Ref": user_name},
        },
    )

    # assert that the pool id is used correctly in the pool group
    template.has_resource_properties(
        "AWS::Cognito::UserPoolGroup",
        {
            "UserPoolId": {"Ref": user_pool_id.as_string()},
        },
    )

    # get the group name
    template.has_resource_properties(
        "AWS::Cognito::UserPoolUserToGroupAttachment",
        {
            "GroupName": {"Ref": group_name},
            "Username": {"Ref": user_name.as_string()},
            "UserPoolId": {"Ref": user_pool_id.as_string()},
        },
    )

    # assert that the user pool is correctly created
    assert template.to_json()["Resources"][group_name.as_string()]["Type"] == "AWS::Cognito::UserPoolGroup"

    # assert that the user pool is correctly created
    assert template.to_json()["Resources"][user_pool_id.as_string()]["Type"] == "AWS::Cognito::UserPool"


def test_cognito_userpoolgroup_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::Cognito::UserPoolGroup", 1)

    user_pool_id = Capture()
    user_role_arn = Capture()

    template.has_resource_properties(
        "AWS::Cognito::UserPoolGroup",
        {
            "UserPoolId": {"Ref": user_pool_id},
            "Description": Match.any_value(),
            "GroupName": {"Fn::Sub": Match.any_value()},
            "RoleArn": {"Fn::GetAtt": user_role_arn},
        },
    )

    # assert that the user pool is correctly created
    assert template.to_json()["Resources"][user_pool_id.as_string()]["Type"] == "AWS::Cognito::UserPool"

    # assert that the user pool is correctly created
    assert template.to_json()["Resources"][user_role_arn.as_string().replace(".Arn", "")]["Type"] == "AWS::IAM::Role"


def test_cognito_userpoolusertogroupattachment_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::Cognito::UserPoolUserToGroupAttachment", 1)

    role_arn = Capture()
    user_pool_id = Capture()

    template.has_resource_properties(
        "AWS::Cognito::UserPoolGroup",
        {
            "UserPoolId": {"Ref": user_pool_id},
            "Description": Match.any_value(),
            "GroupName": {"Fn::Sub": Match.any_value()},
            "RoleArn": {"Fn::GetAtt": role_arn},
        },
    )

    # assert that the user pool is correctly created
    assert template.to_json()["Resources"][user_pool_id.as_string()]["Type"] == "AWS::Cognito::UserPool"

    # assert that the user role is correctly created
    assert template.to_json()["Resources"][role_arn.as_string().replace(".Arn", "")]["Type"] == "AWS::IAM::Role"


def test_cognito_identitypool_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::Cognito::IdentityPool", 1)

    client_id = Capture()
    provider_name = Capture()
    template.has_resource_properties(
        "AWS::Cognito::IdentityPool",
        {
            "AllowUnauthenticatedIdentities": False,
            "CognitoIdentityProviders": [
                {"ClientId": {"Ref": client_id}, "ProviderName": {"Fn::GetAtt": provider_name}}
            ],
        },
    )
    # assert that the user pool client is correctly created
    assert template.to_json()["Resources"][client_id.as_string()]["Type"] == "AWS::Cognito::UserPoolClient"

    # assert that the provider is correctly created
    assert (
        template.to_json()["Resources"][provider_name.as_string().replace(".ProviderName", "")]["Type"]
        == "AWS::Cognito::UserPool"
    )


def test_cognito_identitypoolroleattachment_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::Cognito::IdentityPoolRoleAttachment", 1)

    identity_pool_id = Capture()
    user_pool_id = Capture()
    web_app_client = Capture()

    template.has_resource_properties(
        "AWS::Cognito::IdentityPoolRoleAttachment",
        {
            "IdentityPoolId": {"Ref": identity_pool_id},
            "RoleMappings": {
                "TransformedRoleMapping": {
                    "AmbiguousRoleResolution": "Deny",
                    "IdentityProvider": {
                        "Fn::Join": [":", [{"Fn::GetAtt": [user_pool_id, "ProviderName"]}, {"Ref": web_app_client}]]
                    },
                    "Type": "Token",
                }
            },
            "Roles": {
                "authenticated": {"Fn::GetAtt": "CognitoStandardAuthDefaultRole.Arn"},
                "unauthenticated": {"Fn::GetAtt": "CognitoStandardUnauthDefaultRole.Arn"},
            },
        },
    )

    # assert that the identity pool is correctly created
    assert template.to_json()["Resources"][identity_pool_id.as_string()]["Type"] == "AWS::Cognito::IdentityPool"

    # assert that the user pool client is correctly created
    assert template.to_json()["Resources"][user_pool_id.as_string()]["Type"] == "AWS::Cognito::UserPool"

    # assert that the user pool client is correctly created
    assert template.to_json()["Resources"][web_app_client.as_string()]["Type"] == "AWS::Cognito::UserPoolClient"


def test_iam_role_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::IAM::Role", 4)

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
            },
            "Path": "/",
            "Policies": [
                {
                    "PolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": ["logs:CreateLogGroup", "logs:CreateLogStream", "logs:PutLogEvents"],
                                "Resource": "arn:aws:logs:*:*:*",
                            }
                        ],
                    },
                    "PolicyName": "root",
                }
            ],
        },
    )


def test_lambda_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::Lambda::Function", 1)

    lambda_execution_role = Capture()

    template.has_resource_properties(
        "AWS::Lambda::Function",
        {
            "Code": Match.object_like({"ZipFile": Match.any_value()}),
            "Role": {"Fn::GetAtt": lambda_execution_role},
            "Handler": {"Fn::Join": ["", ["index", ".handler"]]},
            "Runtime": Match.string_like_regexp("python3.*"),
            "Timeout": 30,
        },
    )

    # assert that the provider is correctly created
    assert (
        template.to_json()["Resources"][lambda_execution_role.as_string().replace(".Arn", "")]["Type"]
        == "AWS::IAM::Role"
    )
