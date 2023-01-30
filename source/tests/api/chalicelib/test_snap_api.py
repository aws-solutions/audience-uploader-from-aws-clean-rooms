# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import json
from chalice.test import Client
import pytest
os.environ['AMC_ENDPOINT_URL'] = "Test"
os.environ['AMC_API_ROLE_ARN'] = "Test"
os.environ['VERSION'] = "v1.0.0"
os.environ['AMC_GLUE_JOB_NAME'] = "Test"
os.environ['AWS_REGION'] = "us-east-1"
import app

@pytest.mark.filterwarnings("ignore:IAMAuthorizer")
def test_start_snap_transformation(mocker):
    session_client_mocker = mocker.MagicMock()
    session_client_mocker.client.return_value = session_client_mocker
    expected_return = {"JobRunId": "test_id"}
    session_client_mocker.start_job_run.return_value = expected_return
    mocker.patch("app.boto3.session.Session", return_value=session_client_mocker)

    with Client(app.app) as client:
        response = client.http.post('/start_snap_transformation?',
                                    headers={'Content-Type': 'application/json'},
                                    body=json.dumps({"sourceBucket": "1", "sourceKey": "2", "outputBucket": "3", "piiFields": "4", "segmentName": "5"}))
        assert response.json_body == expected_return

    expected_return_2 = {"JobRunId": "test_id_2", "SomeOtherImportantData": "test_important_data"}
    session_client_mocker.start_job_run.return_value = expected_return_2

    with Client(app.app) as client:
        response = client.http.post('/start_snap_transformation?',
                                    headers={'Content-Type': 'application/json'},
                                    body=json.dumps({"sourceBucket": "1", "sourceKey": "2", "outputBucket": "3", "piiFields": "4", "segmentName": "5"}))
        assert response.json_body == {"JobRunId": "test_id_2"} # Assert that only the JobRunId is returned
