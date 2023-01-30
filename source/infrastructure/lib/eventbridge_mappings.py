# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from aws_cdk import (
    aws_events as events,
    aws_sqs as sqs,
    Stack,
    Duration,
    aws_kms as kms
)
from aws_solutions_constructs.aws_eventbridge_sqs import EventbridgeToSqs
from constructs import Construct


class EventbridgeToSQS(Construct):
    """Link the Glue Job Event Bridge notifications to the SQS queues to kick off activators"""

    def __init__(self, scope: Construct):
        super().__init__(scope, "EventBrSqs")

        key = kms.Key(self, "Key", enable_key_rotation=True)
        queue = sqs.Queue(
            self,
            "activator_connector",
            encryption=sqs.QueueEncryption.KMS,
            encryption_master_key=key,
            data_key_reuse=Duration.days(1),
            visibility_timeout=Duration.minutes(90),
        )

        # create the bus object to watch for the Glue Job notifications
        construct_stack = EventbridgeToSqs(
            self,
            "EventBrToSqs",
            event_rule_props=events.RuleProps(
                event_pattern=events.EventPattern(
                    source=["aws.s3"],
                    detail_type=["Object Created"],
                    account=[Stack.of(self).account],
                    region=[Stack.of(self).region],
                    detail={"bucket": {"name": [{"prefix": "uploader-etl-artifacts"}]},
                            "object": {"key": [{"prefix": "output/"}]}
                            }
                )
            ),
            deploy_dead_letter_queue=True,
            existing_queue_obj=queue,
            dead_letter_queue_props=sqs.QueueProps(
                encryption=sqs.QueueEncryption.KMS,
                encryption_master_key=key
            ),
        )

        # return the new stack with the new Eventbridge and new SQS
        self.construct_stack = construct_stack