# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
import os
import logging
from botocore.exceptions import ClientError
import json
import requests
from requests.structures import CaseInsensitiveDict
import pandas as pd
import urllib.parse
import gzip
from datetime import datetime, timedelta
from aws_solutions.core.helpers import get_service_client

logger = logging.getLogger()
logger.setLevel(logging.INFO)

s3_client = get_service_client("s3")
secrets_client = get_service_client("secretsmanager")


snap_uploader_credentials_oauth_refresh = os.environ["REFRESH_SECRET_NAME"]
snap_uploader_credentials = os.environ["CRED_SECRET_NAME"]
APPLICATION_JSON_HEADER = "application/json"


def get_snap_credentials(secret_name):
    """Get the snap credentials from Secret Manager"""


    response = secrets_client.get_secret_value(SecretId=secret_name)
    snap_credentials = []
    snap_credentials = json.loads(response["SecretString"])
    return snap_credentials


def update_snap_credentials(secret_name, new_snap_credentials):
    """Update the credentials in SecretManager"""
    response = secrets_client.put_secret_value(
        SecretId=secret_name, SecretString=json.dumps(new_snap_credentials)
    )

    return response


def refresh_token(snap_credentials, snap_refresh_credentials):
    """Get the oAuth Refresh Token"""
    access_token_url = "https://accounts.snapchat.com/login/oauth2/access_token"
    params = {}
    params["client_id"] = snap_credentials["client_id"]
    params["client_secret"] = snap_credentials["client_secret"]
    params["refresh_token"] = snap_refresh_credentials["refresh_token"]
    params["grant_type"] = "refresh_token"
    response = (
        urllib.request.urlopen( # nosec, B310 vulnerability does not apply to URL's that start with http (eg only for ftp:, file:)
            access_token_url, urllib.parse.urlencode(params).encode("UTF-8") # nosec, B310
        )
        .read()
        .decode("UTF-8")
    )

    response = json.loads(response)
    expires_at = datetime.now() + timedelta(seconds=1800)
    expires_at = expires_at.strftime("%Y-%m-%d %H:%M:%S")
    response["expires_at"] = expires_at

    return response


def add_users(access_token, segment_id, schema, data):
    """Get all available accounts for credentials in the form of a list"""
    url_segments = f"https://adsapi.snapchat.com/v1/segments/{segment_id}/users"

    headers = CaseInsensitiveDict()
    headers["Accept"] = APPLICATION_JSON_HEADER
    headers["Authorization"] = "Bearer " + access_token
    headers["Content-Type"] = APPLICATION_JSON_HEADER

    payload = {"users": [{"schema": [schema], "data": data}]}
    payload = json.dumps(payload)
    res = requests.post(url=url_segments, headers=headers, data=payload)
    return res.json()


def get_segment_id_by_name(snap_credentials, snap_refresh_credentials, segment_name):
    """Get the segment id by name"""

    ad_account_id = snap_credentials["ad_account_id"]
    url_segments = f"https://adsapi.snapchat.com/v1/adaccounts/{ad_account_id}/segments"
    headers = CaseInsensitiveDict()
    headers["Accept"] = APPLICATION_JSON_HEADER
    headers["Authorization"] = "Bearer " + snap_refresh_credentials["access_token"]
    headers["Content-Type"] = APPLICATION_JSON_HEADER

    res = requests.get(url=url_segments, headers=headers)
    data = json.dumps(res.json())
    data = json.loads(data)
    data = data["segments"]

    for segment in data:
        if segment["segment"]["name"] == segment_name:
            segment_id = segment["segment"]["id"]
            return segment_id

    return 0


def user_hash(lst):
    """Get the user hashes"""
    res = []
    for el in lst:
        sub = el.split(", ")
        res.append(sub)
    return res


def is_token_expired(expires_at):
    """check if the oAuth Token is expired"""
    try:
        expires_at = datetime.strptime(expires_at, "%Y-%m-%d %H:%M:%S")
        time_now = datetime.now()

        if expires_at < time_now:
            logger.info("Token expired")
            return True
        else:
            logger.info("Token is valid")
            return False
    except TypeError as _:
        logger.info("Expire data format is not valid")
        return True
    


def lambda_handler(event, _):

    try:
        # getting secret from secret manager
        snap_credentials = []
        snap_refresh_credentials = get_snap_credentials(
            snap_uploader_credentials_oauth_refresh
        )

        # get the snap client credentials
        snap_credentials = get_snap_credentials(snap_uploader_credentials)

        # find out if token expired
        token_expires_at = snap_refresh_credentials["expires_at"]

        # refresh the token if it expired
        if is_token_expired(token_expires_at):
            snap_refresh_credentials = get_snap_credentials(
                snap_uploader_credentials_oauth_refresh
            )
            # get refresh token
            snap_refresh_credentials = refresh_token(
                snap_credentials, snap_refresh_credentials
            )

            # updated the new oauth secret in Secret Manager
            update_snap_credentials(
                snap_uploader_credentials_oauth_refresh, snap_refresh_credentials
            )

        for record in event["Records"]:
            # input event from s3 put event from sqs
            segment_name_prefix = ""

            logger.info(record["body"])
            bucket_name = json.loads(record["body"])["detail"]["bucket"][
                "name"
            ]
            key = urllib.parse.unquote_plus(
                json.loads(record["body"])["detail"]["object"]["key"],
                encoding="utf-8",
            )

            segment_name_prefix, file_name = os.path.split(key)

            segment_name_prefix = segment_name_prefix.split("/")
            segment_name_prefix = str(segment_name_prefix[2])

            logger.info(segment_name_prefix)

            # get segment id by segment name
            segment_id = get_segment_id_by_name(
                snap_credentials, snap_refresh_credentials, segment_name_prefix
            )

            # snap supported schemas
            schema_options = ["EMAIL_SHA256", "MOBILE_AD_ID_SHA256", "PHONE_SHA256"]

            if not file_name.endswith(".gz"):
                logger.info("not a supported file")
                return {
                    "uploader": {
                        "response": "not a supported file",
                    }
                }
            
            # add segment users
            # loop through the csv for each schema option and add each schema users to the  segment
            obj = s3_client.get_object(Bucket=bucket_name, Key=key)
            with gzip.GzipFile(fileobj=obj['Body'], mode='rb') as f:

                data_csv = pd.read_csv(f).groupby("schema")

                # initialize for the case where no schemas exist within the data_csv keys
                add_user_resp = "no schemas were found"

                for schema in schema_options:

                    if schema in data_csv.groups.keys():

                        schema_data = data_csv.get_group(schema)

                        if not schema_data.empty:

                            data = user_hash(schema_data["hash"].tolist())
                            add_user_resp = add_users(
                                snap_refresh_credentials["access_token"],
                                segment_id,
                                schema,
                                data,
                            )
                            count_row = schema_data.shape[0]
                            logger.info(
                                schema
                                + " has "
                                + str(count_row)
                                + " rows of data in "
                                + key
                            )

                            users_added_count = str(
                                add_user_resp["users"][0]["user"]["number_uploaded_users"]
                            )

                            logger.info(
                                "Users added to segment: "
                                + segment_name_prefix
                                + " is "
                                + users_added_count
                            )

                    else:
                        logger.info(schema + " is empty")

                return {
                    "uploader": {
                        "response": add_user_resp,
                    }
                }

    except ClientError as e:
        logger.error(e)
        return {"uploader": {"statusCode": e}}
