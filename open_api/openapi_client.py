#coding=utf-8

from .core.http import http_client
from .core.rsa_client import rsa_client as rsa
import datetime
import gzip
import json
import asyncio
import aiohttp

class openapi_client(object):
    AUTHORIZE_URL = "https://ac.ppdai.com/oauth2/authorize"
    REFRESHTOKEN_URL = "https://ac.ppdai.com/oauth2/refreshtoken"

    @staticmethod
    async def authorize(appid, code):
        data = "{\"AppID\":\"%s\",\"Code\":\"%s\"}" % (appid, code)
        data = data.encode("utf-8")
        timeout = aiohttp.ClientTimeout(total=10)
        async with aiohttp.ClientSession() as session:
            result = await http_client.http_post(session, timeout, openapi_client.AUTHORIZE_URL, data)
        return json.loads(result)

    @staticmethod
    async def refresh_token(session, timeout, appid, openid, refreshtoken):
        data = "{\"AppID\":\"%s\",\"OpenId\":\"%s\",\"RefreshToken\":\"%s\"}" % (appid,openid,refreshtoken)
        result = await http_client.http_post(session, timeout, openapi_client.REFRESHTOKEN_URL, data)
        return {'token_info':json.loads(result), 'OpenID':openid}

    @staticmethod
    async def send(session, timeout, url, data, headers, accesstoken=''):
        if accesstoken:
            headers["X-PPD-ACCESSTOKEN"] = accesstoken
        result = await http_client.http_post(session, timeout, url, data, headers=headers)
        return result