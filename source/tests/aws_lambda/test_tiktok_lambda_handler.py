# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

from lambda_helpers import *
import tiktok.uploader.lambda_handler
from tiktok.uploader.lambda_handler import *
from aws_xray_sdk.core import xray_recorder
xray_recorder.configure(context_missing='LOG_ERROR')


def test_get_tiktok_credentials(create_secrets, mocker):
    client, name, value = create_secrets
    mocker.patch.object(tiktok.uploader.lambda_handler,
                        'tiktok_uploader_credentials', name)
    mocker.patch('tiktok.uploader.lambda_handler.boto3.client',
                 return_value=client)
    assert get_tiktok_credentials() == value


def test_update_tiktok_credentials(create_secrets, mocker):
    client, name, value = create_secrets
    mocker.patch.object(tiktok.uploader.lambda_handler, 'tiktok_uploader_credentials', name)
    mocker.patch('tiktok.uploader.lambda_handler.boto3.client', return_value=client)
    assert get_tiktok_credentials() == value
    update_tiktok_credentials(name, value)
    assert get_tiktok_credentials() == {"ACCESS_TOKEN": name, "ADVERTISER_ID": value}

    
def test_build_url():
    path, query = "test_path", "test_query"
    assert build_url("/" + path, query) == "https://business-api.tiktok.com/test_path?test_query"
    assert build_url(path, query) == "https://business-api.tiktok.com/test_path?test_query"
    
def test_get_custom_audience_obj():
    audience_1 = {"name": "test_audience_name_1"}
    audience_2 = {"name": "test_audience_name_2"}
    audience_3 = {"name": "test_audience_name_3"}
    audience_list = [audience_1, audience_2, audience_3]
    assert get_custom_audience_obj(audience_list, "test_audience_name_1") == audience_1
    assert get_custom_audience_obj(audience_list, "test_audience_name_3") == audience_3
    assert get_custom_audience_obj(audience_list, "test_audience_name") == None
    assert get_custom_audience_obj(audience_list, "") == None
    assert get_custom_audience_obj(audience_list, None) == None

def test_get_upload_audience_info(mocker):
    mocker.patch.dict(os.environ, {"SUPPORTED_CALCULATE_TYPES": "TYPE_1,TYPE_2"})
    assert get_upload_audience_info("test1/test2/test3/PHONE_SHA256/test4.zip") == ("test4.zip", "PHONE_SHA256", "test3")
    with pytest.raises(ValueError):
        get_upload_audience_info("test1/test4.zip")
        
def test_get_calculate_type(mocker):
    assert get_calculate_type("PHONE_SHA256") == "PHONE_SHA256"
    assert get_calculate_type("phone_sha256") == "PHONE_SHA256"
    assert get_calculate_type("idfa_sha256") == "IDFA_SHA256"
    with pytest.raises(ValueError):
        get_calculate_type("type_3")
        
def test_lambda_handler_happy_path(mocker):
    mocker.patch("tiktok.uploader.lambda_handler.upload_custom_audience_data", return_value={"code": 0, "data": {"file_path": "test1/test2/test3/test4.zip"}})
    mocker.patch("tiktok.uploader.lambda_handler.check_custom_audience_exist", return_value={"audience_id": "test_audience_id"})
    mocker.patch("tiktok.uploader.lambda_handler.update_custom_audience_data", return_value={"code": 0})
    mocker.patch("tiktok.uploader.lambda_handler.clean_up")
    assert lambda_handler(FAKE_CSV_EVENT, None) == {"statusCode": 200, "body": '"Custom Audience test3 is successfully updated in TikTok Ads!"'}
    mocker.patch("tiktok.uploader.lambda_handler.check_custom_audience_exist", return_value=None)
    mocker.patch("tiktok.uploader.lambda_handler.create_custom_audience_data", return_value={"code": 0})
    assert lambda_handler(FAKE_CSV_EVENT, None) == {"statusCode": 200, "body": '"Custom Audience test3 is successfully created to TikTok Ads!"'}
