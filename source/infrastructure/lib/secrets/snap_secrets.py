# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
from constructs import Construct
from aws_cdk import (
    RemovalPolicy,
    aws_secretsmanager as secretsmanager,
)


class SnapSecrets(Construct):

    def __init__(self, scope: Construct, id: str, **kwargs) -> None:
        super().__init__(scope, id, **kwargs)
        self.oauth_refresh_secret = secretsmanager.Secret(
            self,
            "snap_uploader_credentials_oauth_refresh",
            description="snapads marketing api - oauth refresh",
            removal_policy=RemovalPolicy.RETAIN,
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps({"credentials": ""}),
                generate_string_key="credentials",
            ),
        )

        self.snap_uploader_secret = secretsmanager.Secret(
            self,
            "snap_uploader_credentials",
            description="snapads marketing api - credentials",
            removal_policy=RemovalPolicy.RETAIN,
            generate_secret_string=secretsmanager.SecretStringGenerator(
                secret_string_template=json.dumps({"credentials": ""}),
                generate_string_key="credentials",
            ),
        )