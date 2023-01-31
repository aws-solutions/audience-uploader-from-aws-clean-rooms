# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from lambda_helpers import *
from snap.uploader.lambda_handler import *
from aws_xray_sdk.core import xray_recorder
xray_recorder.configure(context_missing='LOG_ERROR')


def test_get_snap_credentials(create_secrets, mocker):
    client, name, value = create_secrets
    mocker.patch('snap.uploader.lambda_handler.get_service_client', return_value = client)
    assert get_snap_credentials(name) == value


def test_update_snap_credentials(create_secrets, mocker):
    client, name, value = create_secrets
    mocker.patch('snap.uploader.lambda_handler.get_service_client', return_value = client)
    assert get_snap_credentials(name) == value
    update_snap_credentials(name, TEST_CREDENTIALS_2)
    assert get_snap_credentials(name) == TEST_CREDENTIALS_2



def test_refresh_token(mocker):
    content_mock = mocker.MagicMock()
    content_mock.decode.return_value = """{"refresh_token": "test"}"""
    content_mock.read.return_value = content_mock
    mocker.patch("snap.uploader.lambda_handler.urllib.request.urlopen", return_value = content_mock)

    expected_expiry = (datetime.now() + timedelta(seconds=1800))
    actual_expiry = datetime.strptime(refresh_token(TEST_CREDENTIALS, TEST_CREDENTIALS)["expires_at"], "%Y-%m-%d %H:%M:%S")
    #Assert our expiry times are almost equal to one another
    assert timedelta(seconds=-EXPECTED_EXPIRY_OFFSET) <= expected_expiry - actual_expiry <= timedelta(seconds=EXPECTED_EXPIRY_OFFSET)


def test_add_users(requests_mock):
    requests_mock.post(f"https://adsapi.snapchat.com/v1/segments/{TEST_SEGMENT_ID}/users",
        json=RESPONSE_SUCCESS
    )
    assert add_users("", TEST_SEGMENT_ID, "", "") == RESPONSE_SUCCESS


def test_get_segment_id_by_name(requests_mock):
    requests_mock.get(f"https://adsapi.snapchat.com/v1/adaccounts/{TEST_CREDENTIALS['ad_account_id']}/segments",
        json=TEST_SEGMENT_DATA
    )

    # Assert segment is found
    assert get_segment_id_by_name(TEST_CREDENTIALS, TEST_CREDENTIALS, "segment2") == 2

    # Assert segment is not found
    assert get_segment_id_by_name(TEST_CREDENTIALS, TEST_CREDENTIALS, "segment") == 0


def test_user_hash():
    assert user_hash(["a, b, c", "d, e", "f", "g, h", "i, j, k"]) == [["a", "b", "c"], ["d", "e"], ["f"], ["g", "h"], ["i", "j", "k"]]


def test_is_token_expired(create_times):
    expired, unexpired = create_times
    assert is_token_expired(expired)
    assert not is_token_expired(unexpired)


def test_lambda_handler(mocker):
    data_mock = mocker.MagicMock()
    data_mock.read_csv.return_value = data_mock
    data_mock.groupby.return_value = data_mock
    data_mock.groups.keys.return_value = ["EMAIL_SHA256"]
    data_mock.get_group.return_value = SCHEMA_HASH_VALUES

    mocker.patch("snap.uploader.lambda_handler.get_snap_credentials", return_value = TEST_CREDENTIALS)
    mocker.patch("snap.uploader.lambda_handler.is_token_expired", return_value = True)
    mocker.patch("snap.uploader.lambda_handler.refresh_token", return_value = TEST_CREDENTIALS)
    mocker.patch("snap.uploader.lambda_handler.update_snap_credentials")
    mocker.patch("snap.uploader.lambda_handler.get_segment_id_by_name", return_value = 1)
    mocker.patch("snap.uploader.lambda_handler.s3_client.get_object", return_value = {"Body": "test_body"})
    mocker.patch("snap.uploader.lambda_handler.pd.read_csv", return_value = data_mock)
    mocker.patch("snap.uploader.lambda_handler.add_users", return_value = SUCCESSFUL_UPLOAD_2)
    
    assert lambda_handler(FAKE_GZ_EVENT, None)["uploader"]["response"] == SUCCESSFUL_UPLOAD_2

    data_mock.groups.keys.return_value = []
    assert lambda_handler(FAKE_GZ_EVENT, None)["uploader"]["response"] == "no schemas were found"

    assert lambda_handler(FAKE_CSV_EVENT, None)["uploader"]["response"] == "not a supported file"
    