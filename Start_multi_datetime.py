#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2017/8/1 14:50
# @File    : Start.py
"""
应用启动类
"""
import sys
import json
import asyncio
# import logging
# import logging.config
# logging.config.fileConfig('start_logging.conf')
# logger = logging.getLogger('Start')
# logger_warning = logger.warning
import aiohttp
from functools import wraps
from datetime import datetime

from flask import Flask, render_template, flash, url_for, redirect, Blueprint, request
from flask_wtf.csrf import CSRFProtect
from flask_compress import Compress
from flask_bootstrap import Bootstrap
from flask_moment import Moment
from flask_login import LoginManager, login_user, UserMixin, logout_user, login_required, current_user
from flask_sqlalchemy import SQLAlchemy

from werkzeug.contrib.cache import SimpleCache
#from Model import Users # 与 token 类 update_token 方法中的 userInfo 赋值语句结合使用

''' #解决flash的一个bug
defaultencoding = 'utf-8'
if sys.getdefaultencoding() != defaultencoding:
    reload(sys)
    sys.setdefaultencoding(defaultencoding)
 '''

appid = "6aeed0c3774a473f936f128bddd97367"

cache = SimpleCache()
app = Flask(__name__)
Compress(app)  # 启用压缩响应内容
csrf = CSRFProtect()  # 启用 csrf 防御，开启后，所有表单的提交以及 Ajax 请求都需要带上 csrf token

log_file = 'web.log'
model_name = 'Start'

#各项插件的配置
app.config['CSRF_ENABLED'] = True
'''import os
os.urandom(24)'''
# SECRET_KEY 为随机值，由以上语句生成，也可以直接使用诸如'1234','abcd'这样的普通字符串
app.config['SECRET_KEY'] = '\xa8\xd2k\x91\x10\x87K{F\xdd\xb2\x04cA\xdc=\xb5\xd1\x8e\x9d\xbc\x7f\x8c_'
app.config['SQLALCHEMY_DATABASE_URI'] ='mysql+pymysql://xxsu:1300793suarjun@127.0.0.1/ppdcat'#配置数据库，mysql：数据库类型；pymysql：数据库驱动；用户名:密码@主机/数据库名
#app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///db/sqlite/user.db'# /// 为相对路径，////为绝对路径；
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False  # 如果设置成 True (默认情况)，Flask-SQLAlchemy 将会追踪对象的修改并且发送信号。这需要额外的内存，如果不必要的可以禁用它。
app.config['SQLALCHEMY_POOL_SIZE'] = 50  # 连接池大小
app.config['SQLALCHEMY_MAX_OVERFLOW'] = 50  # 控制在连接池达到最大值后可以创建的连接数。当这些额外的连接使用后回收到连接池后将会被断开和抛弃。保证连接池只有设置的大小；
app.config['SQLALCHEMY_POOL_TIMEOUT'] = 10  # 指定数据库连接池的超时时间。默认是 10
app.config['SQLALCHEMY_POOL_RECYCLE'] = 10  # 连接回收前空闲时间(秒)
app.config['SQLALCHEMY_COMMIT_ON_TEARDOWN'] = True  # 设置是否在每次连接结束后自动提交数据库中的变动。
app.config['SQLALCHEMY_ECHO'] = False  # 如果设置成 True，SQLAlchemy 将会记录所有 发到标准输出(stderr)的语句，这对调试很有帮助。关闭则可以提高性能
app.config['TEMPLATES_AUTO_RELOAD'] = True  # 模板自动重载

db = SQLAlchemy()
db.init_app(app)

bootstrap = Bootstrap(app)
moment = Moment(app)

login_manger = LoginManager()
# 认证加密程度
login_manger.session_protection = 'strong'
# 登陆认证的处理视图
login_manger.login_view = 'account.login'
# 配置用户认证信息
login_manger.init_app(app)


@login_manger.user_loader
def load_user(user_id):
    from Model_multi_datetime import Users
    return Users.query.get(int(user_id))

@app.route('/')
def index():
    if current_user.is_authenticated:
        code = request.values.get('code')  # 点击获取授权后，授权页面会在浏览器直接跳转到回调地址并在地址后附上 code 值，故用 request.values.get('code') 直接获取
        if code:
            Token().get_token(current_user, code)  # 获取 AccessToken 并保存
            return '''<font color='#228B22'>授权成功！<font>'''
        else:
            return redirect(url_for('account.index', name=current_user.Name))
    flash('已注册用户请输入账户密码并登录，新用户请先点击注册链接，进入注册页面注册账户', 'info')
    return redirect(url_for('account.login'))

@csrf.exempt  # 取消 CSRF 对该路由的保护
@app.route('/verify', methods=['POST'])
def verify():
    if request.json.get('verify'):
        import json
        import base64
        import time
        import requests
        from Model_multi_datetime import Users
        from open_api.core.Crypto_RSA import RSACrypto
        from open_api.core.server_key import server_private_key, server_public_key

        private_key = RSACrypto.load_private_key_pem(server_private_key)

        cookies_time_encrypted = base64.b64decode(request.json.get('verify'))
        user_encrypted = base64.b64decode(request.json.get('other'))

        cookies_time_decrypted = RSACrypto.decrypt(cookies_time_encrypted, private_key)
        cookies, timestamp = cookies_time_decrypted.split(":")
        user_decrypted = RSACrypto.decrypt(user_encrypted, private_key)

        if (time.time() - int(timestamp)) > 1800:
            logger(f"{user_decrypted} 试图使用过期授权信息，访问被拒绝，地址：{request.remote_addr}")
            return '拒绝访问'

        headers = {
            "Connection":"keep-alive",
            "Accept":"application/json, text/plain, */*",
            "User-Agent":"Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.26 Safari/537.36 Core/1.63.5050.400 QQBrowser/10.0.941.400",
            "Content-Type":"application/json;charset=UTF-8",
            "Accept-Encoding":"gzip, deflate, br",
            "Accept-Language":"zh-CN,zh;q=0.9",
            "Cookie":cookies
        }
        resp = requests.get('https://invest.ppdai.com/api/invuser/user/getUserName', headers=headers)
        res = resp.text

        if res:
            try:
                user_name = json.loads(res)['resultContent']
            except:
                return '{"verify":"令牌过期"}'
            else:
                if user_name:
                    if user_decrypted == user_name:
                        user = Users.query.filter(Users.AuthorizeBinding.like(f'%{user_name}%')).first()
                        if user:
                            authorize_binding = json.loads(user.AuthorizeBinding)
                            for key, value in authorize_binding.items():
                                if value.get("PPDUN") == user_name and value.get("Verify"):
                                    encrypt_str = '验证成功:'+str(int(time.time()))
                                    public_key = RSACrypto.load_public_key_pem(server_public_key)
                                    encrypted_str = RSACrypto.encrypt(encrypt_str, public_key)
                                    logger(f"{user_name} 通过验证，地址：{request.remote_addr}")
                                    return '{"verify":"%s"}' % base64.b64encode(encrypted_str).decode()
                        return '{"verify":"授权过期"}'
                    else:
                        logger(f"{request.remote_addr} 伪造授权，请求体 {request.json}")
                        return '{"verify":"伪造授权"}'
                else:
                    return '{"verify":"令牌过期"}'
        else:
            return '{"verify":"令牌过期"}'
    else:
        logger(f"{request.remote_addr} 参数错误，请求体 {request.json}")
        return '参数错误'


"""
蓝图注册
"""
def init():
    from Views_multi_datetime import account
    app.register_blueprint(blueprint=account, url_prefix='/account')


'''
处理令牌
'''
class Token(object):

    '''
    换取 AccessToken 返回值 authorizeObj 示例
    {
           "OpenID":"012ab36f894c45cfbfddf932eb906d98",
           "AccessToken":"69f96ee0-a37e-4a58-86d1-e7d58c064e2e",
           "RefreshToken":3890da19-a14f-4d50-9534-cdec40a41373
           "ExpiresIn":"604800"
       }
    换取 AccessToken 返回参数说明
    名称          是否必选    字段类型    参数释义
    AccessToken     是         string     身份令牌：访问网关接口的身份令牌（默认有效期7天）；
    OpenID          是         string     用户的开放平台ID：拍拍贷给予的开发者和授权用户之间的唯一关联ID
    ExpiresIn       是         number     令牌有效期：身份令牌的有效期，单位秒
    RefreshToken    是         string     刷新令牌：通过该令牌可以刷新AccessToken (有效期：90天)
    '''

    from open_api.openapi_client import openapi_client as client
    from open_api.core.rsa_client import rsa_client as rsa

    def __init__(self):
        pass

    def get_token(self, user, code):
        loop = asyncio.new_event_loop()  # 防止复用 loop 导致 RuntimeError: There is no current event loop in thread  错误，新建 event_loop
        asyncio.set_event_loop(loop)
        # 授权（privatekey 全局变量在 Global.py 中配置）
        token_info, ppd_user_name = loop.run_until_complete(self._get_token(code))
        loop.close()

        self.update_token(user, token_info, ppd_user_name)
        db.session.commit()

    async def _get_token(self, code):
        token_info = await self.client.authorize(appid, code)  # 授权（privatekey 全局变量在 Global.py 中配置）
        url = 'https://openapi.ppdai.com/open/openApiPublicQueryService/QueryUserNameByOpenID'
        timeout = aiohttp.ClientTimeout(total=10)
        utctime = datetime.utcnow()
        timestamp = utctime.strftime('%Y-%m-%d %H:%M:%S')
        headers = {
            "X-PPD-APPID":appid,
            "X-PPD-TIMESTAMP":timestamp,
            "X-PPD-TIMESTAMP-SIGN":self.rsa.sign(f"{appid}{timestamp}").decode(),
            "X-PPD-SIGN":self.rsa.sign("OpenID" + token_info['OpenID']).decode(),
            "Accept":"application/json;charset=UTF-8",
            'Connection': 'keep-alive',
            'Cache-Control': 'max-age=0',
            'Accept-Language': 'en-US,en;q=0.8,zh-CN;q=0.6,zh;q=0.4',
            'Content-Type':'application/json;charset=utf-8'
            }
        data = {"OpenID": token_info['OpenID']}
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, data=json.dumps(data), timeout=timeout) as resp:
                res = await resp.text()
            user_name = json.loads(res)["UserName"]
        return token_info, self.rsa.decrypt(user_name).decode()

    def update_token(self, user, token_info, ppd_user_name):
        # 将返回的 authorize 对象反序列化成 dict 对象 {"OpenID":"xx","AccessToken":"xxx","RefreshToken":"xxx","ExpiresIn":604800}，成功得到 OpenID、AccessToken、RefreshToken、ExpiresIn
        authorize_binding_dict = json.loads(user.AuthorizeBinding)
        for k, v in authorize_binding_dict.items():
            if v['State'] is 0:
                v['State'] = 1
                v['Authorized'] = 1
                v['AccessToken'] = token_info['AccessToken']
                v['RefreshToken'] = token_info['RefreshToken']
                v["PPDUN"] = ppd_user_name
                if token_info.get('OpenID'):
                    v['OpenID'] = token_info['OpenID']
                    if token_info['OpenID'] not in user.OpenIdBinding:
                        user.OpenIdBinding = user.OpenIdBinding + ',' + str(token_info['OpenID'])
                break
        user.AuthorizeBinding = str(authorize_binding_dict).replace("'",'"')
        user.Authorized = 1


class Log(object):

    def __init__(self, model_name='root', file=None):
        #self.width = os.get_terminal_size().columns -31
        self.model_name = model_name
        self.file = file

    def format(self, model_name, input):
        self.formatted = f'{datetime.now()} - {model_name} - {input}\r\n'

    def console(self, input):
        self.format(self.model_name, input)
        self._console()

    def _console(self):
        sys.stdout.write(self.formatted)
        sys.stdout.flush()

    def file(self, input):
        self.format(self.model_name, input)
        self._file()

    def _file(self):
        with open(self.file, 'a+') as f:
            f.write(self.formatted)

    def confile(self, input):
        self.format(self.model_name, input)
        self._console()
        self._file()


def cached(timeout=300, key='view_%s'):
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if request.values:
                return f(*args, **kwargs)
            cache_key = key % request.path
            value = cache.get(cache_key)
            if value is None:
                value = f(*args, **kwargs)
                cache.set(cache_key, value, timeout=timeout)
            return value
        return decorated_function
    return decorator

#在您的应用当中以一个显式调用 SQLAlchemy , 您只需要将如下代码放置在您应用 的模块中。Flask 将会在请求结束时自动移除数据库会话
@app.teardown_request
def shutdown_session(exception=None):
    db.session.remove()

if __name__ == '__main__':
    from Start_multi_datetime import db # 使用 db 前须导入，以初始化，具体原理不明
    from werkzeug.debug import DebuggedApplication
    from gevent import monkey, pywsgi
    monkey.patch_all()  # 猴子补丁会导致执行 select.epoll() 时，出现 AttributeError: module 'select' has no attribute 'epoll' 的错误， 故将代码置于此，以免在本模块被调用时污染调用程序

    init()

    logger = Log(model_name=model_name, file=log_file).confile
    csrf.init_app(app)
    #app.run(host='0.0.0.0', port=80, debug=True)
    app.debug = True
    dapp = DebuggedApplication(app, evalex= True)
    server = pywsgi.WSGIServer(('0.0.0.0', 80), dapp)
    server.serve_forever()
