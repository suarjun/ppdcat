#coding=utf-8

__author__ = "yangl"


class http_client(object):


    REQUEST_HEADER = {'Connection': 'keep-alive',
                  'Cache-Control': 'max-age=0',
                  'Accept-Language': 'en-US,en;q=0.8,zh-CN;q=0.6,zh;q=0.4',
                  'Content-Type':'application/json;charset=utf-8'
                  }

    @staticmethod
    async def http_post(session, timeout, url, data, headers={}):
        headers = dict(http_client.REQUEST_HEADER, **headers)
        async with session.post(url, headers=headers, data=data, timeout=timeout) as resp:
            res = await resp.text()
            return res
