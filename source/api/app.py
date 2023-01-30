# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from chalice import Chalice, IAMAuthorizer
import boto3
import json
import os
from chalicelib.snap_api import snap_routes
from chalicelib.tiktok_api import tiktok_routes

from aws_xray_sdk.core import xray_recorder
from aws_xray_sdk.core import patch_all
patch_all()

import logging

logger = logging.getLogger()
logger.setLevel(logging.INFO)

# Initialization
app = Chalice(app_name='audience-uploader-from-aws-clean-rooms')

app.register_blueprint(snap_routes)
app.register_blueprint(tiktok_routes)

authorizer = IAMAuthorizer()

# Environment variables
VERSION = os.environ['VERSION']
AMC_GLUE_JOB_NAME = os.environ['AMC_GLUE_JOB_NAME']


@app.route('/get_etl_jobs', cors=True, methods=['GET'], authorizer=authorizer)
def get_etl_jobs():
    """
    Retrieves metadata for all runs of a given Glue ETL job definition.

    Returns:

    .. code-block:: python

        {'JobRuns': [...]}
    """
    try:
        log_request_parameters()
        client = boto3.client('glue', region_name=os.environ['AWS_REGION'])
        response = client.get_job_runs(JobName=AMC_GLUE_JOB_NAME)
        for i in range(len(response['JobRuns'])):
            if 'Arguments' in response['JobRuns'][i]:
                response['JobRuns'][i]['SegmentName'] = response['JobRuns'][i]['Arguments']['--segment_name']
        return json.loads(json.dumps(response, default=str))
    except Exception as e:
        logger.error("Something went wrong while getting ETL jobs - ERROR: {}".format(e))
        raise Exception("Something went wrong while getting ETL jobs")


@app.route('/version', cors=True, methods=['GET'], authorizer=authorizer)
def version():
    """
    Get the solution version number.

    Returns:

    .. code-block:: python

        {"Version": string}
    """
    log_request_parameters()
    stack_version = {"version": VERSION}
    return stack_version

@app.route('/list_bucket', cors=True, methods=['POST'], content_types=['application/json'], authorizer=authorizer)
def list_bucket():
    """ List the contents of a user-specified S3 bucket

    Body:

    .. code-block:: python

        {
            "s3bucket": string
        }


    Returns:
        A list of S3 keys (i.e. paths and file names) for all objects in the bucket.

        .. code-block:: python

            {
                "objects": [{
                    "key": string
                    },
                    ...
            }

    Raises:
        500: ChaliceViewError - internal server error
    """
    log_request_parameters()
    try:
        s3 = boto3.resource('s3')
        bucket = json.loads(app.current_request.raw_body.decode())['s3bucket']
        results = []
        for s3object in s3.Bucket(bucket).objects.all():
            results.append({"key": s3object.key, "last_modified": s3object.last_modified.isoformat(
            ), "size": s3object.size})
        return json.dumps(results)
    except Exception as e:
        logger.error("Something went wrong while listing the contents of S3 bucket - ERROR: {}".format(e))
        raise Exception("Something went wrong while listing the contents of S3 bucket")


@app.route('/get_data_columns', cors=True, methods=['POST'], content_types=['application/json'], authorizer=authorizer)
def get_data_columns():
    """ Get the column names of a user-specified JSON or CSV file

    Body:

    .. code-block:: python

        {
            "s3bucket": string,
            "s3key": string
            "file_format": ['CSV', 'JSON']
        }


    Returns:
        List of column names and data types found in the first row of
        the user-specified data file.

        .. code-block:: python

            {
                "object": {
                }
            }

    Raises:
        500: ChaliceViewError - internal server error
    """
    try:
        import awswrangler as wr
        log_request_parameters()
        bucket = json.loads(app.current_request.raw_body.decode())['s3bucket']
        key = json.loads(app.current_request.raw_body.decode())['s3key']
        file_format = json.loads(app.current_request.raw_body.decode())[
            'file_format']
        if file_format != 'CSV' and file_format != 'JSON':
            raise TypeError('File format must be CSV or JSON')

        # Read first row
        logger.info("Reading " + 's3://'+bucket+'/'+key)
        if file_format == 'JSON':
            dfs = wr.s3.read_json(
                path=['s3://'+bucket+'/'+key], chunksize=1, lines=True)
        elif file_format == 'CSV':
            dfs = wr.s3.read_csv(path=['s3://'+bucket+'/'+key], chunksize=1)
        chunk = next(dfs)
        columns = list(chunk.columns.values)
        result = json.dumps({'columns': columns})
        return result
    except Exception as e:
        logger.error("Something went wrong while getting the column names - ERROR: {}".format(e))
        raise Exception("Something went wrong while getting the column names")

@app.route('/read_file', cors=True, methods=['POST'], content_types=['application/json'], authorizer=authorizer)
def read_file():
    """ Read the contents of a user-specified S3 object

    Body:

    .. code-block:: python

        {
            "s3bucket": string,
            "s3key": string
        }


    Returns:
        The body of the use-specified S3 object.

        .. code-block:: python

            {
                "object": {
                }
            }

    Raises:
        500: ChaliceViewError - internal server error
    """
    try:
        log_request_parameters()
        s3 = boto3.client('s3')
        bucket = json.loads(app.current_request.raw_body.decode())['s3bucket']
        key = json.loads(app.current_request.raw_body.decode())['s3key']
        results = s3.get_object(Bucket=bucket, Key=key)
        return json.dumps(results['ResponseMetadata'])
    except Exception as e:
        logger.error("Something went wrong while reading the file - ERROR: {}".format(e))
        raise Exception("Something went wrong while reading the file")

def log_request_parameters():
    logger.info("Processing the following request:\n")
    logger.info('userArn: ' + app.current_request.context['identity']['userArn'])
    logger.info('caller: ' + app.current_request.context['identity']['caller'])
    logger.info("resource path: " + app.current_request.context['resourcePath'])
    logger.info("method: " + app.current_request.method)
    logger.info("uri parameters: " + str(app.current_request.uri_params))
    logger.info("query parameters: " + str(app.current_request.query_params))
    logger.info("AWS request ID: " + app.current_request.lambda_context.aws_request_id)
    logger.info("request ID: " + app.current_request.context.get('requestId', ""))
