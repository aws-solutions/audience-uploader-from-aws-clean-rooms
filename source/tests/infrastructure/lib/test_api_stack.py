# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import pytest
import aws_cdk as cdk
from aws_cdk.assertions import Template, Capture, Match
from lib.uploader_stack import UploaderStack

construct_id = "TestApiNestedStack"

# Create the stack in a fixture - pass the fixture to each test
@pytest.fixture(scope="module")
def synth_nested_template():

    FAKE_CONTEXT = {
        "SOLUTION_ID": "SO0226",
        "SOLUTION_VERSION": "V1.0.0",
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
    # these next two lines of code will work once we get the JSON error fixed!
    # snap_uploader = uploader_stack.snap_stack
    # glue_stack = uploader_stack.cf_stack.get_nested_stack("GlueStack")
    # web_stack = uploader_stack.cf_stack.get_nested_stack("WebStack")
    api_stack = uploader_stack.cf_stack.get_nested_stack("ApiStack")

    template = Template.from_stack(api_stack.stack)
    yield template

# IAM Role creation
def test_iam_role_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::IAM::Role", 1)

    template.has_resource_properties(
        "AWS::IAM::Role",
        {
            "AssumeRolePolicyDocument": {
                "Version": "2012-10-17",
                "Statement": [
                    {
                        "Sid": "",
                        "Effect": "Allow",
                        "Principal": {
                            "Service": "lambda.amazonaws.com"
                        },
                        "Action": "sts:AssumeRole"
                    }
                ]
            },
            "Policies": [
                {
                    "PolicyDocument": {
                        "Version": "2012-10-17",
                        "Statement": [
                            {
                                "Effect": "Allow",
                                "Action": [
                                    "s3:GetObject"
                                ],
                                "Resource": {
                                    "Fn::Sub": Match.any_value()
                                }
                            },
                            {
                                "Effect": "Allow",
                                "Action": [
                                    "s3:ListBucket"
                                ],
                                "Resource": {
                                    "Fn::Sub": Match.any_value()
                                }
                            },
                            {
                                "Effect": "Allow",
                                "Action": [
                                    "glue:StartJobRun",
                                    "glue:GetJobRuns"
                                ],
                                "Resource": {
                                    "Fn::Sub": Match.any_value()
                                }
                            },
                            {
                                "Action": [
                                    "logs:CreateLogGroup",
                                    "logs:CreateLogStream",
                                    "logs:PutLogEvents"
                                ],
                                "Resource": {
                                    "Fn::Sub": Match.any_value()
                                },
                                "Effect": "Allow",
                                "Sid": "Logging"
                            },
                            {
                                "Action": [
                                    "xray:PutTraceSegments",
                                    "xray:PutTelemetryRecords"
                                ],
                                "Resource": [
                                    "*"
                                ],
                                "Effect": "Allow",
                            }
                        ]
                    },
                    "PolicyName": Match.any_value()
                }
            ]
        }    
    )

# Serverless Function
def test_serverless_function_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::Serverless::Function", 1)

    bucket = Capture()
    key_id = Capture()
    template.has_resource_properties(
        "AWS::Serverless::Function",
        {
            "CodeUri": {
                "Bucket": {
                    "Ref": bucket
                },
                "Key": {
                    "Ref": key_id
                }
            },
            "Environment": {
                "Variables": {
                    "botoConfig": {
                        "Ref": "botoConfig"
                    },
                    "VERSION": {
                        "Ref": "Version"
                    },
                    "AMC_ENDPOINT_URL": Match.any_value(),
                    "AMC_API_ROLE_ARN": Match.any_value(),
                    "AMC_GLUE_JOB_NAME": {
                        "Ref": Match.any_value()
                    }
                }
            },
            "Handler": "app.app",
            "Layers": [
                Match.any_value()
            ],
            "MemorySize": 2048,
            "Role": {
                "Fn::GetAtt": [
                    "ApiHandlerRole",
                    "Arn"
                ]
            },
            "Runtime": "python3.9",
            "Tags": Match.any_value(),
            "Timeout": 600,
            "Tracing": "Active"
        }
    )

    # ensure the bucket details match
    template.has_resource_properties(
        "AWS::Serverless::Function",
        {
            "CodeUri": {
                "Bucket": {
                    "Ref": bucket
                },
                "Key": {
                    "Ref": key_id
                }
            },
        }
    )

# Serverless Api
def test_serverless_api_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::Serverless::Api", 1)

    # TODO: Convert this to a snapshot - cleanup code
    template.has_resource_properties(
        "AWS::Serverless::Api",
        {

            "StageName": "api",
            "DefinitionBody": {
            "swagger": "2.0",
            "info": {
            "version": "1.0",
            "title": Match.any_value()
            },
            "schemes": [
            "https"
            ],
            "paths": {
            "/start_snap_transformation": {
            "post": {
                "consumes": [
                "application/json"
                ],
                "produces": [
                "application/json"
                ],
                "responses": {
                "200": {
                "description": "200 response",
                "schema": {
                "$ref": "#/definitions/Empty"
                }
                }
                },
                "x-amazon-apigateway-integration": {
                "responses": {
                "default": {
                "statusCode": "200"
                }
                },
                "uri": {
                "Fn::Sub": Match.any_value()
                },
                "passthroughBehavior": "when_no_match",
                "httpMethod": "POST",
                "contentHandling": "CONVERT_TO_TEXT",
                "type": "aws_proxy"
                },
                "summary": "Invoke Glue job to prepare data for uploading into Snap.",
                "security": [
                {
                "sigv4": []
                }
                ]
            },
            "options": {
                "consumes": [
                "application/json"
                ],
                "produces": [
                "application/json"
                ],
                "responses": {
                "200": {
                "description": "200 response",
                "schema": {
                "$ref": "#/definitions/Empty"
                },
                "headers": {
                "Access-Control-Allow-Methods": {
                    "type": "string"
                },
                "Access-Control-Allow-Origin": {
                    "type": "string"
                },
                "Access-Control-Allow-Headers": {
                    "type": "string"
                }
                }
                }
                },
                "x-amazon-apigateway-integration": {
                "responses": {
                "default": {
                "statusCode": "200",
                "responseParameters": {
                    "method.response.header.Access-Control-Allow-Methods": "'POST,OPTIONS'",
                    "method.response.header.Access-Control-Allow-Origin": "'*'",
                    "method.response.header.Access-Control-Allow-Headers": "'Authorization,Content-Type,X-Amz-Date,X-Amz-Security-Token,X-Api-Key'"
                }
                }
                },
                "requestTemplates": {
                "application/json": "{\"statusCode\": 200}"
                },
                "passthroughBehavior": "when_no_match",
                "type": "mock",
                "contentHandling": "CONVERT_TO_TEXT"
                }
            }
            },
            "/get_etl_jobs": {
            "get": {
                "consumes": [
                "application/json"
                ],
                "produces": [
                "application/json"
                ],
                "responses": {
                "200": {
                "description": "200 response",
                "schema": {
                "$ref": "#/definitions/Empty"
                }
                }
                },
                "x-amazon-apigateway-integration": {
                "responses": {
                "default": {
                "statusCode": "200"
                }
                },
                "uri": {
                "Fn::Sub": Match.any_value()
                },
                "passthroughBehavior": "when_no_match",
                "httpMethod": "POST",
                "contentHandling": "CONVERT_TO_TEXT",
                "type": "aws_proxy"
                },
                "summary": "Retrieves metadata for all runs of a given Glue ETL job definition.",
                "description": "Returns:\n\n.. code-block:: python\n\n    {'JobRuns': [...]}",
                "security": [
                {
                "sigv4": []
                }
                ]
            },
            "options": {
                "consumes": [
                "application/json"
                ],
                "produces": [
                "application/json"
                ],
                "responses": {
                "200": {
                "description": "200 response",
                "schema": {
                "$ref": "#/definitions/Empty"
                },
                "headers": {
                "Access-Control-Allow-Methods": {
                    "type": "string"
                },
                "Access-Control-Allow-Origin": {
                    "type": "string"
                },
                "Access-Control-Allow-Headers": {
                    "type": "string"
                }
                }
                }
                },
                "x-amazon-apigateway-integration": {
                "responses": {
                "default": {
                "statusCode": "200",
                "responseParameters": {
                    "method.response.header.Access-Control-Allow-Methods": "'GET,OPTIONS'",
                    "method.response.header.Access-Control-Allow-Origin": "'*'",
                    "method.response.header.Access-Control-Allow-Headers": "'Authorization,Content-Type,X-Amz-Date,X-Amz-Security-Token,X-Api-Key'"
                }
                }
                },
                "requestTemplates": {
                "application/json": "{\"statusCode\": 200}"
                },
                "passthroughBehavior": "when_no_match",
                "type": "mock",
                "contentHandling": "CONVERT_TO_TEXT"
                }
            }
            },
            "/version": {
            "get": {
                "consumes": [
                "application/json"
                ],
                "produces": [
                "application/json"
                ],
                "responses": {
                "200": {
                "description": "200 response",
                "schema": {
                "$ref": "#/definitions/Empty"
                }
                }
                },
                "x-amazon-apigateway-integration": {
                "responses": {
                "default": {
                "statusCode": "200"
                }
                },
                "uri": {
                "Fn::Sub": Match.any_value()
                },
                "passthroughBehavior": "when_no_match",
                "httpMethod": "POST",
                "contentHandling": "CONVERT_TO_TEXT",
                "type": "aws_proxy"
                },
                "summary": Match.any_value(), # "Get the solution version number.",
                "description": Match.any_value(), # "Returns:\n\n.. code-block:: python\n\n    {\"Version\": string}",
                "security": [
                {
                "sigv4": []
                }
                ]
            },
            "options": {
                "consumes": [
                "application/json"
                ],
                "produces": [
                "application/json"
                ],
                "responses": {
                "200": {
                "description": "200 response",
                "schema": {
                "$ref": "#/definitions/Empty"
                },
                "headers": {
                "Access-Control-Allow-Methods": {
                    "type": "string"
                },
                "Access-Control-Allow-Origin": {
                    "type": "string"
                },
                "Access-Control-Allow-Headers": {
                    "type": "string"
                }
                }
                }
                },
                "x-amazon-apigateway-integration": {
                "responses": {
                "default": {
                "statusCode": "200",
                "responseParameters": {
                    "method.response.header.Access-Control-Allow-Methods": "'GET,OPTIONS'",
                    "method.response.header.Access-Control-Allow-Origin": "'*'",
                    "method.response.header.Access-Control-Allow-Headers": "'Authorization,Content-Type,X-Amz-Date,X-Amz-Security-Token,X-Api-Key'"
                }
                }
                },
                "requestTemplates": {
                "application/json": "{\"statusCode\": 200}"
                },
                "passthroughBehavior": "when_no_match",
                "type": "mock",
                "contentHandling": "CONVERT_TO_TEXT"
                }
            }
            },
            "/list_bucket": {
            "post": {
                "consumes": [
                "application/json"
                ],
                "produces": [
                "application/json"
                ],
                "responses": {
                "200": {
                "description": "200 response",
                "schema": {
                "$ref": "#/definitions/Empty"
                }
                }
                },
                "x-amazon-apigateway-integration": {
                "responses": {
                "default": {
                "statusCode": "200"
                }
                },
                "uri": {
                "Fn::Sub": Match.any_value()
                },
                "passthroughBehavior": "when_no_match",
                "httpMethod": "POST",
                "contentHandling": "CONVERT_TO_TEXT",
                "type": "aws_proxy"
                },
                "summary": Match.any_value(), # "List the contents of a user-specified S3 bucket",
                "description": Match.any_value(), # "Body:\n\n.. code-block:: python\n\n    {\n        \"s3bucket\": string\n    }\n\n\nReturns:\n    A list of S3 keys (i.e. paths and file names) for all objects in the bucket.\n\n    .. code-block:: python\n\n        {\n            \"objects\": [{\n                \"key\": string\n                },\n                ...\n        }\n\nRaises:\n    500: ChaliceViewError - internal server error",
                "security": [
                {
                "sigv4": []
                }
                ]
            },
            "options": {
                "consumes": [
                "application/json"
                ],
                "produces": [
                "application/json"
                ],
                "responses": {
                "200": {
                "description": "200 response",
                "schema": {
                "$ref": "#/definitions/Empty"
                },
                "headers": {
                "Access-Control-Allow-Methods": {
                    "type": "string"
                },
                "Access-Control-Allow-Origin": {
                    "type": "string"
                },
                "Access-Control-Allow-Headers": {
                    "type": "string"
                }
                }
                }
                },
                "x-amazon-apigateway-integration": {
                "responses": {
                "default": {
                "statusCode": "200",
                "responseParameters": {
                    "method.response.header.Access-Control-Allow-Methods": "'POST,OPTIONS'",
                    "method.response.header.Access-Control-Allow-Origin": "'*'",
                    "method.response.header.Access-Control-Allow-Headers": "'Authorization,Content-Type,X-Amz-Date,X-Amz-Security-Token,X-Api-Key'"
                }
                }
                },
                "requestTemplates": {
                "application/json": "{\"statusCode\": 200}"
                },
                "passthroughBehavior": "when_no_match",
                "type": "mock",
                "contentHandling": "CONVERT_TO_TEXT"
                }
            }
            },
            "/get_data_columns": {
            "post": {
                "consumes": [
                "application/json"
                ],
                "produces": [
                "application/json"
                ],
                "responses": {
                "200": {
                "description": "200 response",
                "schema": {
                "$ref": "#/definitions/Empty"
                }
                }
                },
                "x-amazon-apigateway-integration": {
                "responses": {
                "default": {
                "statusCode": "200"
                }
                },
                "uri": {
                "Fn::Sub": Match.any_value()
                },
                "passthroughBehavior": "when_no_match",
                "httpMethod": "POST",
                "contentHandling": "CONVERT_TO_TEXT",
                "type": "aws_proxy"
                },
                "summary": Match.any_value(), # "Get the column names of a user-specified JSON or CSV file",
                "description": Match.any_value(), # "Body:\n\n.. code-block:: python\n\n    {\n        \"s3bucket\": string,\n        \"s3key\": string\n        \"file_format\": ['CSV', 'JSON']\n    }\n\n\nReturns:\n    List of column names and data types found in the first row of\n    the user-specified data file.\n\n    .. code-block:: python\n\n        {\n            \"object\": {\n            }\n        }\n\nRaises:\n    500: ChaliceViewError - internal server error",
                "security": [
                {
                "sigv4": []
                }
                ]
            },
            "options": {
                "consumes": [
                "application/json"
                ],
                "produces": [
                "application/json"
                ],
                "responses": {
                "200": {
                "description": "200 response",
                "schema": {
                "$ref": "#/definitions/Empty"
                },
                "headers": {
                "Access-Control-Allow-Methods": {
                    "type": "string"
                },
                "Access-Control-Allow-Origin": {
                    "type": "string"
                },
                "Access-Control-Allow-Headers": {
                    "type": "string"
                }
                }
                }
                },
                "x-amazon-apigateway-integration": {
                "responses": {
                "default": {
                "statusCode": "200",
                "responseParameters": {
                    "method.response.header.Access-Control-Allow-Methods": "'POST,OPTIONS'",
                    "method.response.header.Access-Control-Allow-Origin": "'*'",
                    "method.response.header.Access-Control-Allow-Headers": "'Authorization,Content-Type,X-Amz-Date,X-Amz-Security-Token,X-Api-Key'"
                }
                }
                },
                "requestTemplates": {
                "application/json": "{\"statusCode\": 200}"
                },
                "passthroughBehavior": "when_no_match",
                "type": "mock",
                "contentHandling": "CONVERT_TO_TEXT"
                }
            }
            },
            "/read_file": {
            "post": {
                "consumes": [
                "application/json"
                ],
                "produces": [
                "application/json"
                ],
                "responses": {
                "200": {
                "description": "200 response",
                "schema": {
                "$ref": "#/definitions/Empty"
                }
                }
                },
                "x-amazon-apigateway-integration": {
                "responses": {
                "default": {
                "statusCode": "200"
                }
                },
                "uri": {
                "Fn::Sub": Match.any_value()
                },
                "passthroughBehavior": "when_no_match",
                "httpMethod": "POST",
                "contentHandling": "CONVERT_TO_TEXT",
                "type": "aws_proxy"
                },
                "summary": Match.any_value(), # "Read the contents of a user-specified S3 object",
                "description": Match.any_value(), # "Body:\n\n.. code-block:: python\n\n    {\n        \"s3bucket\": string,\n        \"s3key\": string\n    }\n\n\nReturns:\n    The body of the use-specified S3 object.\n\n    .. code-block:: python\n\n        {\n            \"object\": {\n            }\n        }\n\nRaises:\n    500: ChaliceViewError - internal server error",
                "security": [
                {
                "sigv4": []
                }
                ]
            },
            "options": {
                "consumes": [
                "application/json"
                ],
                "produces": [
                "application/json"
                ],
                "responses": {
                "200": {
                "description": "200 response",
                "schema": {
                "$ref": "#/definitions/Empty"
                },
                "headers": {
                "Access-Control-Allow-Methods": {
                    "type": "string"
                },
                "Access-Control-Allow-Origin": {
                    "type": "string"
                },
                "Access-Control-Allow-Headers": {
                    "type": "string"
                }
                }
                }
                },
                "x-amazon-apigateway-integration": {
                "responses": {
                "default": {
                "statusCode": "200",
                "responseParameters": {
                    "method.response.header.Access-Control-Allow-Methods": "'POST,OPTIONS'",
                    "method.response.header.Access-Control-Allow-Origin": "'*'",
                    "method.response.header.Access-Control-Allow-Headers": "'Authorization,Content-Type,X-Amz-Date,X-Amz-Security-Token,X-Api-Key'"
                }
                }
                },
                "requestTemplates": {
                "application/json": "{\"statusCode\": 200}"
                },
                "passthroughBehavior": "when_no_match",
                "type": "mock",
                "contentHandling": "CONVERT_TO_TEXT"
                }
            }
            }
            },
            "definitions": {
            "Empty": {
            "type": "object",
            "title": "Empty Schema"
            }
            },
            "x-amazon-apigateway-binary-media-types": [
            "application/octet-stream",
            "application/x-tar",
            "application/zip",
            "audio/basic",
            "audio/ogg",
            "audio/mp4",
            "audio/mpeg",
            "audio/wav",
            "audio/webm",
            "image/png",
            "image/jpg",
            "image/jpeg",
            "image/gif",
            "video/ogg",
            "video/mpeg",
            "video/webm"
            ],
            "securityDefinitions": {
            "sigv4": {
            "in": "header",
            "type": "apiKey",
            "name": "Authorization",
            "x-amazon-apigateway-authtype": "awsSigv4"
            }
            }
            },
        }
    )

# Lambda Permission
def test_lambda_permission_creation(synth_nested_template):
    template = synth_nested_template
    template.resource_count_is("AWS::Lambda::Permission", 1)
    api_handler = Capture()
    template.has_resource_properties(
        "AWS::Lambda::Permission",
        {
            "Action": "lambda:InvokeFunction",
            "FunctionName": {
                "Ref": api_handler
            },
            "Principal": "apigateway.amazonaws.com",
            "SourceArn": {
                "Fn::Sub": [
                    Match.any_value(),
                    {
                        "RestAPIId": {
                            "Ref": "RestAPI"
                        }
                    }
                ]
            }
        }
    )
    	  		  
    assert ( template.to_json()["Resources"][api_handler.as_string()]["Type"] == "AWS::Serverless::Function")
