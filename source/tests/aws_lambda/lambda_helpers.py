# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import pytest
import json
import boto3
import pandas as pd

from moto import mock_secretsmanager
from datetime import datetime, timedelta


os.environ["REFRESH_SECRET_NAME"] = "Test"
os.environ["CRED_SECRET_NAME"] = "Test"
os.environ["SOLUTION_ID"] = "SO0226"
os.environ["SOLUTION_VERSION"] = "v1.0.0"
os.environ["SOLUTION_NAME"] = "audience-uploader-from-aws-clean-rooms"
os.environ["AWS_REGION"] = "us-east-1"

TEST_CREDENTIALS = {"ad_account_id": "test_account_id", "expires_at": "test", "access_token": "test_access_token", "client_id": "test", "client_secret": "test", "refresh_token": "test"}
TEST_CREDENTIALS_2 = {"ad_account_id": "test_account_id_2"}
TEST_SEGMENT_ID = "test_segment_id"
TEST_SEGMENT_DATA = {"segments": [
    {"segment": {"name": "segment1", "id": 1}}, 
    {"segment": {"name": "segment2", "id": 2}}, 
    {"segment": {"name": "segment3", "id": 3}} 
]}

FAKE_GZ_EVENT = {"Records": [{"body":"""{"detail": {"bucket": {"name": "test_bucket_name"}, "object": {"key": "test1/test2/test3/PHONE_SHA256/test4.gz"}}}"""}]}
FAKE_CSV_EVENT = {"Records": [{"body":"""{"detail": {"bucket": {"name": "test_bucket_name"}, "object": {"key": "test1/test2/test3/PHONE_SHA256/test4.csv"}}}"""}]}

SCHEMA_HASH_VALUES = pd.DataFrame(data = {"schema": ["EMAIL_SHA256", "EMAIL_SHA256"], "hash": ["test_hash", "test_hash_2"]})

RESPONSE_SUCCESS = {"result": "success"}

SUCCESSFUL_UPLOAD_2 = {"result": "success", "users": [{"user": {"number_uploaded_users": 2}}]}

EXPECTED_EXPIRY_OFFSET = 3

@mock_secretsmanager
@pytest.fixture
def setup_secrets_client():
    with mock_secretsmanager():
        yield boto3.client("secretsmanager", region_name="us-east-1")

@pytest.fixture
def create_secrets(setup_secrets_client, create_times):
    expired, _ = create_times
    secret_name = "test_secret"

    secret_value = TEST_CREDENTIALS
    secret_value["expires_at"] = expired
    setup_secrets_client.create_secret(Name=secret_name, SecretString=json.dumps(secret_value))
    yield setup_secrets_client, secret_name, secret_value

@pytest.fixture
def create_times():
    now = datetime.now()
    expired = now - timedelta(hours=1)
    unexpired = now + timedelta(hours=1)
    yield expired.strftime("%Y-%m-%d %H:00:00"), unexpired.strftime("%Y-%m-%d %H:00:00")