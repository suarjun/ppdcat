# !/usr/bin/env python
# -*- coding: utf-8 -*-
# Created on 2018-05-15 21:36:25
# Model: Autobid
'''
程序名：拍拍猫自动投标程序
作者：西海岸
'''
import os
import sys
import re
import time
import json
# import logging
# import logging.config

# logging.config.fileConfig('ppdcat_logging.conf')
# logger = logging.getLogger('PPDcat')

from sqlalchemy import func
from decimal import Decimal
from collections import defaultdict, deque
from pybloom_live import ScalableBloomFilter
from datetime import datetime, date, timedelta

from Start_multi_datetime import app, appid, db, Log
from Model_multi_datetime import Users, AllBids, gentable
from open_api.core.rsa_client import rsa_client as rsa
from Event_Loop_AB_BD import Loop


log_file = 'ppdcat.log'
model_name = 'PPDcat'


class AutoBid(object):


    def __init__(self):
        # 共用
        self.AA_limit_file = 'AA_limit'  # 赔标(债)起投设置
        with open(self.AA_limit_file, 'r', encoding='utf-8') as f:
            AA_limit_info = json.load(f)

        self.policy_file = 'policy/policy'  # 策略路径

        self.school_file = 'school/school'  # 院校路径
        with open(self.school_file, 'r', encoding='utf-8') as f:  # 读取 985 院校列表
            school_info = json.load(f)

        self.sbf = ScalableBloomFilter(initial_capacity=100, error_rate=0.001, mode=ScalableBloomFilter.LARGE_SET_GROWTH)
        self.nef = list(school_info['985_211'])
        self.logger = Log(model_name=model_name, file=log_file).confile
        self.rsa_sign = rsa.sign
        self.repeated_reminders = defaultdict(dict)

        self.openapi_host = 'openapi.ppdai.com'
        self.www_host = 'www.ppdai.com'
        self.invest_host = 'invest.ppdai.com'

        # 投标
        self.balance_url = "/balance/balanceService/QueryBalance"
        self.listing_url = "/listing/openapiNoAuth/loanList"
        self.loan_url = "/listing/openapiNoAuth/batchListingInfo"
        self.bid_url = "/listing/openapi/bid"
        self.query_bid_url = '/listingbid/openapi/queryBid'

        self.cc_min = 5  # 限制投标代币最小金额
        self.AA_rate_min = AA_limit_info['AA_rate_min']  # 赔标起投利率
        self.balance_min = 100  # 限制投标账户最小余额
        self.bid_cost_rate = Decimal(0.0015)  # 散标扣费计算费率
        self.restart_producter_times = 36  # 重启生产者循环的次数
        self.back_seconds = 10  # 列表回溯秒数

        self.timeout = 1
        self.b2r = defaultdict(list)
        self.bid_list_dict = defaultdict(list)
        self.d2r = defaultdict(list)
        self.debt_list_dict = defaultdict(list)
        self.all_bids_dict = {}
        self.Balance_Authorized = set()
        self.user_cc = {}

        self.viewBar = ViewBar()
        self.process = 0
        self.error = 0
        self.success = 0
        self.fail = 0

        # 债权
        self.transfer_host = "transfer.ppdai.com"
        #self.get_buy_list_url = "/api/debt/pcBuyDebtService/getBuyList"  # 需登录接口
        self.get_buy_list_url = "/api/debt/pcBuyDebtWithNoAuthService/getBuyList"  # 免登录接口
        self.buy_list_url = "/debt/openapiNoAuth/buyList"
        self.buy_debt_url = "/debt/openapi/buy"
        self.query_order_url = "/debt/openapi/queryOrder"
        self.headers_debt = [
            "Connection:keep-alive\r\n" \
            "Accept:application/json, text/plain, */*\r\n" \
            "User-Agent:Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.26 Safari/537.36 Core/1.63.5050.400 QQBrowser/10.0.941.400\r\n" \
            "Content-Type:application/json;charset=UTF-8\r\n" \
            "Accept-Language:zh-CN,zh;q=0.9\r\n"
            ]
        self.AA_debt_rate_min = AA_limit_info['AA_debt_rate_min']  # 赔债起投利率
        self.request_interval_market = AA_limit_info['request_interval_market']
        self.request_interval_api = AA_limit_info['request_interval_api']
        self.waiting_time_for_rerty = AA_limit_info['waiting_time_for_rerty']

        self.debt_cost_rate_base = Decimal(0.00075)  # 基础扣费
        self.debt_cost_rate_base_double = self.debt_cost_rate_base * 2  # 双倍扣费
        # 债权扣费计算费率
        self.debt_cost_rate = {
            12:self.debt_cost_rate_base * Decimal(1.2),
            13:self.debt_cost_rate_base * Decimal(1.4),
            14:self.debt_cost_rate_base * Decimal(1.6),
            15:self.debt_cost_rate_base * Decimal(1.8)
        }
        self.debt_cost_rate_min, self.debt_cost_rate_max = 12, 15
        self.process_debt = 0
        self.error_debt = 0
        self.success_debt = 0
        self.fail_debt = 0
        self.process_debt_api = 0
        self.error_debt_api = 0
        self.success_debt_api = 0
        self.fail_debt_api = 0

        # 更新逾期
        self.repayment_url = "/creditor/openapi/fetchLenderRepayment"
        self.request_interval_over_due = 1

        # 微信提醒
        self.ifeige_host = 'u.ifeige.cn'
        self.ifeige_send_user_url = '/api/message/send-user'
        self.ifeige_headers = ["content-type:application/json\r\n"]
        self.ifeige_secret_key = 'c0f7bf6c5017745d351372afaf1fb9a8'
        self.alert_weixin = {}
        self.ifeige_template_id = {
            '余额不足': {
                'secret': self.ifeige_secret_key,
                'uid': '',
                'template_id': 'KebYBh23-qzBAICi7zGFi3hFEPVBgF6rEtRDHLR_gk8',
                'data': {
                    'first': {
                        'value': '',
                        'color': '#173177'
                    },
                    'keyword1': {
                        'value': '',
                        'color': '#173177'
                    },
                    'keyword2': {
                        'value': '',
                        'color': '#173177'
                    },
                    'remark': {
                        'value': '请及时充值',
                        'color': '#173177'
                    }
                }
            }
        }

    def tasks_loop(self):
        self.logger('开始启动拍拍猫')
        loop_host_dict = {
            self.openapi_host:{'create_free_sockets':50, 'min_free_sockets':30, 'max_free_sockets':70},
            self.transfer_host:{'create_free_sockets':4, 'min_free_sockets':2, 'max_free_sockets':10}
        }
        self.loop = Loop(loop_host_dict=loop_host_dict)
        #self.loop.add_future_loop(self.start())  # 添加为定长循环任务
        self.loop.add_future_loop(self.start_sign())  # 加密 StartDateTime 参数
        self.loop.add_future_loop(self.get_debt_market(), self.request_interval_market)
        self.loop.add_future_loop(self.get_debt_api(), self.request_interval_api)
        self.loop.add_future_loop(self.get_over_due(), self.request_interval_over_due)
        #self.loop.add_future(self.get_bid_list('xxsu'))
        self.loop.run_forever()

    def start(self):
        self.txt = ''
        self.headers = [
            "X-PPD-SIGN:S+GZ4Cx08eGWUWAEzEVex4FdGX9aHLcDb1sVcMvvQ2IlHw0d6nviFqB1yv6rIOxCo+tRtTtXU89AoUg17+t6IXy1gsesJiD8pvv7MJCINXcNd15Kg1cGwviKfYnQtvcupKZJM62m5pSTBWXUGdAtymZmR2Wl/eQmSbNEo0pR7bg=\r\n",
            "X-PPD-TIMESTAMP:\r\n",
            "X-PPD-TIMESTAMP-SIGN:\r\n",
            f"X-PPD-APPID:{appid}\r\n",
            "Accept:application/json;charset=UTF-8\r\n" \
            "Connection:keep-alive\r\n" \
            "Cache-Control:no-cache\r\n" \
            "Accept-Language:en-US,en;q=0.8,zh-CN;q=0.6,zh;q=0.4\r\n" \
            "Content-Type:application/json;charset=utf-8\r\n"
            ]
        listing_ids_data = '{"PageIndex":1}'

        loan_list_url = '/api/invapi/ListingListNoAuthService/listingPagerNoAuth'
        loan_list_headers = [
            "Connection:keep-alive\r\n" \
            "Accept:application/json, text/plain, */*\r\n" \
            "Origin:https://invest.ppdai.com\r\n" \
            "x-ppd-appid: 10000008\r\n" \
            "User-Agent:Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.26 Safari/537.36 Core/1.63.6726.400 QQBrowser/10.2.2265.400\r\n" \
            "Content-Type:application/json;charset=UTF-8\r\n" \
            "Accept-Encoding:gzip, deflate, br\r\n" \
            "Accept-Language:zh-CN,zh;q=0.9\r\n"
            ]
        loan_list_data = '{"authInfo":"","authenticated":false,"availableBalance":0,"creditCodes":"","dataList":[],"didIBid":"0","maxAmount":0,"minAmount":0,"months":"","needTotalCount":true,"pageCount":0,"pageIndex":1,"pageSize":10,"rates":"","riskLevelCategory":"1","sort":0,"source":1,"successLoanNum":"","totalCount":0}'
        while 1:
            token().refresh_all_token()
            for i in range(48):
                self.refresh_env()
                for i in range(5):
                    for index in range(1, self.restart_producter_times+1, 1):
                        self.loop.add_future(self.get_loan_list(loan_list_url, loan_list_headers, loan_list_data))
                        for each in range(10):
                            yield self.loop.add_future(self.get_listing_ids(listing_ids_data))
                        self.viewBar.view_bar(i, self.restart_producter_times, success=self.success, fail=self.fail, process=self.process, error=self.error)
                    self.viewBar.new_line()
                    self.result()
            self.sbf.filters.clear()  # 清空布隆过滤器
            #self.sbf = ScalableBloomFilter(initial_capacity=10, error_rate=0.001, mode=ScalableBloomFilter.LARGE_SET_GROWTH)

    def start_sign(self):
        self.txt = ''
        self.headers = [
            "X-PPD-SIGN:\r\n",
            "X-PPD-TIMESTAMP:\r\n",
            "X-PPD-TIMESTAMP-SIGN:\r\n",
            f"X-PPD-APPID:{appid}\r\n",
            "Accept:application/json;charset=UTF-8\r\n" \
            "Connection:keep-alive\r\n" \
            "Cache-Control:no-cache\r\n" \
            "Accept-Language:en-US,en;q=0.8,zh-CN;q=0.6,zh;q=0.4\r\n" \
            "Content-Type:application/json;charset=utf-8\r\n"
            ]
        """loan_list_url = '/api/invapi/ListingListNoAuthService/listingPagerNoAuth'
        loan_list_headers = [
            "Connection:keep-alive\r\n" \
            "Accept:application/json, text/plain, */*\r\n" \
            "Origin:https://invest.ppdai.com\r\n" \
            "x-ppd-appid: 10000008\r\n" \
            "User-Agent:Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.26 Safari/537.36 Core/1.63.6726.400 QQBrowser/10.2.2265.400\r\n" \
            "Content-Type:application/json;charset=UTF-8\r\n" \
            "DNT:1\r\n" \
            "Referer:https://invest.ppdai.com/loan/listpage/?risk=1&mirror=&pageIndex=1&showMore=0\r\n" \
            "Accept-Encoding:gzip, deflate, br\r\n" \
            "Accept-Language:zh-CN,zh;q=0.9\r\n"
            ]
        loan_list_data = '{"authInfo":"","authenticated":false,"availableBalance":0,"creditCodes":"","dataList":[],"didIBid":"0","maxAmount":0,"minAmount":0,"months":"","needTotalCount":true,"pageCount":0,"pageIndex":1,"pageSize":10,"rates":"","riskLevelCategory":"1","sort":0,"source":1,"successLoanNum":"","totalCount":0}'"""
        while 1:
            token().refresh_all_token()
            for each in range(48):
                self.refresh_env()  # 初始化环境，刷新令牌后，必须及时重置环境，否则 self.bid_enable_users 中的令牌信息未更新，将导致“令牌不存在”的错误
                for index in range(5):
                    for i in range(1, self.restart_producter_times+1, 1):
                        #StartDateTime = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(time.time() - self.back_seconds))
                        StartDateTime = str(datetime.now() - timedelta(seconds=self.back_seconds))[:23]
                        #StartDateTime = str(datetime.now() - timedelta(minutes=1))[:19]
                        #StartDateTime = str(datetime.now())[:19]
                        sign = f"X-PPD-SIGN:{self.rsa_sign('StartDateTime' + StartDateTime).decode()}\r\n"
                        data = '{"PageIndex":1, "StartDateTime":"%s"}' % StartDateTime
                        #for each in range(10):
                            #self.loop.add_future(self.get_loan_list(loan_list_url, loan_list_headers, loan_list_data))
                        for each in range(100):
                            yield self.loop.add_future(self.get_listing_ids_sign(sign, data))
                        self.viewBar.view_bar(i, self.restart_producter_times, success=self.success, fail=self.fail, process=self.process, error=self.error)
                    self.viewBar.new_line()
                    self.result()
            self.sbf.filters.clear()  # 清空布隆过滤器
            #self.sbf = ScalableBloomFilter(initial_capacity=10, error_rate=0.001, mode=ScalableBloomFilter.LARGE_SET_GROWTH)

    def result(self):
        # 删除借款信息 loan_info 中的暂无价值参数
        loan_info_pop_keys = ["FistBidTime", "LastBidTime", "LenderCount", "AuditingTime", \
            "RemainFunding", "DeadLineTimeOrRemindTimeStr", "BorrowName", "FirstSuccessBorrowTime", \
            "LastSuccessBorrowTime", "RegisterTime", "PhoneValidate", "Rate"]

        users_save_CC = set()
        if self.b2r:
            for user_name, bid_infos in self.b2r.items():
                users_save_CC.add(user_name)
                # 保存用户标信息
                user_bids = gentable(user_name, '_Bids')  # 动态建表
                db.session.bulk_insert_mappings(user_bids, bid_infos)  # 如数据库中有重复数据，将插入失败，并导致程序阻塞
            self.b2r.clear()

        if self.d2r:
            for user_name, bid_infos in self.d2r.items():
                users_save_CC.add(user_name)
                # 保存用户债权信息
                user_bids = gentable(user_name, '_Debts')
                db.session.bulk_insert_mappings(user_bids, bid_infos)
            self.d2r.clear()

        for user_name in users_save_CC:
            self.save_users(user_name, 'CC')  # 保存代币余额

        # if self.bid_list_dict:  # 拍拍贷账户投标总表
            # for user_name, bid_infos in self.bid_list_dict.items():
                # user_lists = gentable(user_name, '_Lists')
                # db.session.bulk_insert_mappings(user_lists, bid_infos)
            # self.bid_list_dict = defaultdict(list)

        if self.all_bids_dict:
            for loan_info in self.all_bids_dict.values():
                FirstSuccessBorrowTime = loan_info.get('FirstSuccessBorrowTime')
                LastSuccessBorrowTime = loan_info.get('LastSuccessBorrowTime')

                if FirstSuccessBorrowTime:
                    RegisterTimeDT = datetime.strptime(loan_info['RegisterTime'][:10],'%Y-%m-%d')  # 转换为 datetime 对象
                    FirstSuccessBorrowTimeDT = datetime.strptime(FirstSuccessBorrowTime[:10],'%Y-%m-%d')
                    FirstRegTime = (FirstSuccessBorrowTimeDT - RegisterTimeDT).days
                    loan_info['FirstRegTime'] = FirstRegTime
                else:
                    loan_info['FirstRegTime'] = -1

                if LastSuccessBorrowTime:
                    LastSuccessBorrowTimeDT = datetime.strptime(LastSuccessBorrowTime[:10],'%Y-%m-%d')
                    NowLastTime = (datetime.now() - LastSuccessBorrowTimeDT).days
                    loan_info['NowLastTime'] = NowLastTime
                else:
                    loan_info['NowLastTime'] = -1

                for key in loan_info_pop_keys:
                    if key in loan_info:
                        del loan_info[key]

                # 保存标信息
                #db.session.bulk_insert_mappings(AllBids, [loan_info])  # 采用 orm 的 bulk_insert_mappings 形式写入，以优化批量写入性能
                # 防止多人投同一标时，重复写入标信息，将导致 sqlalchemy.exc.IntegrityError: (pymysql.err.IntegrityError) (1062, "Duplicate entry '124448529' for key 'PRIMARY'") 错误，使用 merge方法 规避，相当于更新数据
                db.session.merge(AllBids(**loan_info))
            self.all_bids_dict.clear()

        if self.Balance_Authorized:
            for user_name, bind_name, save_type in self.Balance_Authorized:
                self.save_users(user_name, save_type, bind_name=bind_name)
            self.Balance_Authorized.clear()

        db.session.commit()

    def refresh_env(self):
        with open(self.AA_limit_file, 'r', encoding='utf-8') as f:
            AA_limit_info = json.load(f)
        self.AA_rate_min = AA_limit_info['AA_rate_min']
        self.AA_debt_rate_min = AA_limit_info['AA_debt_rate_min']
        self.request_interval_market = AA_limit_info['request_interval_market']
        self.request_interval_api = AA_limit_info['request_interval_api']
        self.waiting_time_for_rerty = AA_limit_info['waiting_time_for_rerty']

        # 未限制账户余额用户信息查询语句
        enable_users_query = Users.query.filter(Users.Authorized != 0, Users.CC >= self.cc_min)

        # 遍历账户余额不足的用户，查询其实际余额，以备下次查询
        insufficient_balance_all = enable_users_query.filter(Users.Balance != 2).all()
        if insufficient_balance_all:
            self.get_save_user_balance(insufficient_balance_all)

        bid_enable_users = self.query_enable_users(enable_users_query)  # 可投标用户信息
        debt_enable_users = self.query_enable_users(enable_users_query, user_type='Debt')  # 可购买债权用户信息

        with open(self.policy_file, 'r', encoding='utf-8') as f:
            policy = json.load(f)
        self.bid_enable_users, self.sys_policy_users, self.sys_policy_infos, self.AA_policy_infos = self._refresh_env(bid_enable_users, policy)
        self.debt_enable_users, self.sys_debt_policy_users, self.sys_debt_policy_infos, self.AA_debt_policy_infos = self._refresh_env(debt_enable_users, policy)

        db.session.commit()

    def _refresh_env(self, enable_users, policy):
        all_user_sys_policys = set()  # 所有用户已开启系统策略列表 [policy1,policy2]
        # 每个呈开启状态系统策略的所属用户列表所汇总的字典 {policy1:[user1, user2],policy2:[user1, user2, user3]}
        sys_policy_users = {}

        for user_name, user_info in enable_users.items(): # 枚举投资账户呈开启状态的系统策略
            for policy_name, policy_info in user_info['Policy']['系统策略'].items():
                if policy_info.get('AuthorizeBinding'):
                    if policy_name in sys_policy_users:
                        sys_policy_users[policy_name].append(user_name)
                    else:
                        sys_policy_users[policy_name] = [user_name]
                    if policy_name not in all_user_sys_policys:
                        all_user_sys_policys.add(policy_name)

        # 获取用户猫币余额
        for user_name in enable_users:
            if not self.user_cc.get(user_name):
                self.user_cc[user_name] = {}
                self.user_cc[user_name]['CC'] = self.user_cc[user_name]['pre_CC'] = enable_users[user_name].pop('CC')
            else:
                del enable_users[user_name]['CC']
            if user_name not in self.alert_weixin:
                if enable_users[user_name]['AlertWeiXin']:
                    self.alert_weixin[user_name] = enable_users[user_name].pop('AlertWeiXin')
            else:
                del enable_users[user_name]['AlertWeiXin']

        # 系统(债转)策略读取
        sys_policy_infos = {}  # 所有用户已开启的信标系统策略的信息字典列表
        AA_policy_infos = {}  # 所有用户已开启的赔标策略的信息字典列表，目前为系统策略，后续可考虑改为读取全部赔标策略

        for policy_name in all_user_sys_policys:
            if policy[policy_name]['info']['in'].get('GraduateSchool'):
                policy[policy_name]['info']['in']['GraduateSchool'] = self.nef  # 赋值 985 院校列表
            if policy[policy_name]['info']['in'].get('CreditCode') == ["AA"]:
                AA_policy_infos[policy_name] = policy[policy_name]
            else:
                sys_policy_infos[policy_name] = policy[policy_name]

        return enable_users, sys_policy_users, sys_policy_infos, AA_policy_infos

    def query_enable_users(self, enable_users_query, user_type='Bid'):
        # 获取账户余额充足的可投标用户信息
        if user_type == 'Bid':
            enable_users_all = enable_users_query.filter(Users.BidSwitch == 1, Users.Balance != 0).all()
        else:
            enable_users_all = enable_users_query.filter(Users.DebtSwitch == 1, Users.Balance != 0).all()
        enable_users = {}

        # 去除余额不足的用户及绑定为空的策略
        for enable_user in enable_users_all:
            authorize_binding = json.loads(enable_user.AuthorizeBinding)
            del_bind_name_list = set()
            authorize_binding_enable = defaultdict(dict)
            for bind_name, bind_info in authorize_binding.items():
                if bind_info['Balance'] >= self.balance_min and bind_info['Authorized'] == 1:
                    self.repeated_reminders[enable_user.Name][bind_name] = {'Authorized':True, 'Sufficient_Balance':True}
                    authorize_binding_enable[bind_name] = bind_info
                else:
                    del_bind_name_list.add(bind_name)

            if user_type == 'Bid':
                policy = json.loads(enable_user.Policy)
            else:
                policy = json.loads(enable_user.DebtPolicy)

            policy_enable = defaultdict(dict)
            for policy_type in ['自选策略','系统策略']:
                for policy_name, policy_info in policy[policy_type].items():
                    if policy_info.get('AuthorizeBinding'):
                        policy_info['AuthorizeBinding'] = [bind_name for bind_name in policy_info['AuthorizeBinding'] if bind_name not in del_bind_name_list]
                        if policy_info['AuthorizeBinding']:
                            if policy_type == '自选策略' and policy_info['info']['in'].get('GraduateSchool'):
                                policy_info['info']['in']['GraduateSchool'] = self.nef  # 赋值 985 院校列表
                            policy_enable[policy_type][policy_name] = policy_info

            if authorize_binding_enable and policy_enable:
                enable_users[enable_user.Name] = {
                    'CC': enable_user.CC,
                    'Policy': policy_enable,
                    'AuthorizeBinding': authorize_binding_enable,
                    #'Cookies':enable_user.Cookies if enable_user.CookiesEnable else None,
                    'AlertWeiXin':json.loads(enable_user.AlertWeiXin) if enable_user.AlertWeiXin else {}
                }

        return enable_users

    def get_save_user_balance(self, insufficient_balance_all):
        timestamp = str(datetime.utcnow())[:19]
        headers = [
            f"X-PPD-APPID:{appid}\r\n" \
            f"X-PPD-TIMESTAMP:{timestamp}\r\n" \
            f"X-PPD-TIMESTAMP-SIGN:{self.rsa_sign(appid+timestamp).decode()}\r\n" \
            "X-PPD-SIGN:S+GZ4Cx08eGWUWAEzEVex4FdGX9aHLcDb1sVcMvvQ2IlHw0d6nviFqB1yv6rIOxCo+tRtTtXU89AoUg17+t6IXy1gsesJiD8pvv7MJCINXcNd15Kg1cGwviKfYnQtvcupKZJM62m5pSTBWXUGdAtymZmR2Wl/eQmSbNEo0pR7bg=\r\n" \
            "Accept:application/json;charset=UTF-8\r\n" \
            "Connection:keep-alive\r\n" \
            "Cache-Control:no-cache\r\n" \
            "Accept-Language:en-US,en;q=0.8,zh-CN;q=0.6,zh;q=0.4\r\n" \
            "Content-Type:application/json;charset=utf-8\r\n"
            ]
        for balance_low_user in insufficient_balance_all:
            self.loop.add_future(self._get_save_user_balance(balance_low_user, headers))

    def _get_save_user_balance(self, balance_low_user, headers):
        balance_low_user_authorize_binding = json.loads(balance_low_user.AuthorizeBinding)
        num_balance_sufficiently = 0
        for bind_name, bind_info in balance_low_user_authorize_binding.items():
            if bind_info['Balance'] < self.balance_min:
                access_token = f"X-PPD-ACCESSTOKEN:{bind_info['AccessToken']}\r\n"
                res = yield self.loop.request(self.openapi_host, self.balance_url, headers, '{}', access_token=access_token)
                if res:
                    result = json.loads(res)
                    if result.get("Result") == 0:
                        bind_info['Balance'] = result['Balance'][0]['Balance']
                        if bind_info['Balance'] >= self.balance_min:
                            num_balance_sufficiently += 1
            else:
                num_balance_sufficiently += 1
        balance_low_user.AuthorizeBinding = str(balance_low_user_authorize_binding).replace('\'', '\"').replace(' ','')

        if num_balance_sufficiently == len(balance_low_user_authorize_binding):
            balance_low_user.Balance = 2
        elif num_balance_sufficiently:
            balance_low_user.Balance = 1
        else:
            balance_low_user.Balance = 0

        db.session.commit()

    def save_users(self, user_name, types, bind_name=None):
        user = Users.query.filter_by(Name=user_name).first()
        if types == 'CC':
            if int(user.CC) == int(self.user_cc[user_name]['pre_CC']):
                user.CC = self.user_cc[user_name]['pre_CC'] = self.user_cc[user_name]['CC']
            else:
                user.CC = self.user_cc[user_name]['CC'] = self.user_cc[user_name]['pre_CC'] = user.CC - (self.user_cc[user_name]['pre_CC'] - self.user_cc[user_name]['CC'])
        elif types == 'Balance':
            authorize_binding = json.loads(user.AuthorizeBinding)
            authorize_binding[bind_name]['Balance'] = 0
            for bind_name, bind_info in authorize_binding.items():
                if bind_info['Balance'] >= self.balance_min:
                    user.Balance = 1
                    break
            else:
                user.Balance = 0
            user.AuthorizeBinding = str(authorize_binding).replace('\'', '\"').replace(' ','')
        elif types == 'Authorized':
            authorize_binding = json.loads(user.AuthorizeBinding)
            authorize_binding[bind_name]['Authorized'] = 0
            for bind_name, bind_info in authorize_binding.items():
                if bind_info['Authorized'] != 0:
                    user.Authorized = 1
                    break
            else:
                user.Authorized = 0
            user.AuthorizeBinding = str(authorize_binding).replace('\'', '\"').replace(' ','')

    def get_bid_list(self, user_name):
        while 1:
            user = Users.query.filter_by(Name=user_name, CookiesEnable=1).first()
            if user:
                headers = [
                    "Connection:keep-alive\r\n" \
                    "Accept:application/json, text/plain, */*\r\n" \
                    "Origin:https://www.ppdai.com\r\n" \
                    "User-Agent:Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.26 Safari/537.36 Core/1.63.6726.400 QQBrowser/10.2.2265.400\r\n" \
                    "Content-Type:application/json;charset=UTF-8\r\n" \
                    "DNT:1\r\n" \
                    "Referer:https://www.ppdai.com/moneyhistory\r\n" \
                    "Accept-Encoding:gzip, deflate, br\r\n" \
                    "Accept-Language:zh-CN,zh;q=0.9\r\n",
                    f"Cookie:{user.Cookies}\r\n"
                    ]
                db.session.commit()
                url = '/api/cms/account/moneyHistory'
                data = '{"page":1,"size":20,"time":3,"type":0}'

                self.list_history = set()
                while 1:
                    # 向布隆过滤器添加当前列表中的所有标，以避免爬取到重复标，导致写入阻塞
                    result = yield self.loop.request(self.www_host, url, headers, data)
                    #print('投标列表', result)
                    if result:
                        if '<html' in result:
                            self.logger(f'\033[41;1m{user_name} cookies已过期，采集投标记录失败\033[0m')
                            yield self.loop.await_sleep(1)
                            while 1:
                                user = Users.query.filter_by(Name=user_name, CookiesEnable=1).first()
                                if user:
                                    headers[-1] = f"Cookie:{user.Cookies}\r\n"
                                    result = yield self.loop.request(self.www_host, url, headers, data)
                                    if result:
                                        if '<html' in result:
                                            self.logger(f'\033[41;1m{user_name} 模拟授权设置为无效\033[0m')
                                            user.CookiesEnable = 0
                                        else:
                                            db.session.commit()
                                            yield self.loop.await_sleep(1)
                                            break
                                    else:
                                        yield self.loop.await_sleep(10)
                                        continue
                                db.session.commit()
                                yield self.loop.await_sleep(1800)
                        else:
                            showMoneyHistory = json.loads(result)['resultContent']['showMoneyHistory']
                            self.list_history = {each['descriptionNoHtml'] for each in showMoneyHistory}
                            break
                    else:
                        yield self.loop.await_sleep(10)
                self.loop.add_future(self._get_bid_list(user_name, url, headers, data))
                break
            else:
                db.session.commit()
                yield self.loop.await_sleep(1800)

    def _get_bid_list(self, user_name, url, headers, data):
        # 正式开始爬取
        while 1:
            for i in range(86400 // 120):
                yield self.loop.await_sleep(60)
                while 1:
                    result = yield self.loop.request(self.www_host, url, headers, data)
                    #print(result)
                    if result:
                        if '<html' in result:
                            self.logger(f'\033[41;1m{user_name} cookies已过期，采集投标记录失败\033[0m')
                            yield self.loop.await_sleep(1)
                            while 1:
                                user = Users.query.filter_by(Name=user_name, CookiesEnable=1).first()
                                if user:
                                    headers[-1] = f"Cookie:{user.Cookies}\r\n"
                                    result = yield self.loop.request(self.www_host, url, headers, data)
                                    if result:
                                        if '<html' in result:
                                            self.logger(f'\033[41;1m{user_name} 模拟授权设置为无效\033[0m')
                                            user.CookiesEnable = 0
                                        else:
                                            db.session.commit()
                                            break
                                    else:
                                        db.session.commit()
                                        yield self.loop.await_sleep(10)
                                        continue
                                db.session.commit()
                                yield self.loop.await_sleep(1800)
                        else:
                            #print('投标列表结果',result)
                            try:
                                showMoneyHistory = json.loads(result)['resultContent']['showMoneyHistory']
                            except ValueError:
                                yield self.loop.await_sleep(2)
                                continue
                            if showMoneyHistory:
                                #print('开始查询投标详情')
                                self.loop.add_future(self._get_loan_infos(showMoneyHistory, user_name))
                            break
                    else:
                        yield self.loop.await_sleep(10)
            while 1:
                user = Users.query.filter_by(Name=user_name, CookiesEnable=1).first()
                if user:
                    headers[-1] = f"Cookie:{user.Cookies}\r\n"
                    db.session.commit()
                    break
                db.session.commit()
                yield self.loop.await_sleep(1800)

    def _get_loan_infos(self, showMoneyHistory, user_name):
        list_history_new = {each['descriptionNoHtml'] for each in showMoneyHistory}
        list_history_diff = list_history_new.difference(self.list_history)
        #print(f'差集：{list_history_diff}，新记录：{list_history_new}，历史记录：{self.list_history}')
        #print('查询投标详情')
        if list_history_diff:
            self.list_history = list_history_new
            #lists_dict = dict((int(each.split('：')[1].split('策')[0]), int(each.split('标')[1].split('.')[0])) for each in list_history_diff)
            lists_dict = {}
            for each in list_history_diff:
                list_num = re.findall(r"\d+", each)
                lists_dict[int(list_num[2])] = int(list_num[0])
            #print('投标列表', lists_dict)
            bid_listing_ids = list(lists_dict)
            for i in range(0, len(bid_listing_ids), 10):
                bid_listing_ids_ten = bid_listing_ids[i:i+10]
                data = '{"ListingIds":%s}' % bid_listing_ids_ten
                while 1:
                    headers = self.headers.copy()
                    headers[0] = "X-PPD-SIGN:S+GZ4Cx08eGWUWAEzEVex4FdGX9aHLcDb1sVcMvvQ2IlHw0d6nviFqB1yv6rIOxCo+tRtTtXU89AoUg17+t6IXy1gsesJiD8pvv7MJCINXcNd15Kg1cGwviKfYnQtvcupKZJM62m5pSTBWXUGdAtymZmR2Wl/eQmSbNEo0pR7bg=\r\n"
                    result = yield self.loop.request(self.openapi_host, self.loan_url, headers, data)
                    if result != '{"LoanInfos":[],"Result":1,"ResultCode":null,"ResultMessage":"查询成功"}' and 'LoanInfos' in result:
                        loan_infos = json.loads(result)['LoanInfos']
                        if len(loan_infos) == len(bid_listing_ids_ten):
                            for loan_info in loan_infos:
                                ListingId = loan_info['ListingId']
                                bid_info = {
                                        'ListingId': ListingId,
                                        'BidAmount': lists_dict[ListingId],
                                        'BidTime': str(date.today())
                                    }
                                self.bid_list_dict[user_name].append(bid_info)
                                self.all_bids_dict[ListingId] = loan_info
                            break
                    yield self.loop.await_sleep(10)
                yield self.loop.await_sleep(10)

    def get_loan_list(self, url, headers, data):
        listing_time = time.time()
        resp = yield self.loop.request(self.invest_host, url, headers, data)
        if resp:
            try:
                dataList = json.loads(resp)['resultContent']['dataList']
            except:
                print('网页散标列表错误', resp)
            else:
                listing_ids = [loan_info["listingId"] for loan_info in dataList if not self.sbf.add(loan_info["listingId"])]
                #print(listing_ids)
                self.loop.add_future(self.get_loan_infos(listing_ids, listing_time))

    def get_listing_ids(self, data):
        listing_time = time.time()
        #timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(listing_time))
        timestamp = str(datetime.utcnow() + timedelta(seconds=1))[:23]
        #timestamp = str(datetime.utcnow())[:23]
        #self.headers[0] = sign
        self.headers[1] = f"X-PPD-TIMESTAMP:{timestamp}\r\n"
        self.headers[2] = f"X-PPD-TIMESTAMP-SIGN:{self.rsa_sign(appid + timestamp).decode()}\r\n"
        result = yield self.loop.request(self.openapi_host, self.listing_url, self.headers, data, timeout=self.timeout)
        #print('列表', listing_time, time.time(), result)
        if result != '{"LoanInfos":[],"Result":1,"ResultCode":null,"ResultMessage":"查询成功"}' and result != self.txt:
            if 'LoanInfos' in result:
                self.txt = result
                loan_infos = json.loads(result)['LoanInfos']
                listing_ids = []
                for loan_info in loan_infos:
                    ListingId = loan_info["ListingId"]
                    if not self.sbf.add(ListingId):
                        if loan_info['CreditCode'] != 'AA':
                            listing_ids.append(ListingId)
                        else:
                            if loan_info["Rate"] >= self.AA_rate_min:
                                for policy_name, policy_info in self.AA_policy_infos.items():
                                    if loan_info["Rate"] >= policy_info['info']['interval']['CurrentRate'][0]:
                                        loan_info["CurrentRate"] = loan_info.pop("Rate")
                                        for user_name in self.sys_policy_users[policy_name]:
                                            self.bid('系统策略', policy_name, loan_info, user_name, self.bid_enable_users[user_name], listing_time, listing_time)
                #listing_ids = [loan_info["ListingId"] for loan_info in loan_infos if not self.sbf.add(loan_info["ListingId"]) and loan_info['CreditCode'] != 'AA']
                for i in range(0, len(listing_ids), 10):  # 以 10 个元素的长度分割 listing_ids
                   self.loop.add_future(self.get_loan_infos(listing_ids[i:i+10], listing_time))
            else:
                if result:
                    print(result)

    def get_listing_ids_sign(self, sign, data):
        #listing_time = time.time()

        #timestamp = time.strftime('%Y-%m-%d %H:%M:%S', time.gmtime(listing_time))
        timestamp = str(datetime.utcnow() + timedelta(seconds=1))[:23]
        #timestamp = str(datetime.utcnow())[:23]
        self.headers[0] = sign
        self.headers[1] = f"X-PPD-TIMESTAMP:{timestamp}\r\n"
        self.headers[2] = f"X-PPD-TIMESTAMP-SIGN:{self.rsa_sign(appid + timestamp).decode()}\r\n"

        #listing_time = time.time()
        listing_time = 1
        result = yield self.loop.request(self.openapi_host, self.listing_url, self.headers, data, timeout=self.timeout)
        #print('列表', listing_time, time.time(), result)
        if result != '{"LoanInfos":[],"Result":1,"ResultCode":null,"ResultMessage":"查询成功"}' and result != self.txt:
            if 'LoanInfos' in result:
                self.txt = result
                loan_infos = json.loads(result)['LoanInfos']
                listing_ids = []
                for loan_info in loan_infos:
                    ListingId = loan_info["ListingId"]
                    if not self.sbf.add(ListingId):
                        if loan_info['CreditCode'] != 'AA':
                            listing_ids.append(ListingId)
                        else:
                            if loan_info["Rate"] >= self.AA_rate_min:
                                for policy_name, policy_info in self.AA_policy_infos.items():
                                    if loan_info["Rate"] >= policy_info['info']['interval']['CurrentRate'][0]:
                                        for user_name in self.sys_policy_users[policy_name]:
                                            self.bid('系统策略', policy_name, loan_info, user_name, self.bid_enable_users[user_name], listing_time, listing_time)
                #listing_ids = [loan_info["ListingId"] for loan_info in loan_infos if not self.sbf.add(loan_info["ListingId"]) and loan_info['CreditCode'] != 'AA']
                for i in range(0, len(listing_ids), 10):  # 以 10 个元素的长度分割 listing_ids
                   self.loop.add_future(self.get_loan_infos(listing_ids[i:i+10], listing_time))
            else:
                if result:
                    print(result)

    def get_loan_infos(self, listing_ids, listing_time):
        #loan_time = time.time()
        loan_time = 1

        data = '{"ListingIds":%s}' % listing_ids
        while 1:
            headers = self.headers.copy()
            headers[0] = "X-PPD-SIGN:S+GZ4Cx08eGWUWAEzEVex4FdGX9aHLcDb1sVcMvvQ2IlHw0d6nviFqB1yv6rIOxCo+tRtTtXU89AoUg17+t6IXy1gsesJiD8pvv7MJCINXcNd15Kg1cGwviKfYnQtvcupKZJM62m5pSTBWXUGdAtymZmR2Wl/eQmSbNEo0pR7bg=\r\n"
            result = yield self.loop.request(self.openapi_host, self.loan_url, headers, data, timeout=self.timeout)
            #print('详情',result)
            if 'LoanInfos' in result:
                if result != '{"LoanInfos":[],"Result":1,"ResultCode":null,"ResultMessage":"查询成功"}':
                    loan_infos = json.loads(result)['LoanInfos']
                    self.match(loan_infos, listing_time, loan_time)
                    break
                else:
                    continue
            else:
                break

    def match(self, loan_infos, listing_time, loan_time):
        for loan_info in loan_infos:
            FirstSuccessBorrowTime = loan_info.get('FirstSuccessBorrowTime')
            LastSuccessBorrowTime = loan_info.get('LastSuccessBorrowTime')

            if FirstSuccessBorrowTime:
                try:
                    RegisterTimeDT = datetime.strptime(loan_info['RegisterTime'][:10],'%Y-%m-%d')  # 转换为 datetime 对象
                except:
                    print('注册时间为空')
                    return
                FirstSuccessBorrowTimeDT = datetime.strptime(FirstSuccessBorrowTime[:10],'%Y-%m-%d')
                FirstRegTime = (FirstSuccessBorrowTimeDT - RegisterTimeDT).days
                loan_info['FirstRegTime'] = FirstRegTime
            else:
                loan_info['FirstRegTime'] = -1

            if LastSuccessBorrowTime:
                LastSuccessBorrowTimeDT = datetime.strptime(LastSuccessBorrowTime[:10],'%Y-%m-%d')
                NowLastTime = (datetime.now() - LastSuccessBorrowTimeDT).days
                loan_info['NowLastTime'] = NowLastTime
            else:
                loan_info['NowLastTime'] = -1

            Amount = loan_info["Amount"]
            OwingAmount = loan_info["OwingAmount"]
            SuccessCount = loan_info["SuccessCount"]
            WasteCount = loan_info["WasteCount"]
            NormalCount = loan_info["NormalCount"]
            OverdueLessCount = loan_info["OverdueLessCount"]
            OverdueMoreCount = loan_info["OverdueMoreCount"]
            HighestPrincipal = loan_info.get("HighestPrincipal", 0)
            HighestDebt = loan_info["HighestDebt"]
            extend_match_args = {
                "Debt": OwingAmount + Amount,
                "RatioAmountHighest": Amount / (HighestPrincipal + 0.001),
                "RatioOwingAmount": OwingAmount / Amount,
                "RatioOwingAmountHighestDebt": OwingAmount / (HighestDebt + 0.001),
                "RatioDebtHighest": (OwingAmount + Amount) / (HighestDebt + 0.001),
                "RatioTotalPaySuccessLoan": (NormalCount + OverdueLessCount + OverdueMoreCount) / (SuccessCount + 0.001),
                "RatioTotalOverdueNormalPay": (OverdueLessCount + OverdueMoreCount) / (NormalCount + 0.001),
                "RatioWasteNormalPay": WasteCount / (NormalCount + 0.001)
            }

            loan_info_merge = dict(loan_info, **extend_match_args)

            for user_name, user_info in self.bid_enable_users.items():
                for policy_name, policy_info in user_info['Policy']['自选策略'].items():
                    if self.judge(policy_name, policy_info['info'], loan_info_merge):
                        self.bid('自选策略', policy_name, loan_info, user_name, user_info, listing_time, loan_time)
                        break

    def judge(self, policy_name, policy_info, loan_info_merge):
        for key, value in policy_info['in'].items():
            if loan_info_merge[key] not in value:
                #print(f"编号 {loan_info_merge['ListingId']} {key} 不匹配策略 {policy_name} 当前值={loan_info_merge[key]} 策略值={value}")
                return False
        for key, value in policy_info['interval'].items():
            if not value[0] <= loan_info_merge[key] <= value[1]:
                #print(f"编号 {loan_info_merge['ListingId']} {key} 不匹配策略 {policy_name} 当前值={loan_info_merge[key]} 策略值={value}")
                return False
        for key, value in policy_info['is'].items():
            if loan_info_merge[key] != value:
                #print(f"编号 {loan_info_merge['ListingId']} {key} 不匹配策略 {policy_name} 当前值={loan_info_merge[key]} 策略值={value}")
                return False
        return True

    def bid(self, policy_type, policy_name, loan_info, user_name, user_info, listing_time, loan_time):
        #bid_time = time.time()
        bid_time = 1

        ListingId = loan_info["ListingId"]
        BidAmount = user_info['Policy'][policy_type][policy_name]['BidAmount']  # 投额
        headers = self.headers.copy()
        headers[0] = "X-PPD-SIGN:WuDVQbyd2iwhyqoPFvRygEExBZiQ2Iglozv2cZ+G/KaDXGrG0EnRv60wjQh2uOWyBBys5LGCV6PngVoBTXH8Iz08Jrcr5FDtvxoxCEvf5oZUEexPNiwePNxm6gqW0cZaMd8ctuiP2lB4DxFMQarSMP1Vp3HV5GcijbZExCz/je8=\r\n"
        data = '{"ListingId": %s,"Amount": %s,"UseCoupon":"true"}' % (ListingId, BidAmount)
        for bind_name in user_info['Policy'][policy_type][policy_name]['AuthorizeBinding']:
            access_token = f"X-PPD-ACCESSTOKEN:{user_info['AuthorizeBinding'][bind_name]['AccessToken']}\r\n"
            self.loop.add_future(self._bid(user_name, bind_name, policy_name, ListingId, loan_info, headers, data, access_token))

    def _bid(self, user_name, bind_name, policy_name, ListingId, loan_info, headers, data, access_token):
        resp = yield self.loop.request(self.openapi_host, self.bid_url, headers, data, access_token=access_token)
        if resp:
            res = json.loads(resp)
            result = res.get("Result")
            if result == 9999:
                BidTime = datetime.now()
                OrderId = res["OrderId"]
                #self.logger(f"\033[43;1m处理 账号 {user_name} | {bind_name} 编号 {ListingId} 订单 {OrderId} 列表 {listing_time} 详情 {loan_time} 投标 {bid_time}\033[0m")
                self.logger(f"\033[43;1m处理 账号 {user_name} | {bind_name} 编号 {ListingId} 订单 {OrderId}\033[0m")
                self.process += 1
                # 延迟查询
                yield self.loop.await_sleep(240)
                yield from self.get_bid(OrderId, ListingId, user_name, bind_name, loan_info, policy_name, BidTime, access_token)
            # 小于等于 256 的数字 python 优化为同一对象 故采用 == 来判断 以更快速的运行 大于 256 必须采用 ==
            elif result == 4001:
                # 余额不足设置余额为 1 待下一次轮询时从拍拍贷获取余额 以判断是否放弃投标
                self.logger(f"\033[46;1m账号 {user_name} | {bind_name} 拍拍贷余额不足\033[0m")
                # if self.alert_weixin.get(user_name) and self.alert_weixin[user_name]['拍拍贷余额不足'] != str(date.today()):
                    # self.ifeige_template_id['余额不足']['uid'] = self.alert_weixin[user_name]['uid']
                    # self.ifeige_template_id['余额不足']['data']['first']['value'] = '拍拍贷余额不足'
                    # self.ifeige_template_id['余额不足']['data']['keyword1']['value'] = user_name
                    # self.ifeige_template_id['余额不足']['data']['keyword2']['value'] = '小于策略投额'
                    # self.loop.add_future(self.alert_ifeige(user_name, '拍拍贷余额不足', json.dumps(self.ifeige_template_id['余额不足'])))
                if self.repeated_reminders[user_name][bind_name]['Sufficient_Balance']:
                    self.del_bind_user(user_name, bind_name)
                    self.Balance_Authorized.add((user_name, bind_name, 'Balance'))
                    self.repeated_reminders[user_name][bind_name]['Sufficient_Balance'] = False
            elif result == 1002:
                self.logger(f"\033[46;1m账号 {user_name} | {bind_name} 第三方授权过期\033[0m")
                if self.repeated_reminders[user_name][bind_name]['Authorized']:
                    self.del_bind_user(user_name, bind_name, user_type='All')
                    self.Balance_Authorized.add((user_name, bind_name, 'Authorized'))
                    self.repeated_reminders[user_name][bind_name]['Authorized'] = False

                    user = Users.query.filter_by(Name=user_name).first()
                    bid_policy = json.loads(user.Policy)
                    debt_policy = json.loads(user.DebtPolicy)
                    authorize_binding_dict = json.loads(user.AuthorizeBinding)
                    authorize_binding_dict[bind_name]['Authorized'] = 0
                    for policy_dict, policy_class in ((bid_policy, 'Bid'), (debt_policy, 'Debt')):
                        for policy_type, policys in policy_dict.items():
                            for policy_name, policy_info in policys.items():
                                try:
                                    policy_info['AuthorizeBinding'].remove(bind_name)
                                except:
                                    pass
                        if policy_class == 'Bid':
                            user.Policy = str(policy_dict).replace("'",'"')
                        else:
                            user.DebtPolicy = str(policy_dict).replace("'",'"')
                    user.AuthorizeBinding = str(authorize_binding_dict).replace("'",'"')
                    db.session.commit()
            elif result in [3002, 3003]:
                self.logger(f"\033[46;1m账号 {user_name} | {bind_name} 累计投标金额过大\033[0m")
            else:
                #self.logger(f'\033[45;1m响应 账号 {user_name} | {bind_name} 列表 {listing_time} 详情 {loan_time} 投标 {bid_time}\033[0m {resp}')
                self.error += 1

    def get_bid(self, OrderId, ListingId, user_name, bind_name, loan_info, policy_name, BidTime, access_token):
        data = '{"orderId":"%s","listingId":%s}' % (OrderId, ListingId)
        sign = f"X-PPD-SIGN:{self.rsa_sign('orderId'+OrderId).decode()}\r\n"
        while 1:
            headers = self.headers.copy()
            headers[0] = sign
            resp = yield self.loop.request(self.openapi_host, self.query_bid_url, headers, data, access_token=access_token)
            if resp:
                break
            else:
                self.logger(f'\033[41;1m重试 账号 {user_name} | {bind_name} 编号 {ListingId} 订单 {OrderId}\033[0m 响应为空，120秒后重试')
                yield self.loop.await_sleep(120)
                bid_user = Users.query.filter(Users.Name == user_name).first()
                access_token = f"X-PPD-ACCESSTOKEN:{json.loads(bid_user.AuthorizeBinding)[bind_name]['AccessToken']}\r\n"
        query_bid_res = json.loads(resp)
        if query_bid_res.get('result') == 1:
            #self.logger(f'\033[42;1m成功 账号 {user_name} | {bind_name}\033[0m {resp}')
            self.success += 1
            self.process -= 1
            participation_amount = query_bid_res['resultContent']["participationAmount"]
            bid_cost = Decimal(participation_amount) * self.bid_cost_rate  # 计算应扣代币金额(费率在全局变量里设置)
            self.cost_cc(user_name, bid_cost)
            bid_info = {
                    'ListingId': ListingId,
                    'PolicyName': policy_name,
                    'ParticipationAmount': participation_amount,
                    'BidTime': BidTime,
                    'User': bind_name
                }  # SQLite date 类型，只接受 Python date 对象
            self.b2r[user_name].append(bid_info)
            self.all_bids_dict[ListingId] = loan_info
        elif query_bid_res.get('result') == 2:
            while 1:
                self.logger(f'\033[41;1m重试 账号 {user_name} | {bind_name} 编号 {ListingId} 订单 {OrderId}\033[0m 处理中，120秒后重试')
                yield self.loop.await_sleep(120)
                bid_user = Users.query.filter(Users.Name == user_name).first()
                try:
                    access_token = f"X-PPD-ACCESSTOKEN:{json.loads(bid_user.AuthorizeBinding)[bind_name]['AccessToken']}\r\n"
                except:
                    pass
                else:
                    self.loop.add_future(self.get_bid(OrderId, ListingId, user_name, bind_name, loan_info, policy_name, BidTime, access_token))
                    break
        else:
            #self.logger(f'\033[41;1m失败 账号 {user_name} | {bind_name} 订单 {OrderId}\033[0m {resp}')
            if '令牌不存在' in resp:
                while 1:
                    self.logger(f'\033[41;1m重试 账号 {user_name} | {bind_name} 编号 {ListingId} 订单 {OrderId}\033[0m 令牌不存在，300秒后重试')
                    yield self.loop.await_sleep(300)
                    bid_user = Users.query.filter(Users.Name == user_name).first()
                    try:
                        access_token = f"X-PPD-ACCESSTOKEN:{json.loads(bid_user.AuthorizeBinding)[bind_name]['AccessToken']}\r\n"
                    except:
                        pass
                    else:
                        self.loop.add_future(self.get_bid(OrderId, ListingId, user_name, bind_name, loan_info, policy_name, BidTime, access_token))
                        break
            else:
                self.fail += 1
                self.process -= 1

    def get_debt_market(self):
        self.wait_debt = False
        sleep_retry_debt = int(self.waiting_time_for_rerty//self.request_interval_market)  # 失败重试前市场延时次数

        self.data_debt = {"pageIndex":1,"pageSize":10,"category":1,"currentLevelList":None,"levelList":None,"lastDueDayList":None,"overDueDayList":None,"monthGroupList":None,"rate":self.AA_debt_rate_min,"minAmount":"","maxAmount":"","sortType":None,"minPastDueNumber":"","maxPastDueNumber":"","minPastDueDay":"","maxPastDueDay":"","minAllowanceRadio":"","maxAllowanceRadio":""}  # 1，赔标
        self.data_debt_json = json.dumps(self.data_debt)
        self.data_debt_json_original = self.data_debt_json

        while 1:
            for index in range(720):
                for i in range(1,21):
                    for index in range(5):
                        yield self.loop.add_future(self._get_debt_market())
                    self.viewBar.view_bar(i, 20, success=self.success_debt, fail=self.fail_debt, process=self.process_debt, error=self.error_debt, type_from='\033[45;1m市场')
                self.viewBar.new_line()
                if self.wait_debt:
                    self.logger(f'\033[41;1m访问过频，市场刷新失败，{self.waiting_time_for_rerty} 秒后自动重试\033[0m')
                    for i in range(sleep_retry_debt):
                        yield
                    self.wait_debt = False

    def _get_debt_market(self):
        res = yield self.loop.request(self.transfer_host, self.get_buy_list_url, self.headers_debt, self.data_debt_json)
        #print('债权市场', time.time() ,res)
        if res:
            try:
                res = json.loads(res, strict=False)  # 偶尔出现 json.decoder.JSONDecodeError: Expecting value: line 1 column 1 (char 0) 错误，故做容错处理
            except:
                return
            if res.get('result') is 1:
                items = res['resultContent']['items']
                if items:
                    not_be_filtered = True
                    for item in items:
                        if not self.sbf.add(9000000000+item['debtDealId']):
                            for policy_name, policy_info in self.AA_debt_policy_infos.items():
                                if item['currentRate'] >= policy_info['info']['interval']['CurrentRate'][0]:
                                    user_list = self.sys_debt_policy_users[policy_name]
                                    if user_list:
                                        user_name = user_list.pop(0)
                                        binding_list = self.debt_enable_users[user_name]['Policy']['系统策略'][policy_name]['AuthorizeBinding']
                                        if binding_list:
                                            bind_name = binding_list.pop(0)
                                            #self.logger('市场开始购买')
                                            self.loop.add_future(self.buy_debt(policy_name, user_name, bind_name, item['listingId'], item['debtDealId'], item['currentRate'], item['priceForSale'], is_market=True))
                                            binding_list.append(bind_name)
                                            user_list.append(user_name)
                                            break
                                        else:
                                            user_list.insert(0, user_name)
                        else:
                            not_be_filtered = False
                    if len(items) is 10 and not_be_filtered:
                        self.data_debt["pageIndex"] = self.data_debt["pageIndex"] + 1
                        self.data_debt_json = json.dumps(self.data_debt)
                    else:
                        self.data_debt["pageIndex"] = 1
                        self.data_debt_json = self.data_debt_json_original
            elif res.get('result') == 409:
                self.wait_debt = True
            else:
                self.logger(f'市场响应异常，{res}')
        else:
            if res is False:
                self.logger('市场管道错误，自动重试')
                self.loop.add_future(self._get_debt_market())

    def get_debt_api(self):
        self.wait_debt_api = False
        sleep_retry_api = int(self.waiting_time_for_rerty//self.request_interval_api)  # 失败重试前接口延时次数
        back_seconds = 15  # 列表回溯秒数
        #self.debt_api_page = 1

        #self.data_api = '{"PageIndex": %s, "Levels":"AA"}' % self.debt_api_page

        while 1:
            for i in range(1,61):
                yield self.loop.add_future(self._get_debt_api(back_seconds))
                self.viewBar.view_bar(i, 60, success=self.success_debt_api, fail=self.fail_debt_api, process=self.process_debt_api, error=self.error_debt_api, type_from='\033[46;1m接口')
            self.viewBar.new_line()
            if self.wait_debt_api:
                self.logger(f'\033[41;1m访问过频，接口刷新失败，{self.waiting_time_for_rerty} 秒后自动重试\033[0m')
                for i in range(sleep_retry_api):
                    yield
                self.wait_debt_api = False
                #self.debt_api_page = 1

    def _get_debt_api(self, back_seconds):
        headers = self.headers.copy()
        start_date_time = str(datetime.now() - timedelta(seconds=back_seconds))[:19]
        headers[0] = f"X-PPD-SIGN:{self.rsa_sign('StartDateTime' + start_date_time).decode()}\r\n"
        data_api = '{"PageIndex": 1, "StartDateTime":"%s", "Levels":"AA"}' % start_date_time
        #headers[0] = "X-PPD-SIGN:S+GZ4Cx08eGWUWAEzEVex4FdGX9aHLcDb1sVcMvvQ2IlHw0d6nviFqB1yv6rIOxCo+tRtTtXU89AoUg17+t6IXy1gsesJiD8pvv7MJCINXcNd15Kg1cGwviKfYnQtvcupKZJM62m5pSTBWXUGdAtymZmR2Wl/eQmSbNEo0pR7bg=\r\n"
        res = yield self.loop.request(self.openapi_host, self.buy_list_url, headers, data_api)
        #res = yield self.loop.request(self.openapi_host, self.buy_list_url, headers, '{"PageIndex": %s, "Levels":"AA"}' % self.debt_api_page)
        #print('债权接口', time.time() ,res)
        if res:
            res = json.loads(res, strict=False)
            if res.get('Result') is 1:
                DebtInfos = res['DebtInfos']
                if DebtInfos:
                    next_debt_api_page = True
                    for DebtInfo in DebtInfos:
                        #if not self.sbf.add(DebtInfo['DebtdealId']) and DebtInfo['CreditCode'] == 'AA' and DebtInfo['PriceforSaleRate'] >= self.AA_debt_rate_min:
                        if self.sbf.add(9000000000+DebtInfo['DebtdealId']):
                            next_debt_api_page = False
                        else:
                            if DebtInfo['PriceforSaleRate'] >= self.AA_debt_rate_min:
                                for policy_name, policy_info in self.AA_debt_policy_infos.items():
                                    if DebtInfo['PriceforSaleRate'] >= policy_info['info']['interval']['CurrentRate'][0]:
                                        user_list = self.sys_debt_policy_users[policy_name]
                                        if user_list:
                                            user_name = user_list.pop(0)
                                            binding_list = self.debt_enable_users[user_name]['Policy']['系统策略'][policy_name]['AuthorizeBinding']
                                            if binding_list:
                                                bind_name = binding_list.pop(0)
                                                #self.logger('接口开始购买')
                                                self.loop.add_future(self.buy_debt(policy_name, user_name, bind_name, DebtInfo['ListingId'], DebtInfo['DebtdealId'], DebtInfo['PriceforSaleRate'], DebtInfo['PriceforSale']))
                                                binding_list.append(bind_name)
                                                user_list.append(user_name)
                                                break
                                            else:
                                                user_list.insert(0, user_name)
                    # if next_debt_api_page:
                        # self.debt_api_page += 1
                    # else:
                        # self.debt_api_page = 1
            elif res.get('message'):
                self.wait_debt_api = True
            else:
                self.logger(f'接口响应异常，{res}')
        # else:
            # self.logger('债权接口响应为空')

    def buy_debt(self, policy_name, user_name, bind_name, listing_id, debt_deal_Id, price_for_sale_rate, price_for_sale, is_market=False):
        access_token = f"X-PPD-ACCESSTOKEN:{self.debt_enable_users[user_name]['AuthorizeBinding'][bind_name]['AccessToken']}\r\n"
        headers = self.headers.copy()
        headers[0] = "X-PPD-SIGN:S+GZ4Cx08eGWUWAEzEVex4FdGX9aHLcDb1sVcMvvQ2IlHw0d6nviFqB1yv6rIOxCo+tRtTtXU89AoUg17+t6IXy1gsesJiD8pvv7MJCINXcNd15Kg1cGwviKfYnQtvcupKZJM62m5pSTBWXUGdAtymZmR2Wl/eQmSbNEo0pR7bg=\r\n"
        res = yield self.loop.request(self.openapi_host, self.buy_debt_url, headers, '{"DebtDealId":%d}' % debt_deal_Id, access_token=access_token)
        if res:
            res = json.loads(res)
            if res.get("Result") == 0:
                #self.logger(f'已完成购买，请稍后查看！债权编号：{debt_deal_Id}')
                self.logger(f"\033[43;1m成功 账号 {user_name} | {bind_name} 债编 {debt_deal_Id}\033[0m {res}")
                BuyDate = str(date.today())
                if is_market:
                    self.process_debt += 1
                else:
                    self.process_debt_api += 1
                self._buy_debt(policy_name, user_name, bind_name, listing_id, debt_deal_Id, price_for_sale_rate, price_for_sale, BuyDate, is_market)
            elif res.get("Result") == 1001:
                OrderId = res['OrderId']
                self.logger(f"\033[43;1m处理 账号 {user_name} | {bind_name} 债编 {debt_deal_Id} 订单 {OrderId}\033[0m")
                BuyDate = str(date.today())
                if is_market:
                    self.process_debt += 1
                else:
                    self.process_debt_api += 1
                yield self.loop.await_sleep(120)
                yield from self.get_debt(policy_name, user_name, bind_name, listing_id, debt_deal_Id, price_for_sale_rate, price_for_sale, BuyDate, is_market, OrderId, access_token)
            else:
                if is_market:
                    self.error_debt += 1
                else:
                    self.error_debt_api += 1
        else:
            if res is False:
                self.logger('购买管道错误，自动重试')
                self.loop.add_future(self.buy_debt(policy_name, user_name, listing_id, debt_deal_Id, price_for_sale_rate, price_for_salee, is_market))

    def _buy_debt(self, policy_name, user_name, bind_name, listing_id, debt_deal_Id, price_for_sale_rate, price_for_sale, BuyDate, is_market):
        price_for_sale = float(price_for_sale)
        if price_for_sale_rate < self.debt_cost_rate_min:
            debt_cost_rate = self.debt_cost_rate_base
        elif self.debt_cost_rate_min <= price_for_sale_rate <= self.debt_cost_rate_max:
            debt_cost_rate = self.debt_cost_rate[int(price_for_sale_rate)]
        else:
            debt_cost_rate = self.debt_cost_rate_base_double
        debt_cost = Decimal(price_for_sale) * debt_cost_rate  # 计算应扣代币金额
        self.cost_cc(user_name, debt_cost)
        debt_info = {
            'DebtdealId': debt_deal_Id,
            'ListingId': listing_id,
            'PolicyName': policy_name,
            'PriceForSaleRate':price_for_sale_rate,
            'PriceForSale': price_for_sale,
            'BuyDate': BuyDate,
            'User': bind_name
        }  # SQLite date 类型，只接受 Python date 对象
        self.d2r[user_name].append(debt_info)
        #self.logger(f'债权利率 {price_for_sale_rate}，价格 {price_for_sale}，扣费 {debt_cost_rate}:{debt_cost}')
        if is_market:
            self.success_debt += 1
            self.process_debt -= 1
        else:
            self.success_debt_api += 1
            self.process_debt_api -= 1

    def get_debt(self, policy_name, user_name, bind_name, listing_id, debt_deal_Id, price_for_sale_rate, price_for_sale, BuyDate, is_market, OrderId, access_token):
        data = '{"orderId":"%s"}' % OrderId
        sign = f"X-PPD-SIGN:{self.rsa_sign('orderId'+OrderId).decode()}\r\n"
        while 1:
            headers = self.headers.copy()
            headers[0] = sign
            resp = yield self.loop.request(self.openapi_host, self.query_order_url, headers, data, access_token=access_token)
            if resp:
                break
            else:
                self.logger(f'\033[41;1m重试 账号 {user_name} | {bind_name} 债编 {debt_deal_Id} 订单 {OrderId}\033[0m 响应为空，120秒后重试')
                yield self.loop.await_sleep(120)
                bid_user = Users.query.filter(Users.Name == user_name).first()
                access_token = f"X-PPD-ACCESSTOKEN:{json.loads(bid_user.AuthorizeBinding)[bind_name]['AccessToken']}\r\n"
        query_debt_res = json.loads(resp)
        if query_debt_res.get('code') == 1:
            self._buy_debt(policy_name, user_name, bind_name, listing_id, debt_deal_Id, price_for_sale_rate, price_for_sale, BuyDate, is_market)
        elif query_debt_res.get('code') == 1001:
            while 1:
                self.logger(f'\033[41;1m重试 账号 {user_name} | {bind_name} 债编 {debt_deal_Id} 订单 {OrderId}\033[0m 购买中，120秒后重试')
                yield self.loop.await_sleep(120)
                bid_user = Users.query.filter(Users.Name == user_name).first()
                try:
                    access_token = f"X-PPD-ACCESSTOKEN:{json.loads(bid_user.AuthorizeBinding)[bind_name]['AccessToken']}\r\n"
                except:
                    pass
                else:
                    self.loop.add_future(self.get_debt(policy_name, user_name, listing_id, debt_deal_Id, price_for_sale_rate, price_for_sale, BuyDate, is_market, OrderId, access_token))
                    break
        else:
            #self.logger(f'\033[41;1m失败 账号 {user_name} | {bind_name} 订单 {OrderId}\033[0m {resp}')
            if '令牌不存在' in resp:
                while 1:
                    self.logger(f'\033[41;1m重试 账号 {user_name} | {bind_name} 债编 {debt_deal_Id} 订单 {OrderId}\033[0m 令牌不存在，300秒后重试')
                    yield self.loop.await_sleep(300)
                    bid_user = Users.query.filter(Users.Name == user_name).first()
                    try:
                        access_token = f"X-PPD-ACCESSTOKEN:{json.loads(bid_user.AuthorizeBinding)[bind_name]['AccessToken']}\r\n"
                    except:
                        pass
                    else:
                        self.loop.add_future(self.get_debt(policy_name, user_name, listing_id, debt_deal_Id, price_for_sale_rate, price_for_sale, BuyDate, is_market, OrderId, access_token))
                        break
            else:
                if is_market:
                    self.fail_debt += 1
                    self.process_debt -= 1
                else:
                    self.fail_debt_api += 1
                    self.process_debt_api -= 1

    def cost_cc(self, user_name, cost):
        self.user_cc[user_name]['CC'] = self.user_cc[user_name]['CC'] - cost  # 计费
        # 删除猫币不足用户
        if self.user_cc[user_name]['CC'] < self.cc_min:
            self.logger(f"\033[46;1m账号 {user_name} 猫币不足， 将被暂停投标\033[0m")
            if self.alert_weixin.get(user_name) and self.alert_weixin[user_name]['拍拍猫猫币不足'] != str(date.today()):
                self.ifeige_template_id['余额不足']['uid'] = self.alert_weixin[user_name]['uid']
                self.ifeige_template_id['余额不足']['data']['first']['value'] = '拍拍猫猫币不足'
                self.ifeige_template_id['余额不足']['data']['keyword1']['value'] = user_name
                self.ifeige_template_id['余额不足']['data']['keyword2']['value'] = str(self.user_cc[user_name]['CC'].quantize(Decimal('0.0')))
                self.loop.add_future(self.alert_ifeige(user_name, '拍拍猫猫币不足', json.dumps(self.ifeige_template_id['余额不足'])))
            self.del_user(user_name, user_type='All')

    def del_user(self, user_name, user_type='Bid'):
        if user_type == 'Bid':
            self._del_user(user_name, self.bid_enable_users, self.sys_policy_users)
        elif user_type == 'Debt':
            self._del_user(user_name, self.debt_enable_users, self.sys_debt_policy_users)
        else:
            self._del_user(user_name, self.bid_enable_users, self.sys_policy_users)
            self._del_user(user_name, self.debt_enable_users, self.sys_debt_policy_users)

    def _del_user(self, user_name, enable_users, sys_policy_users):
        try:
            del enable_users[user_name]
        except:
            pass
        for policy, users in sys_policy_users.items():
            try:
                users.remove(user_name)
            except:
                pass

    def del_bind_user(self, user_name, bind_name, user_type='Bid'):
        if user_type == 'Bid':
            if user_name in self.bid_enable_users:
                self._del_bind_user(user_name, bind_name, self.bid_enable_users, self.sys_policy_users)
        elif user_type == 'Debt':
            if user_name in self.debt_enable_users:
                self._del_bind_user(user_name, bind_name, self.debt_enable_users, self.sys_debt_policy_users)
        else:
            if user_name in self.bid_enable_users:
                self._del_bind_user(user_name, bind_name, self.bid_enable_users, self.sys_policy_users)
            if user_name in self.debt_enable_users:
                self._del_bind_user(user_name, bind_name, self.debt_enable_users, self.sys_debt_policy_users)

    def _del_bind_user(self, user_name, bind_name, enable_users, sys_policy_users):
        all_AuthorizeBinding_is_none = True
        for policy_type in ['自选策略','系统策略']:
            type_AuthorizeBinding_is_none = True
            del_policy_name = []
            for policy_name, policy_info in enable_users[user_name]['Policy'][policy_type].items():
                try:
                    policy_info['AuthorizeBinding'].remove(bind_name)
                except:
                    pass
                if policy_info['AuthorizeBinding']:
                    type_AuthorizeBinding_is_none = False
                    all_AuthorizeBinding_is_none = False
                else:
                    del_policy_name.append(policy_name)
                    if policy_type == '系统策略':
                        try:
                            sys_policy_users[policy_name].remove(user_name)
                        except:
                            pass
            if type_AuthorizeBinding_is_none:
                try:
                    del enable_users[user_name]['Policy'][policy_type]
                except:
                    pass
            else:
                for policy_name in del_policy_name:
                    try:
                        del enable_users[user_name]['Policy'][policy_type][policy_name]
                    except:
                        pass
        if all_AuthorizeBinding_is_none:
            try:
                del enable_users[user_name]
            except:
                pass

    def alert_ifeige(self, user_name, title, data):
        while 1:
            res = yield self.loop.request(self.ifeige_host, self.ifeige_send_user_url, self.ifeige_headers, data, is_http=True)
            if res:
                result = json.loads(res)
                if result.get('code') == 200:
                    self.alert_weixin[user_name][title] = str(date.today())
                    user = Users.query.filter_by(Name=user_name).first()
                    user.AlertWeiXin = str(self.alert_weixin[user_name]).replace('\'', '\"').replace(' ','')
                    db.session.commit()
                    break
                elif result.get('code') == 10010:
                    self.logger(f"\033[46;1m信息发送对象不存在！\033[0m{res}")
                    user = Users.query.filter_by(Name=user_name).first()
                    user.AlertWeiXin = ''
                    db.session.commit()
                    del self.alert_weixin[user_name]
                    break
            self.logger(f"\033[46;1m信息发送失败，600秒后重试！\033[0m{res}")
            yield self.loop.await_sleep(600)

    def get_over_due(self):
        bid_lists_split_len = 120
        self.list_black, self.list_pay_off = [], []
        self.futures_running = []
        self.listing_id_filter = {}

        today = date.today()
        yesterday = today - timedelta(days = 1)
        overdue_update_date = yesterday
        while 1:
            if today > overdue_update_date:
                print(f'开始获取今日逾期数据')
                overdue_update_date = date.today()
                get_over_due_users = Users.query.filter(Users.Authorized != 0, Users.CC >= self.cc_min, Users.GetOverDueTimes > 0)
                for get_over_due_user in get_over_due_users:
                    user_bids = gentable(get_over_due_user.Name, '_Bids')
                    # user_bids.query.update({'Black':0})
                    # db.session.commit()
                    authorize_binding = json.loads(get_over_due_user.AuthorizeBinding)
                    binding_list = list(authorize_binding.keys())
                    bid_lists = db.session.query(user_bids).join(AllBids, user_bids.ListingId==AllBids.ListingId).filter(AllBids.CreditCode!='AA', user_bids.PayOff!=1, user_bids.User.in_(binding_list)).all()
                    len_bid_lists = len(bid_lists)
                    for i in range(0, len_bid_lists, bid_lists_split_len):
                        headers = self.headers.copy()
                        headers[0] = "X-PPD-SIGN:S+GZ4Cx08eGWUWAEzEVex4FdGX9aHLcDb1sVcMvvQ2IlHw0d6nviFqB1yv6rIOxCo+tRtTtXU89AoUg17+t6IXy1gsesJiD8pvv7MJCINXcNd15Kg1cGwviKfYnQtvcupKZJM62m5pSTBWXUGdAtymZmR2Wl/eQmSbNEo0pR7bg=\r\n"
                        for bid in bid_lists[i:i+bid_lists_split_len]:
                            if bid.ListingId in self.listing_id_filter:
                                if self.listing_id_filter[bid.ListingId].get('OverdueDays'):
                                    self.list_black.append((bid, self.listing_id_filter[bid.ListingId]['OverdueDays']))
                                else:
                                    self.list_pay_off.append(bid)
                            else:
                                yield self.loop.add_future(self._get_over_due(bid, authorize_binding, headers))
                        self.viewBar.view_bar(i+1, len_bid_lists, success=0, fail=0, process=0, error=0, type_from=f'\033[44;1m{get_over_due_user.Name}')

                        for bid, OverdueDays in self.list_black:
                            bid.Black = OverdueDays
                        for bid in self.list_pay_off:
                            bid.PayOff = 1
                        self.list_black.clear()
                        self.list_pay_off.clear()
                        db.session.commit()

                    get_over_due_user.GetOverDueTimes -= 1
                    db.session.commit()
                    self.viewBar.new_line()
                while self.futures_running:
                    yield
                for bid, OverdueDays in self.list_black:
                    bid.Black = OverdueDays
                for bid in self.list_pay_off:
                    bid.PayOff = 1
                self.list_black.clear()
                self.list_pay_off.clear()
                db.session.commit()
                self.listing_id_filter.clear()
                print(f'今日逾期数据获取完成')
            for i in range(1800 // self.request_interval_over_due):
                yield
            today = date.today()

    def _get_over_due(self, bid, authorize_binding, headers):
        self.futures_running.append(bid.ListingId)
        access_token = f"X-PPD-ACCESSTOKEN:{authorize_binding[bid.User]['AccessToken']}\r\n"
        resp = yield self.loop.request(self.openapi_host, self.repayment_url, headers, '{"ListingId":%s}' % bid.ListingId, access_token=access_token)
        if resp:  # 防止响应为空
            result = json.loads(resp)
            if result.get('ListingRepayment'):
                OverdueDays_list = []
                OwingPrincipal_zero = True
                for each in result['ListingRepayment']:
                    if not each['OwingPrincipal']:
                        continue
                    OwingPrincipal_zero = False
                    if (not each['RepayStatus'] and each['OverdueDays'] > 0) or each['RepayStatus'] is 4:
                        OverdueDays_list.append(each['OverdueDays'])
                if OwingPrincipal_zero:
                    self.listing_id_filter[bid.ListingId] = {}
                    self.listing_id_filter[bid.ListingId]['PayOff'] = 1
                    self.list_pay_off.append(bid)
                else:
                    if OverdueDays_list:
                        OverdueDays = max(OverdueDays_list)
                        self.listing_id_filter[bid.ListingId] = {}
                        self.listing_id_filter[bid.ListingId]['OverdueDays'] = OverdueDays
                        self.list_black.append((bid, OverdueDays))
        self.futures_running.remove(bid.ListingId)


class token(object):
    __slots__ = ['loop', 'all_authorize_binding_dict', 'logger']

    def __init__(self):
        self.loop = Loop()
        self.all_authorize_binding_dict = {}
        self.logger = Log(model_name=model_name, file=log_file).confile

    def refresh_all_token(self):
        #刷新所有用户令牌
        users = Users.query.all()

        url = "/oauth2/refreshtoken"
        headers = [
                "Connection:keep-alive\r\n" \
                "Cache-Control:no-cache\r\n" \
                "Accept-Language:en-US,en;q=0.8,zh-CN;q=0.6,zh;q=0.4\r\n" \
                "Content-Type:application/json;charset=utf-8\r\n"
                ]
        authorized_users = []
        for user in users:
            authorize_binding_dict = json.loads(user.AuthorizeBinding)
            self.all_authorize_binding_dict[user.Name] = authorize_binding_dict
            for binding_name, binding_info in authorize_binding_dict.items():
                if binding_info.get('State') and binding_info.get('Authorized'):
                    authorized_users.append(user)
                    self.loop.add_future(self.get_token(url, headers, binding_info, binding_name, user.Name))
        self.loop.run_until_complete()

        for user in authorized_users:
            user.AuthorizeBinding = str(self.all_authorize_binding_dict[user.Name]).replace("'",'"')

        db.session.commit()
        #logger.info('所有令牌刷新完成')

    def get_token(self, url, headers, binding_info, binding_name, user_name):
        data = '{"AppID":"%s","OpenId":"%s","RefreshToken":"%s"}' % (appid, binding_info['OpenID'], binding_info['RefreshToken'])
        result = yield self.loop.request('ac.ppdai.com', url, headers, data)
        if result:
            result = json.loads(result)
            if result.get('ErrMsg'):
                self.logger(f'{user_name} 的 {binding_name} 令牌刷新失败')
                binding_info['Authorized'] = 0
            else:
                self.update_token(binding_info, result)

    def update_token(self, binding_info, token_info):
        # 将返回的 authorize 对象反序列化成 dict 对象 {"OpenID":"xx","AccessToken":"xxx","RefreshToken":"xxx","ExpiresIn":604800}，成功得到 OpenID、AccessToken、RefreshToken、ExpiresIn
        binding_info['Authorized'] = 1
        binding_info['AccessToken'] = token_info['AccessToken']
        binding_info['RefreshToken'] = token_info['RefreshToken']
        if token_info.get('OpenID'):
            binding_info['OpenID'] = token_info['OpenID']


class ViewBar(object):
    __slots__ = ['width']

    def __init__(self):
        self.width = os.get_terminal_size().columns -31

    def view_bar(self, num=None, len_group=None, success=None, fail=None, process=None, error=None, type_from='\033[43;1m投标'):
        rate = num / len_group
        char_num = int(self.width * rate / 2)

        r = f'\r{type_from}\033[0m \033[42;1m{success}\033[0m/\033[41;1m{fail}\033[0m/\033[46;1m{process}\033[0m/\033[45;1m{error}\033[0m|{int(rate * 100)}%|{"█" * char_num}|{num}/{len_group}'

        sys.stdout.write(r)
        sys.stdout.flush

    def new_line(self):
        sys.stdout.write(f'|{datetime.now()}\r\n')


#在您的应用当中以一个显式调用 SQLAlchemy , 您只需要将如下代码放置在您应用 的模块中。Flask 将会在请求结束时自动移除数据库会话
@app.teardown_request
def shutdown_session(exception=None):
    db.session.remove()

if __name__ == '__main__':
    with app.app_context():  # 使用 app 上下文环境运行 AutoBid
        AutoBid().tasks_loop()
