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
from lib.secrets.snap_secrets import SnapSecrets


class SnapUploaderStack(BaseUploaderStack):
    TARGET_PLATFORM = "snap"

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)

        self.snap_secrets = SnapSecrets(self, "SnapSecrets")

        self.add_lambda_dest_failure_queue()
        self.add_snap_lambda()

        self.add_lambda_event_source(self.snap_uploader_lambda, self.queue)

    ##############################################################################
    # Snap Lambda functions
    ##############################################################################

    # def add_snap_lambda(self, data_bucket_name):
    def add_snap_lambda(self):
        s3_read_policy_stmt = iam.PolicyStatement(
            resources=["arn:aws:s3:::uploader-etl-artifacts*"],
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

        # segment uploader
        self.snap_uploader_lambda = SolutionsPythonFunction(
            self,
            "snap-uploader-segment",
            entrypoint=Path(__file__).parent.parent.parent.absolute() / "aws_lambda" / "snap" / "uploader" / "lambda_handler.py",
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
                "REFRESH_SECRET_NAME": self.snap_secrets.oauth_refresh_secret.secret_name,
                "CRED_SECRET_NAME": self.snap_secrets.snap_uploader_secret.secret_name,
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
        self.snap_uploader_lambda.add_to_role_policy(s3_read_policy_stmt)
        self.snap_uploader_lambda.add_to_role_policy(queue_decrypt_policy_stmt)

        # Add read secret permissions for both secrets and write to oAuth
        self.snap_secrets.oauth_refresh_secret.grant_read(self.snap_uploader_lambda)
        self.snap_secrets.snap_uploader_secret.grant_read(self.snap_uploader_lambda)
        self.snap_secrets.oauth_refresh_secret.grant_write(self.snap_uploader_lambda)

        CfnOutput(self, "snapCredentialsOauthRefreshSecretName", value=self.snap_secrets.oauth_refresh_secret.secret_name)
        CfnOutput(self, "snapCredentialsSecretName", value=self.snap_secrets.snap_uploader_secret.secret_name)
