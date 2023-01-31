# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

#!/usr/bin/env python3
import os
import aws_cdk as cdk
from lib.uploader_stack import UploaderStack

import logging
from pathlib import Path

from aws_cdk import CfnParameter, App
from constructs import Construct

from aws_solutions.cdk import CDKSolution
from aws_solutions.cdk.stack import SolutionStack
from aws_solutions.cdk.aws_lambda.python.function import SolutionsPythonFunction
from aspects.app_registry import AppRegistry

# The solution helper build script expects this logger to be used
logger = logging.getLogger("cdk-helper")

# Initialize the CDKSolution helper - it will be used to build the templates in a solution-compatible manner
solution = CDKSolution(cdk_json_path=Path(__file__).parent.absolute() / "cdk.json")


@solution.context.requires("SOLUTION_NAME")
@solution.context.requires("SOLUTION_ID")
@solution.context.requires("SOLUTION_VERSION")
@solution.context.requires("BUCKET_NAME")
def build_app(context):
    app = App(context=context)
    stack = UploaderStack(
        app,
        "uploader",
        stack_name=app.node.try_get_context("STACK_NAME"),
        description="Audience Uploader from AWS Clean Rooms Solution CDK stack",
        template_filename="audience-uploader-from-aws-clean-rooms.template",
        synthesizer=solution.synthesizer,
    )
    cdk.Aspects.of(app).add(AppRegistry(stack, "AppRegistryAspect"))
    return app.synth()


if __name__ == "__main__":
    build_app()
