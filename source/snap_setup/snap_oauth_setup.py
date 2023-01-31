# Copyright Amazon.com, Inc. or its affiliates. All Rights Reserved.
# SPDX-License-Identifier: Apache-2.0

import json
from requests_oauthlib import OAuth2Session
import requests
from requests.structures import CaseInsensitiveDict
import webbrowser
import boto3
import argparse
parser = argparse.ArgumentParser()

def get_snap_credentials(secret_name):
    """get the snap credentials from local file"""
    with open(secret_name, "r") as f:
        snap_credentials = json.load(f)
    return snap_credentials


def update_secret_snap_credentials(secret_name, refresh_snap_credentials):
    """update the secret with the new oAuth Token"""
    session = boto3.Session(profile_name=args.profile, region_name=args.region)
    client = session.client("secretsmanager")
    response = client.put_secret_value(
        SecretId=secret_name, SecretString=json.dumps(refresh_snap_credentials)
    )
    return response


def get_snapchat_access_token(snap_credentials):
    """Generate snapchat refresh token"""
    scope = ["snapchat-marketing-api"]
    authorize_url = "https://accounts.snapchat.com/login/oauth2/authorize"
    access_token_url = "https://accounts.snapchat.com/login/oauth2/access_token"
    # User Auth via Redirect
    oauth = OAuth2Session(
        client_id=snap_credentials["client_id"],
        redirect_uri=snap_credentials["redirect_url"],
        scope=scope,
    )
    # Return the url
    authorization_url, state = oauth.authorization_url(authorize_url)
    print("Please go to %s and authorize access." % authorization_url)
    webbrowser.open(
        authorization_url,
    )
    # Use the authorization_url for get token
    authorization_response = input("Enter the full callback URL: ")
    token = oauth.fetch_token(
        token_url=access_token_url,
        authorization_response=authorization_response,
        client_secret=snap_credentials["client_secret"],
        scope=scope,
    )
    return token


def get_segment_id_by_name(snap_credentials, refresh_snap_credentials, segment_name):
    """Get a segment_id by Name"""

    ad_account_id = snap_credentials["ad_account_id"]
    url_segments = f"https://adsapi.snapchat.com/v1/adaccounts/{ad_account_id}/segments"
    headers = CaseInsensitiveDict()
    headers["Authorization"] = "Bearer " + refresh_snap_credentials["access_token"]
    headers["Content-Type"] = "application/json"

    res = requests.get(url=url_segments, headers=headers)
    data = json.dumps(res.json())
    data = json.loads(data)
    data = data["segments"]

    for segment in data:
        if segment["segment"]["name"] == segment_name:
            segment_id = segment["segment"]["id"]
            return segment_id

    return 0


def add_segment(snap_credentials, refresh_snap_credentials, segment_name):
    """Create a Demo Segment"""

    ad_account_id = snap_credentials["ad_account_id"]
    url_segments = f"https://adsapi.snapchat.com/v1/adaccounts/{ad_account_id}/segments"
    headers = CaseInsensitiveDict()
    headers["Authorization"] = "Bearer " + refresh_snap_credentials["access_token"]
    headers["Content-Type"] = "application/json"

    payload = {
        "segments": [
            {
                "name": segment_name,
                "description": "test segment",
                "source_type": "FIRST_PARTY",
                "retention_in_days": 180,
                "ad_account_id": ad_account_id,
            }
        ]
    }
    payload = json.dumps(payload)
    res = requests.post(url=url_segments, headers=headers, data=payload)
    return res.json()

parser.add_argument('--profile', action="store", dest='profile', default="default")
parser.add_argument('--region', action="store", dest='region')
parser.add_argument('--snapCredentialsOauthRefreshSecretName', action="store", dest='cedentials_oauth_refresh')
parser.add_argument('--snapCredentialsSecretName', action="store", dest='credentials')
parser.add_argument('--testAudienceName', action="store", dest='test_audience_name')

args = parser.parse_args()

# Run through getting an access url and then the oauth token

print("1. Getting the snapchat_credentials.json secret.")

snap_credentials = get_snap_credentials("snapchat_credentials.json")

print("2. Generating a token from callback URL")
oauth_token = get_snapchat_access_token(snap_credentials)

print(
    "3. Updating the client secrets to Secrets Manager for secret " + args.credentials
)

update_secret_snap_credentials(args.credentials, snap_credentials)

print(
    "4. Updating the oAuth token in Secrets Manager for secret " + args.cedentials_oauth_refresh
)
update_secret_snap_credentials(
    args.cedentials_oauth_refresh, oauth_token
)

test_audience_name = args.test_audience_name

segment_id = get_segment_id_by_name(
    snap_credentials, oauth_token, test_audience_name
)
print("Segment Id: " + str(segment_id))

print(
    f"5. Creating a test segment in Snapchat Ads Manager called {test_audience_name}"
)

if str(segment_id) == "0":
    add_segment(snap_credentials, oauth_token, test_audience_name)
else:
    print("Segment already exists.")

print(f" ")
print(f"Setup Complete.")
