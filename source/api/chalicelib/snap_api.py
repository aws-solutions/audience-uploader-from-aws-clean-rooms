# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from chalice import Blueprint, IAMAuthorizer
import boto3
import os
import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

authorizer = IAMAuthorizer()

snap_routes = Blueprint(__name__)

# Environment variables
AMC_GLUE_JOB_NAME = os.environ['AMC_GLUE_JOB_NAME']


@snap_routes.route('/start_snap_transformation', cors=True, methods=['POST'], authorizer=authorizer)
def start_snap_transformation():
    """
    Invoke Glue job to prepare data for uploading into Snap.

    """
    try:
        log_request_parameters()
        source_bucket = snap_routes.current_request.json_body['sourceBucket']
        source_key = snap_routes.current_request.json_body['sourceKey']
        output_bucket = snap_routes.current_request.json_body['outputBucket']
        pii_fields = snap_routes.current_request.json_body['piiFields']
        segment_name = snap_routes.current_request.json_body['segmentName']

        session = boto3.session.Session(region_name=os.environ['AWS_REGION'])
        client = session.client('glue')

        args = {
            "--source_bucket": source_bucket,
            "--output_bucket": output_bucket,
            "--source_key": source_key,
            "--pii_fields": pii_fields,
            "--segment_name": segment_name,
        }
        response = client.start_job_run(JobName=AMC_GLUE_JOB_NAME, Arguments=args)
        return {'JobRunId': response['JobRunId']}
    except Exception as e:
        logger.error("Something went wrong while starting Snap transformation - ERROR: {}".format(e))
        raise Exception("Something went wrong while starting Snap transformation")

def log_request_parameters():
    logger.info("Processing the following request:\n")
    logger.info("resource path: " + snap_routes.current_request.context['resourcePath'])
    logger.info("method: " + snap_routes.current_request.method)
    logger.info("uri parameters: " + str(snap_routes.current_request.uri_params))
    logger.info("query parameters: " + str(snap_routes.current_request.query_params))
    logger.info("request ID: " + snap_routes.current_request.context.get('requestId', ""))
    logger.info('request body: ' + snap_routes.current_request.raw_body.decode())
