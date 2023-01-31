# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from webbrowser import get
from constructs import Construct
from aws_cdk import Aspects
from aws_solutions.cdk.cfn_nag import CfnNagSuppressAll, CfnNagSuppression
from aws_cdk import (
    cloudformation_include as cfn_inc,
    CfnParameter,
    CfnCondition,
    Fn,
    aws_ssm as ssm,
)
from pathlib import Path
from lib.base_uploader_stack import BaseUploaderStack
from lib.snap_uploader_stack import SnapUploaderStack
from lib.tiktok_uploader_stack import TiktokUploaderStack
from lib.eventbridge_mappings import EventbridgeToSQS
from aws_solutions.cdk.stack import SolutionStack


class UploaderStack(SolutionStack):
    def __init__(self, scope: Construct, id: str, description: str, template_filename, **kwargs) -> None:
        super().__init__(scope, id, description, template_filename, **kwargs)

        # Define CfnParameter for target platform
        self.target_platform_parameter = CfnParameter(
            self,
            "TargetPlatform",
            type="String",
            description="Please provide the target platform",
            allowed_values=["tiktok"],
        )
        self.metrics.update({"TargetPlatform": self.target_platform_parameter.value})

        eventbridge_to_sqs = EventbridgeToSQS(self)
        queue = eventbridge_to_sqs.construct_stack.sqs_queue

        self.include_cf_stack()

        # Snap nested stack
        self.snap_stack = SnapUploaderStack(
            self,
            "SnapUploaderStack",
            description="Snap Uploader Stack",
            template_filename="snap-stack.template",
            parameters={"SQSArn": queue.queue_arn},
        )
        self.set_deploy_condition(self.snap_stack, self.target_platform_parameter)

        # Tiktok nested stack
        self.tiktok_stack = TiktokUploaderStack(
            self,
            "TiktokUploaderStack",
            description="Tiktok Uploader Stack",
            template_filename="tiktok-stack.template",
            parameters={"SQSArn": queue.queue_arn},
        )
        self.set_deploy_condition(self.tiktok_stack, self.target_platform_parameter)

        self.add_cfn_nag_suppress()

    ##############################################################################
    # Set deploy condition for nested stacks
    ##############################################################################

    def set_deploy_condition(self, nested_stack: BaseUploaderStack, target_platform_parameter):
        nested_stack_platform_name = nested_stack.get_platform_name()
        condition_id = nested_stack_platform_name + "-PlatformEqualParameter"
        deploy_condition = CfnCondition(
            self,
            condition_id,
            expression=Fn.condition_equals(target_platform_parameter, nested_stack_platform_name),
        )
        nested_stack.nested_stack_resource.add_override("Condition", deploy_condition.logical_id)

    ##############################################################################
    # CloudFormation cf Stacks
    ##############################################################################

    def include_cf_stack(self):
        path = f"{Path(__file__).parents[3]}/deployment/cfn-templates/"
        key = "aws:solutions:templatename"
        self.cf_stack = cfn_inc.CfnInclude(
            self,
            "Template",
            template_file=path + "uploader-from-clean-rooms.yaml",
            load_nested_stacks=dict(
                GlueStack=cfn_inc.CfnIncludeProps(template_file=path + "uploader-from-clean-rooms-glue.yaml"),
                WebStack=cfn_inc.CfnIncludeProps(template_file=path + "uploader-from-clean-rooms-web.yaml"),
                AuthStack=cfn_inc.CfnIncludeProps(template_file=path + "uploader-from-clean-rooms-auth.yaml"),
                ApiStack=cfn_inc.CfnIncludeProps(template_file=path + "uploader-from-clean-rooms-api.yaml"),
            ),
        )

        glue_nested_stack = self.cf_stack.get_nested_stack("GlueStack")
        glue_nested_stack.stack.nested_stack_resource.add_metadata(key, "uploader-from-clean-rooms-glue.yaml")
        glue_nested_stack.stack.set_parameter("TargetPlatform", self.target_platform_parameter.value_as_string)

        web_nested_stack = self.cf_stack.get_nested_stack("WebStack")
        web_nested_stack.stack.nested_stack_resource.add_metadata(key, "uploader-from-clean-rooms-web.yaml")
        web_nested_stack.stack.set_parameter("TargetPlatform", self.target_platform_parameter.value_as_string)

        auth_nested_stack = self.cf_stack.get_nested_stack("AuthStack")
        auth_nested_stack.stack.nested_stack_resource.add_metadata(key, "uploader-from-clean-rooms-auth.yaml")

        api_nested_stack = self.cf_stack.get_nested_stack("ApiStack")
        api_nested_stack.stack.nested_stack_resource.add_metadata(key, "uploader-from-clean-rooms-api.yaml")

    def add_cfn_nag_suppress(self):
        Aspects.of(self).add(
            CfnNagSuppressAll(
                suppress=[
                    CfnNagSuppression(
                        "W89",
                        "HelperFunction and MetricsFunctions do not required to be inside a VPC",
                    ),
                    CfnNagSuppression(
                        "W92",
                        "HelperFunction and MetricsFunctions do not required to reserve simultaneous executions",
                    ),
                ],
                resource_type="AWS::Lambda::Function",
            )
        )

        Aspects.of(self).add(
            CfnNagSuppressAll(
                suppress=[
                    CfnNagSuppression("W12", "IAM policy for AWS X-Ray requires an allow on *"),
                    CfnNagSuppression("W76", "This IAM role does need to access multiple services"),
                ],
                resource_type="AWS::IAM::Policy",
            )
        )

        Aspects.of(self).add(
            CfnNagSuppressAll(
                suppress=[
                    CfnNagSuppression("W77", "Uses the account's default AWS managed CMK. Cross-account secret sharing is not required")
                ],
                resource_type="AWS::SecretsManager::Secret",
            )
        )
