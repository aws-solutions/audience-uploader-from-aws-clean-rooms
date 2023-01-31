# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from constructs import Construct
from aws_solutions.cdk.aws_lambda.python.function import SolutionsPythonFunction
from aws_cdk import (
    aws_lambda as _lambda,
    aws_iam as iam,
    CfnOutput,
    Duration,
    aws_lambda_destinations as _lambda_dest,
)
from pathlib import Path
from lib.base_uploader_stack import BaseUploaderStack
from lib.secrets.tiktok_secrets import TiktokSecrets


class TiktokUploaderStack(BaseUploaderStack):
    TARGET_PLATFORM = "tiktok"

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)


        self.tiktok_secrets = TiktokSecrets(self, "TiktokSecrets")

        self.add_lambda_dest_failure_queue()
        self.add_tiktok_lambda()

        self.add_lambda_event_source(self.tiktok_uploader_lambda, self.queue)

    ##############################################################################
    # Tiktok Lambda functions
    ##############################################################################

    def add_tiktok_lambda(self):
        s3_read_policy_stmt = iam.PolicyStatement(
            resources=[
                "arn:aws:s3:::uploader-etl-artifacts*"
            ],
            actions=[
                "S3:ListBucket",
                "S3:GetObjectTagging",
                "S3:ListBucket",
                "S3:GetObject",
                "S3:PutBucketNotification",
            ],
        )

        queue_decrypt_policy_stmt = iam.PolicyStatement(
            actions=["kms:Decrypt"],
            resources=["*"],
        )

        layer_arn = f"arn:aws:lambda:{self.region}:580247275435:layer:LambdaInsightsExtension:21"

        # segment uploader for SQS
        self.tiktok_uploader_lambda = SolutionsPythonFunction(
            self,
            "tiktok-uploader-segment-sqs",
            entrypoint=Path(__file__).parent.parent.parent.absolute() / "aws_lambda" / "tiktok" / "uploader" / "lambda_handler.py",
            function="lambda_handler",
            runtime=_lambda.Runtime.PYTHON_3_9,
            description="activate users to segment",
            timeout=Duration.seconds(900),
            memory_size=256,
            reserved_concurrent_executions=2,
            insights_version=_lambda.LambdaInsightsVersion.from_insight_version_arn(
                layer_arn
            ),
            tracing=_lambda.Tracing.ACTIVE,
            environment={
                "CRED_SECRET_NAME": self.tiktok_secrets.tiktok_uploader_secret.secret_name,
                "SOLUTION_ID": self.solution_id,
                "SOLUTION_VERSION": self.solution_version
            },
            layers=[
                _lambda.LayerVersion.from_layer_version_arn(
                    self,
                    "datawrangler-02",
                    f"arn:aws:lambda:{self.region}:336392948345:layer:AWSDataWrangler-Python39:9",
                ),
                self.layer_solutions
            ],
            on_failure=_lambda_dest.SqsDestination(self.lambda_dest_failure_queue),
        )

        # Add inline policy to the lambda
        self.tiktok_uploader_lambda.add_to_role_policy(s3_read_policy_stmt)
        self.tiktok_uploader_lambda.add_to_role_policy(queue_decrypt_policy_stmt)

        # Add read secret permissions for both secrets and write to oAuth
        self.tiktok_secrets.tiktok_uploader_secret.grant_read(
            self.tiktok_uploader_lambda
        )
        self.tiktok_secrets.tiktok_uploader_secret.grant_write(
            self.tiktok_uploader_lambda
        )
        

        CfnOutput(self, "tiktokCredentialsSecretName", value=self.tiktok_secrets.tiktok_uploader_secret.secret_name)

