# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from constructs import Construct
from aws_cdk.aws_lambda_event_sources import SqsEventSource
from aws_cdk import (
    aws_sqs as sqs,
    CfnParameter,
    aws_kms as kms,
    Stack
)
from aws_solutions.cdk.stack import NestedSolutionStack
from lib.aws_lambda.layers.aws_solutions.layer import SolutionsLayer

SOLUTION_ID = "SOLUTION_ID"
SOLUTION_VERSION = "SOLUTION_VERSION"

class BaseUploaderStack(NestedSolutionStack):
    def __init__(self, scope: Construct, construct_id: str, *args, **kwargs) -> None:
        super().__init__(scope, construct_id, *args, **kwargs)

        self.queue_arn_parameter = CfnParameter(self, "SQSArn")
        
        self.queue = sqs.Queue.from_queue_arn(
            self,
            id="SQS",
            queue_arn=self.queue_arn_parameter.value_as_string,
        )

        stack = Stack.of(self)
        self.solution_id = stack.node.try_get_context(SOLUTION_ID)
        self.solution_version = stack.node.try_get_context(SOLUTION_VERSION)

        #Layers
        self.layer_solutions = SolutionsLayer.get_or_create(self)

    ##############################################################################
    # Lambda dest failure Queue
    ##############################################################################
    def add_lambda_dest_failure_queue(self):
        key = kms.Key(self, "Key", enable_key_rotation=True)
        self.lambda_dest_failure_queue = sqs.Queue(
            self,
            "connector_dest_failure_queue",
            encryption=sqs.QueueEncryption.KMS,
            encryption_master_key=key,
        )

    ##############################################################################
    # Get Platform name
    ##############################################################################
    def get_platform_name(self):
        return self.TARGET_PLATFORM

    ##############################################################################
    # Add Lambda Event Source
    ##############################################################################

    def add_lambda_event_source(self, uploader_lambda, queue):
        event_source = SqsEventSource(queue, batch_size=1)
        queue.grant_consume_messages(uploader_lambda)
        uploader_lambda.add_event_source(event_source)
