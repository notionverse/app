import base64
import json
import os
import requests
import urllib.parse

oauth_client_id = "YOUR_OAUTH_CLIENT_ID"
oauth_client_secret = "YOUR_OAUTH_CLIENT_SECRET"
redirect_uri = "YOUR_REDIRECT_URL"


base_url = 'https://api.notion.com/v1/oauth/token'

auth_headers = {
    'Authorization': 'Basic {}'.format(b64_encoded_key),
    'Content-Type': 'application/x-www-form-urlencoded;charset=UTF-8',
}

auth_data = {
    'grant_type': 'authorization_code',
    'code': auth_code,
    'redirect_uri':redirect_uri,
}

auth_resp = requests.post(base_url, headers=auth_headers, data=auth_data)
auth_resp.json()