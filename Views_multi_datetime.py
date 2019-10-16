#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2018/5/13 15:28
# @File    : Views.py

"""
视图模型
"""

# 模块配置_开始

import os
import sys
import time
import json
import asyncio
#import uvloop
import aiohttp
from datetime import datetime, date, timedelta

from flask import render_template, Blueprint, redirect, url_for, flash, request, make_response, send_from_directory
from flask_wtf import FlaskForm
from flask_login import LoginManager, login_user, UserMixin, logout_user, login_required, current_user
from wtforms import SubmitField, SelectMultipleField, SelectField, IntegerField, DecimalField, StringField, DateField
from wtforms.validators import NumberRange, Length, DataRequired, Optional

from sqlalchemy import func

from open_api.openapi_client import openapi_client as client
from open_api.core.rsa_client import rsa_client as rsa

from Start_multi_datetime import app, appid, login_manger, db, Log, cached
from Form import LoginForm, RegisterForm, SwitchForm, PayForm, ModifyPasswordForm
from Model_multi_datetime import Users, AllBids, gentable

from Event_Loop_Epoll_Web import Loop

import urllib3
'取消显示 InsecureRequestWarning: Unverified HTTPS request is being made. Adding certificate verification is strongly advised. See: https://urllib3.readthedocs.io/en/latest/advanced-usage.html#ssl-warnings 错误'
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# 模块配置_结束


# 变量配置_开始

account = Blueprint('account', __name__)  #蓝图
admin_list = ['xxsu']  # 管理员账户列表
max_authorize_binding = 5  # 授权位限制数
log_file = 'web.log'
model_name = 'Views'
logger = Log(model_name=model_name, file=log_file).confile

# 变量配置_结束


# 脚本正文

'''
class limit_time(object):

    """
    装饰器不仅可以是函数，还可以是类，相比函数装饰器，类装饰器具有灵活度大、高内聚、封装性等优点。
    使用类装饰器主要依靠类的__call__方法，当使用 @ 形式将装饰器附加到函数上时，就会调用此方法。
    """

    def __init__(self, time_need):
        self.time_need = time_need

    def __call__(self, func):
        async def wrapper(*args, **kwargs):
            start_time = datetime.now()
            result = await func(*args, **kwargs)
            time_difference = (datetime.now() - start_time).total_seconds()  # 时间差
            if self.time_need > time_difference:
                await asyncio.sleep(self.time_need - time_difference)
            return result
        return wrapper
'''


"""
页面路由
"""

# 用户主页
@account.route('/<name>', methods=['GET', 'POST'])
@login_required
@cached(timeout=43200)
def index(name=None):
    yesterday = str(date.today() - timedelta(days = 1))
    end_date = yesterday + ' 23:59:59'
    start_date = yesterday + ' 00:00:00'

    user_bids = gentable(current_user.Name, '_Bids')  # 动态建表
    user_bids_query_all = db.session.query(user_bids.ParticipationAmount).filter(user_bids.BidTime >= start_date, user_bids.BidTime <= end_date).all()
    total_participation_amount = sum([each[0] for each in user_bids_query_all])
    total_bid = len(user_bids_query_all)
    return render_template('main.html', admin_list=admin_list, total_participation_amount=total_participation_amount, total_bid=total_bid)

# 用户登录
@account.route('/login', methods=['GET', 'POST'])
def login():
    form = LoginForm()
    if form.validate_on_submit():
        import hashlib
        user = Users.query.filter_by(Name=form.name.data).first()
        if user and (user.Password == hashlib.md5(form.password.data.encode()).hexdigest() or user.Password == form.password.data):
        #if user and user.Password == hashlib.md5(form.password.data.encode()).hexdigest():
            login_user(user)
            logger(f'{current_user.Name} 登录')
            return redirect(url_for('account.index', name=current_user.Name))
        else:
            flash('账户或密码错误', 'danger') # 消息分类 Bootstrap 颜色代码：'success','info','warning','danger','active'，其中'active'为浅灰，'info'为淡青
    return render_template('login.html', form=form)

# 用户退出
@account.route('/logout')
@login_required
def logout():
    logger(f'{current_user.Name} 退出')
    logout_user()
    return redirect(url_for('account.login'))

# 用户注册
@account.route('/register', methods=['GET', 'POST'])
def register():
    form = RegisterForm()
    if form.validate_on_submit():
        name = form.name.data
        user = Users.query.filter_by(Name=name).first()
        if user is None:
            import hashlib
            user = Users(name=name, password=hashlib.md5(form.password.data.encode()).hexdigest())
            db.session.add(user)
            db.session.commit()

            gentable(name, '_Bids')  # 动态建表
            gentable(name, '_Debts')  # 动态建表
            #gentable(name, '_Lists')

            db.create_all()

            flash('注册成功，请登录', 'success')
            logger(f'{name} 注册')
            return redirect(url_for('account.login'))
        else:
            flash('账户已存在，请使用其他用户名进行注册', 'danger')
    return render_template('register.html', form=form)


'''
展示区路由
'''

# 策略管理
@account.route('/policy-manager/<name>', methods=['GET', 'POST'])
@login_required
def policy_manager(name=None):
    policy_dict = json.loads(current_user.Policy)

    sys_policy_dict = policy_dict['系统策略']
    self_policy_dict = policy_dict['自选策略']
    self_policy_list = [(k, k) for k in self_policy_dict]
    authorize_binding = [(k, k) for k in json.loads(current_user.AuthorizeBinding)] if current_user.AuthorizeBinding else []


    # 策略管理
    class PolicyManagerForm(FlaskForm):
        sys_policy = SelectMultipleField('系统策略', choices=[('8以上赔标', '8以上赔标'), ('8.5以上赔标', '8.5以上赔标'), ('9以上赔标', '9以上赔标'), ('9.5以上赔标', '9.5以上赔标'), ('10以上赔标', '10以上赔标'), ('10.5以上赔标', '10.5以上赔标'), ('11以上赔标', '11以上赔标'), ('11.5以上赔标', '11.5以上赔标'), ('12以上赔标', '12以上赔标'), ('12.5以上赔标', '12.5以上赔标')])
        self_policy = SelectMultipleField('自选策略', choices=self_policy_list)
        BidAmount = IntegerField('单标投资金额', validators=[Optional(), NumberRange(min=50, max=500, message='投额必须为整数，且在 50~500 元之间')])
        binding = SelectMultipleField('授权列表', choices=authorize_binding)
        rate = StringField('利率区间', validators=[Optional(), Length(min=3, max=5, message='利率区间必须在 1~99 之间')])
        submit_unbind = SubmitField('解绑')
        submit_modify = SubmitField('绑定/修改')
        submit_del = SubmitField('删除')
        submit_rate = SubmitField('修改利率')


    form = PolicyManagerForm()
    if form.validate_on_submit():
        if form.sys_policy.data:
            policy_data = form.sys_policy.data
            policy_type = '系统策略'
        elif form.self_policy.data:
            policy_data = form.self_policy.data
            policy_type = '自选策略'

        if form.submit_modify.data:
            if form.binding.data or form.BidAmount.data:
                try:
                    for policy_name in policy_data:
                        if policy_name not in policy_dict[policy_type]:
                            policy_dict[policy_type][policy_name] = {}
                        if 'AuthorizeBinding' not in policy_dict[policy_type][policy_name]:
                            policy_dict[policy_type][policy_name]['AuthorizeBinding'] = []
                        if form.BidAmount.data:
                            policy_dict[policy_type][policy_name]['BidAmount'] = form.BidAmount.data
                        authorize_binding = policy_dict[policy_type][policy_name]['AuthorizeBinding']
                        authorize_binding.extend(form.binding.data)
                        policy_dict[policy_type][policy_name]['AuthorizeBinding'] = list(set(authorize_binding))
                    policy_str = str(policy_dict).replace('\'', '\"').replace(' ','')
                    current_user.Policy = policy_str
                    db.session.commit()
                    #flash('策略添加/修改成功','success')
                    return '{"success":["%s 策略绑定/修改成功"]}' % policy_data
                except UnboundLocalError:
                    #flash('策略添加/修改失败，请至少选择一个策略执行“添加/修改”操作','danger')
                    return '{"danger":["策略绑定/修改失败，请至少选择一个策略后，再执行相关操作"]}'
            else:
                return '{"danger":["策略绑定/修改失败，请至少选择/填入一个绑定/修改项后，再执行相关操作"]}'
        elif form.submit_unbind.data:
            if form.binding.data:
                try:
                    for policy_name in policy_data:
                        if policy_name in policy_dict[policy_type]:
                            authorize_binding = policy_dict[policy_type][policy_name]['AuthorizeBinding']
                            for each in form.binding.data:
                                try:
                                    authorize_binding.remove(each)
                                except:
                                    pass
                            policy_dict[policy_type][policy_name]['AuthorizeBinding'] = list(set(authorize_binding))
                    policy_str = str(policy_dict).replace('\'', '\"').replace(' ','')
                    current_user.Policy = policy_str
                    db.session.commit()
                    return '{"success":["%s 策略解绑成功"]}' % policy_data
                except UnboundLocalError:
                    return '{"danger":["策略解绑失败，请至少选择一个策略后，再执行相关操作"]}'
            else:
                return '{"danger":["策略解绑失败，请至少选择一个账户后，再执行相关操作"]}'
        elif form.submit_rate.data:
            if policy_type == '自选策略':
                try:
                    new_rate = list(map(float, form.rate.data.split(':')))
                    if len(new_rate) != 2:
                        return '{"danger":["策略利率修改失败，区间数据输入错误，请输入正确的区间格式，比如：20:99"]}'
                    for policy_name in policy_data:
                        policy_dict[policy_type][policy_name]['info']["interval"]["CurrentRate"] = new_rate
                    policy_str = str(policy_dict).replace('\'', '\"').replace(' ','')
                    current_user.Policy = policy_str
                    db.session.commit()
                    return '{"success":["%s 策略利率修改成功"]}' % policy_data
                except KeyError:
                    return '{"danger":["%s 策略利率修改失败，请选择“在用”列表中的策略后，再执行相关操作"]}' % policy_data
                except UnboundLocalError:
                    return '{"danger":["策略利率修改失败，请至少选择一个策略后，再执行相关操作"]}'
                except ValueError:
                    return '{"danger":["策略利率修改失败，区间数据输入错误，请输入正确的区间格式，比如：20:99"]}'
            else:
                return '{"danger":["策略利率修改失败，当前暂不支持系统策略的个性化利率设置"]}'
        elif form.submit_del.data:
            try:
                for policy_name in policy_data:
                    del policy_dict[policy_type][policy_name]
                policy_str = str(policy_dict).replace('\'', '\"').replace(' ','')
                current_user.Policy = policy_str
                db.session.commit()
                #flash('策略删除成功','warning')
                return '{"warning":["%s 策略删除成功"]}' % policy_data
            except KeyError:
                #flash('策略删除失败，请仅选择“在用”列表中的策略执行删除操作','danger')
                return '{"danger":["%s 策略删除失败，请选择“在用”列表中的策略后，再执行相关操作"]}' % policy_data
            except UnboundLocalError:
                #flash('策略删除失败，请至少选择一个策略执行“删除”操作','danger')
                return '{"danger":["策略删除失败，请至少选择一个策略后，再执行相关操作"]}'
        else:
            #flash('未知错误，请联系管理员','danger')
            return '{"danger":["未知错误，请联系管理员"]}'
    else:
        if form.errors:
            errors_list = [f"{form[field].label.text}：{', '.join(errors)}" for field, errors in form.errors.items()]
            return json.dumps({"danger":errors_list})

    return render_template('policy_manager.html', form=form, sys_policy_dict=sys_policy_dict, self_policy_dict=self_policy_dict)

# 策略自选
@account.route('/policy-self/<name>', methods=['GET', 'POST'])
@login_required
def policy_self(name=None):
    policy_dict = json.loads(current_user.Policy)
    self_policy_dict = policy_dict['自选策略']

    self_policy_list = [(each, each) for each in self_policy_dict]
    self_policy_list.insert(0, ('', '请选择'))

    def tree_map_chart(data):
        '''
        TreeMap(name, , width=1200, height=600) 类
            name -> str  图表名
            width -> str 图表宽度
            height -> str 图表高度

        TreeMap.add() 方法
            add(name, attr, value,
                shape="circle",
                word_gap=20,
                word_size_range=None,
                rotate_step=45)
            name -> str
            图例名称
            data -> list  矩形树图的数据项是 一棵树，每个节点包括value, name（可选）, children（也是树，可选）如下所示
            treemap_left_depth -> int  leafDepth 表示『展示几层』，层次更深的节点则被隐藏起来。设置了 leafDepth 后，下钻（drill down）功能开启。drill down 功能即点击后才展示子层级。例如，leafDepth 设置为 1，表示展示一层节点。
            treemap_drilldown_icon -> str  当节点可以下钻时的提示符。只能是字符。默认为 '▶'
            treemap_visible_min -> int  如果某个节点的矩形的面积，小于这个数值（单位：px平方），这个节点就不显示
            is_label_show=True, label_pos='inside'
        '''

        from pyecharts import TreeMap

        tree_map = TreeMap("策略参数展示")
        translate_dict = {
            "Amount":"借款金额",
            "CreditCode":"等级",
            "Months":"期限",
            "CurrentRate":"利率",
            "Gender":"性别",
            "Age":"年龄",
            "EducationDegree":"文化程度",
            "GraduateSchool":"毕业院校",
            "StudyStyle":"学习形式",
            "CertificateValidate":"学历认证",
            "CreditValidate":"征信认证",
            "NciicIdentityCheck":"户籍认证",
            "SuccessCount":"成功借款次数",
            "WasteCount":"流标",
            "CancelCount":"撤标",
            "FailedCount":"失败",
            "NormalCount":"正常还清次数",
            "OverdueLessCount":"逾期(0-15天)还清次数",
            "OverdueMoreCount":"逾期(15天以上)还清次数",
            "TotalPrincipal":"累计借款金额",
            "OwingPrincipal":"待还本金",
            "OwingAmount":"待还金额",
            "AmountToReceive":"待收金额",
            "HighestPrincipal":"单笔最高借款金额",
            "HighestDebt":"历史最高负债",
            "FirstRegTime":"首贷距注册",
            "NowLastTime":"上贷距今",
            "Debt":"贷后负债",
            "RatioAmountHighest":"贷款比",
            "RatioOwingAmount":"还贷比",
            "RatioOwingAmountHighestDebt":"还债比",
            "RatioDebtHighest":"负债比",
            "RatioTotalPaySuccessLoan":"还借比",
            "RatioTotalOverdueNormalPay":"逾还比",
            "RatioWasteNormalPay":"流还比"
        }
        policy_data = []

        for key, value in data.items():
            policy_children = []
            values_list = list(value['info'].values())
            info = dict(dict(values_list[0], **values_list[1]), **values_list[2])
            for k, v in info.items():
                if k == "Gender":
                    policy_children.append({'name':''.join(("性别=",['', '男', '女'][v])),'value':2})  # 性别为男 1，，女 2
                elif k == "GraduateSchool":
                    policy_children.append({'name':''.join(("毕业院校=",['其他', '985、211'][v])),'value':2})
                elif k == "CertificateValidate":
                    policy_children.append({'name':''.join(("学历认证=",['不投', '只投'][v])),'value':2})
                elif k == "CreditValidate":
                    policy_children.append({'name':''.join(("征信认证=",['不投', '只投'][v])),'value':2})
                elif k == "NciicIdentityCheck":
                    policy_children.append({'name':''.join(("户籍认证=",['不投', '只投'][v])),'value':2})
                else:
                    policy_children.append({'name':''.join((translate_dict[k],'=',str(v))),'value':2})
            policy_data.append({"name": key, "value":1, "children":policy_children})
        tree_map.add('参数展示', policy_data, is_label_show=True, label_pos='inside', treemap_left_depth=1)
        return tree_map

    # 策略自选
    class PolicySelfForm(FlaskForm):
        # Optional() 无输入值时跳过同字段验证函数
        all_self_policy = SelectField('所有自选策略', choices=self_policy_list)
        new_policy_name = StringField('新策略名', validators=[Optional(), Length(min=3, max=60, message='策略名长度必须在 2~60 个字节之间')], render_kw={"placeholder":"策略名若与既有策略同名，则既有策略将被重置"})
        Amount = StringField('借款金额', validators=[Optional(), Length(min=7, max=13, message='借款金额必须在 100~999999 之间')])
        CreditCode = SelectMultipleField('等级', choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D'), ('-999999', '不限')])
        CurrentRate = StringField('利率', validators=[Optional(), Length(min=3, max=5, message='利率必须在 1~99 之间')])
        Months = StringField('期限', validators=[Optional(), Length(min=3, max=5, message='期限必须为整数，且在 1~99 之间')])
        Gender = SelectField('性别', choices=[('', ''), ('1', '男'), ('2', '女'), ('-999999', '不限')], default='')
        Age = StringField('年龄', validators=[Optional(), Length(min=3, max=5, message='年龄必须为整数，且在 1~99 之间')])
        EducationDegree = SelectMultipleField('文化程度', choices=[('专科(高职)', '专科(高职)'), ('专科', '专科'), ('专升本', '专升本'), ('本科', '本科'), ('硕士', '硕士'), ('硕士研究生', '硕士研究生'), ('博士', '博士'), ('博士研究生', '博士研究生'), ('无', '无'), ('-999999', '不限')])
        GraduateSchool = SelectField('毕业院校', choices=[('', ''), ('1', '985、211'), ('-999999', '不限')], default='')
        StudyStyle = SelectMultipleField('学习形式', choices=[('普通', '普通'),('普通全日制', '普通全日制'),('全日制', '全日制'), ('研究生', '研究生'), ('自学考试', '自学考试'), ('自考', '自考'), ('成人', '成人'), ('网络教育', '网络教育'), ('函授', '函授'), ('业余', '业余'), ('夜大学', '夜大学'), ('脱产', '脱产'), ('开放教育', '开放教育'), ('-999999', '不限')])
        CertificateValidate = SelectField('学历认证', choices=[('', ''), ('1', '只投'), ('0', '不投'),('-999999', '不限')], default='')
        CreditValidate = SelectField('征信认证', choices=[('', ''), ('1', '只投'), ('0', '不投'),('-999999', '不限')], default='')
        NciicIdentityCheck = SelectField('户籍认证', choices=[('', ''), ('1', '只投'), ('0', '不投'),('-999999', '不限')], default='')
        SuccessCount = StringField('成功借款次数', validators=[Optional(), Length(min=3, max=7, message='次数必须为整数，且在 0~999 之间')])
        WasteCount = StringField('流标', validators=[Optional(), Length(min=3, max=7, message='次数必须为整数，且在 0~999 之间')])
        CancelCount = StringField('撤标', validators=[Optional(), Length(min=3, max=7, message='次数必须为整数，且在 0~999 之间')])
        FailedCount = StringField('失败', validators=[Optional(), Length(min=3, max=7, message='次数必须为整数，且在 0~999 之间')])
        NormalCount = StringField('正常还清次数', validators=[Optional(), Length(min=3, max=9, message='次数必须为整数，且在 0~9999 之间')])
        OverdueLessCount = StringField('逾期(0-15天)还清次数', validators=[Optional(), Length(min=3, max=9, message='次数必须为整数，且在 0~9999 之间')])
        OverdueMoreCount = StringField('逾期(15天以上)还清次数', validators=[Optional(), Length(min=3, max=9, message='次数必须为整数，且在 0~9999 之间')])
        TotalPrincipal = StringField('累计借款金额', validators=[Optional(), Length(min=3, max=15, message='金额必须为整数，且在 0~9999999 元之间')])
        OwingPrincipal = StringField('待还本金', validators=[Optional(), Length(min=3, max=13, message='金额必须为整数，且在 0~999999 元之间')])
        OwingAmount = StringField('待还金额', validators=[Optional(), Length(min=3, max=13, message='金额必须为整数，且在 0~999999 元之间')])
        AmountToReceive = StringField('待收金额', validators=[Optional(), Length(min=3, max=17, message='金额必须为整数，且在 0~99999999 元之间')])
        HighestPrincipal = StringField('单笔最高借款金额', validators=[Optional(), Length(min=3, max=13, message='金额必须为整数，且在 0~999999 元之间')])
        HighestDebt = StringField('历史最高负债', validators=[Optional(), Length(min=3, max=13, message='金额必须为整数，且在 0~999999 元之间')])
        FirstRegTime = StringField('首贷距注册时间', validators=[Optional(), Length(min=3, max=9, message='天数必须为整数，且在 0~9999 之间')])
        NowLastTime = StringField('上贷距今', validators=[Optional(), Length(min=3, max=9, message='天数必须为整数，且在 0~9999 之间')])
        Debt = StringField('贷后负债', validators=[Optional(), Length(min=3, max=15, message='金额必须为整数，且在 0~9999999 之间')], render_kw={"placeholder":"借款金额+待还金额"})
        RatioAmountHighest = StringField('贷款比', validators=[Optional(), Length(min=3, max=13, message='比值可以为浮点数或整数，但字符串整体长度须小于 13 字节')], render_kw={"placeholder":"借款金额/最高借款金额"})
        RatioOwingAmount = StringField('还贷比', validators=[Optional(), Length(min=3, max=13, message='比值可以为浮点数或整数，但字符串整体长度须小于 13 字节')], render_kw={"placeholder":"待还金额/借款金额"})
        RatioOwingAmountHighestDebt = StringField('还债比', validators=[Optional(), Length(min=3, max=13, message='比值可以为浮点数或整数，但字符串整体长度须小于 13 字节')], render_kw={"placeholder":"待还金额/最高负债"})
        RatioDebtHighest = StringField('负债比', validators=[Optional(), Length(min=3, max=13, message='比值可以为浮点数或整数，但字符串整体长度须小于 13 字节')], render_kw={"placeholder":"待还金额+借款金额/最高负债"})
        RatioTotalPaySuccessLoan = StringField('还借比', validators=[Optional(), Length(min=3, max=13, message='比值可以为浮点数或整数，但字符串整体长度须小于 13 字节')], render_kw={"placeholder":"总还款次数/借款次数"})
        RatioTotalOverdueNormalPay = StringField('逾还比', validators=[Optional(), Length(min=3, max=13, message='比值为浮点数或整数，但字符串整体长度须小于 13 字节')], render_kw={"placeholder":"总逾期次数/正常还清次数"})
        RatioWasteNormalPay = StringField('流还比', validators=[Optional(), Length(min=3, max=13, message='比值可以为浮点数或整数，但字符串整体长度须小于 13 字节')], render_kw={"placeholder":"流标次数/正常还清次数"})

        submit = SubmitField('添加/修改')


    form = PolicySelfForm()
    if form.validate_on_submit():
        form_data = form.data
        if form_data.get('all_self_policy') or (form_data.get('new_policy_name') and len(self_policy_dict) <= 13):
            policy_name = form_data.get('all_self_policy') or form_data.get('new_policy_name')
            if policy_name not in policy_dict['自选策略']:
                policy_dict['自选策略'][policy_name] = {'info':{'is':{}, 'in':{}, 'interval':{}}}

            pop_key_list = ['submit', 'csrf_token', 'all_self_policy', 'new_policy_name']
            for key in pop_key_list:
                del form_data[key]

            ed, ss, gs = [form_data.get('EducationDegree'), form_data.get('StudyStyle'), form_data.get('GraduateSchool')]
            for each in ed,ss,gs:
                if each and ('-999999' not in each):
                    del form_data['CertificateValidate']
                    break

            if gs:
                if gs == '-999999':
                    del policy_dict['自选策略'][policy_name]['info']['in']['GraduateSchool']
                else:
                    policy_dict['自选策略'][policy_name]['info']['in']['GraduateSchool'] = gs
            del form_data['GraduateSchool']

            for key, value in form_data.items():
                if value:
                    try:
                        if '-999999' in value:
                            if key in ('CreditCode', 'EducationDegree', 'StudyStyle'):
                                del policy_dict['自选策略'][policy_name]['info']['in'][key]
                            elif key in ('Gender', 'CertificateValidate', 'CreditValidate', 'NciicIdentityCheck'):
                                del policy_dict['自选策略'][policy_name]['info']['is'][key]
                            else:
                                del policy_dict['自选策略'][policy_name]['info']['interval'][key]
                        else:
                            if isinstance(value, (str)):
                                if value in ('0', '1', '2'):
                                    policy_dict['自选策略'][policy_name]['info']['is'][key] = int(value)
                                else:
                                    value_split = value.split(':')
                                    if len(value_split) is 2:
                                        policy_dict['自选策略'][policy_name]['info']['interval'][key] = list(map(float, value_split))
                                    else:
                                        return '{"danger":["%s 区间数据输入错误，请输入正确的区间格式，比如：10:20"]}' % key
                            else:
                                policy_dict['自选策略'][policy_name]['info']['in'][key] = value
                    except KeyError as e:
                        return '{"success":["自选策略添加/修改失败，存在错误：%s"]}' % e
            else:
                policy_str = str(policy_dict).replace('\'', '\"').replace(' ','')
                current_user.Policy = policy_str
                db.session.commit()
                return '{"success":["自选策略添加/修改成功"]}'
        else:
            return '{"danger":["自选策略“添加/修改”失败，请在“新策略名”或“所有自选策略”中选择一项“填写/选择”，以执行“添加/修改”操作"，如若错误依旧，那么请确保策略总数不超过 13 个。]}'
    else:
        if form.errors:
            errors_list = [f"{form[field].label.text}：{', '.join(errors)}" for field, errors in form.errors.items()]
            return json.dumps({"danger":errors_list})

    if self_policy_dict:
        treeMapChart = tree_map_chart(self_policy_dict)
    else:
        treeMapChart = None

    # return render_template('policy_self.html',
                            # form=form,
                            # treeMapChart=treeMapChart and treeMapChart.render_embed() or None,
                            # host=remote_host,
                            # script_list=treeMapChart and treeMapChart.get_js_dependencies() or None)
    return render_template('policy_self.html', form=form, treeMapChart=treeMapChart and treeMapChart.render_embed() or None)

# 债权管理
@account.route('/debt-policy-manager/<name>', methods=['GET', 'POST'])
@login_required
def debt_policy_manager(name=None):
    policy_dict = json.loads(current_user.DebtPolicy)

    sys_policy_dict = policy_dict['系统策略']
    self_policy_dict = policy_dict['自选策略']
    self_policy_list = [(k, k) for k in self_policy_dict]
    authorize_binding = [(k, k) for k in json.loads(current_user.AuthorizeBinding)] if current_user.AuthorizeBinding else []


    # 策略管理
    class DebtPolicyManagerForm(FlaskForm):
        sys_policy = SelectMultipleField('系统策略', choices=[('8以上赔标', '8以上赔标'), ('8.5以上赔标', '8.5以上赔标'), ('9以上赔标', '9以上赔标'), ('9.5以上赔标', '9.5以上赔标'), ('10以上赔标', '10以上赔标'), ('10.5以上赔标', '10.5以上赔标'), ('11以上赔标', '11以上赔标'), ('11.5以上赔标', '11.5以上赔标'), ('12以上赔标', '12以上赔标'), ('12.5以上赔标', '12.5以上赔标')])
        self_policy = SelectMultipleField('自选策略', choices=self_policy_list)
        price_for_sale = StringField('转让价格', validators=[Optional(), Length(min=3, max=11, message='转让价格必须为整数，且在 0~99999 元之间')])
        binding = SelectMultipleField('授权列表', choices=authorize_binding)
        submit_unbind = SubmitField('解绑')
        submit_modify = SubmitField('绑定/修改')
        submit_del = SubmitField('删除')


    form = DebtPolicyManagerForm()
    if form.validate_on_submit():
        if form.sys_policy.data:
            policy_data = form.sys_policy.data
            policy_type = '系统策略'
        elif form.self_policy.data:
            policy_data = form.self_policy.data
            policy_type = '自选策略'

        if form.submit_modify.data:
            try:
                for policy_name in policy_data:
                    if policy_name not in policy_dict[policy_type]:
                        policy_dict[policy_type][policy_name] = {}
                    if 'AuthorizeBinding' not in policy_dict[policy_type][policy_name]:
                        policy_dict[policy_type][policy_name]['AuthorizeBinding'] = []
                    if form.price_for_sale.data:
                        try:
                            price_for_sale_min, price_for_sale_max = map(int, form.price_for_sale.data.split(':'))
                        except:
                            return '{"danger":["债权策略绑定/修改失败，转让价格数据输入错误，请输入正确的格式，比如：0:99999"]}'
                        policy_dict[policy_type][policy_name]['PriceForSale'] = [price_for_sale_min, price_for_sale_max]
                    authorize_binding = policy_dict[policy_type][policy_name]['AuthorizeBinding']
                    authorize_binding.extend(form.binding.data)
                    policy_dict[policy_type][policy_name]['AuthorizeBinding'] = list(set(authorize_binding))
                policy_str = str(policy_dict).replace('\'', '\"').replace(' ','')
                current_user.DebtPolicy = policy_str
                db.session.commit()
                return '{"success":["%s 债权策略绑定/修改成功"]}' % policy_data
            except UnboundLocalError:
                return '{"danger":["债权策略绑定/修改失败，请至少选择一个策略后，再执行相关操作"]}'
        elif form.submit_unbind.data:
            if form.binding.data:
                try:
                    for policy_name in policy_data:
                        if policy_name in policy_dict[policy_type]:
                            authorize_binding = policy_dict[policy_type][policy_name]['AuthorizeBinding']
                            for each in form.binding.data:
                                try:
                                    authorize_binding.remove(each)
                                except:
                                    pass
                            policy_dict[policy_type][policy_name]['AuthorizeBinding'] = list(set(authorize_binding))
                    policy_str = str(policy_dict).replace('\'', '\"').replace(' ','')
                    current_user.DebtPolicy = policy_str
                    db.session.commit()
                    return '{"success":["%s 策略解绑成功"]}' % policy_data
                except UnboundLocalError:
                    return '{"danger":["策略解绑失败，请至少选择一个策略后，再执行相关操作"]}'
            else:
                return '{"danger":["策略解绑失败，请至少选择一个账户后，再执行相关操作"]}'
        elif form.submit_del.data:
            try:
                for policy_name in policy_data:
                    del policy_dict[policy_type][policy_name]
                policy_str = str(policy_dict).replace('\'', '\"').replace(' ','')
                current_user.DebtPolicy = policy_str
                db.session.commit()
                return '{"warning":["%s 债权策略删除成功"]}' % policy_data
            except KeyError:
                return '{"danger":["%s 债权策略删除失败，请选择“在用”列表中的策略后，再执行相关操作"]}' % policy_data
            except UnboundLocalError:
                return '{"danger":["债权策略删除失败，请至少选择一个策略后，再执行相关操作"]}'
        else:
            return '{"danger":["未知错误，请联系管理员"]}'
    else:
        if form.errors:
            errors_list = [f"{form[field].label.text}：{', '.join(errors)}" for field, errors in form.errors.items()]
            return json.dumps({"danger":errors_list})

    return render_template('debt_policy_manager.html', form=form, sys_policy_dict=sys_policy_dict, self_policy_dict=self_policy_dict)

# 债权自选
@account.route('/debt-policy-self/<name>', methods=['GET', 'POST'])
@login_required
def debt_policy_self(name=None):
    policy_dict = json.loads(current_user.DebtPolicy)
    self_policy_dict = policy_dict['自选策略']

    self_policy_list = [(each, each) for each in self_policy_dict]
    self_policy_list.insert(0, ('', '请选择'))

    def debt_tree_map_chart(data):
        '''
        TreeMap(name, , width=1200, height=600) 类
            name -> str  图表名
            width -> str 图表宽度
            height -> str 图表高度

        TreeMap.add() 方法
            add(name, attr, value,
                shape="circle",
                word_gap=20,
                word_size_range=None,
                rotate_step=45)
            name -> str
            图例名称
            data -> list  矩形树图的数据项是 一棵树，每个节点包括value, name（可选）, children（也是树，可选）如下所示
            treemap_left_depth -> int  leafDepth 表示『展示几层』，层次更深的节点则被隐藏起来。设置了 leafDepth 后，下钻（drill down）功能开启。drill down 功能即点击后才展示子层级。例如，leafDepth 设置为 1，表示展示一层节点。
            treemap_drilldown_icon -> str  当节点可以下钻时的提示符。只能是字符。默认为 '▶'
            treemap_visible_min -> int  如果某个节点的矩形的面积，小于这个数值（单位：px平方），这个节点就不显示
            is_label_show=True, label_pos='inside'
        '''

        from pyecharts import TreeMap

        tree_map = TreeMap("策略参数展示")
        translate_dict = {
            "Amount":"借款金额",
            "CreditCode":"等级",
            "Months":"期限",
            "CurrentRate":"利率",
            "Gender":"性别",
            "Age":"年龄",
            "EducationDegree":"文化程度",
            "GraduateSchool":"毕业院校",
            "StudyStyle":"学习形式",
            "CertificateValidate":"学历认证",
            "CreditValidate":"征信认证",
            "NciicIdentityCheck":"户籍认证",
            "SuccessCount":"成功借款次数",
            "WasteCount":"流标",
            "CancelCount":"撤标",
            "FailedCount":"失败",
            "NormalCount":"正常还清次数",
            "OverdueLessCount":"逾期(0-15天)还清次数",
            "OverdueMoreCount":"逾期(15天以上)还清次数",
            "TotalPrincipal":"累计借款金额",
            "OwingPrincipal":"待还本金",
            "OwingAmount":"待还金额",
            "AmountToReceive":"待收金额",
            "HighestPrincipal":"单笔最高借款金额",
            "HighestDebt":"历史最高负债",
            "FirstRegTime":"首贷距注册",
            "NowLastTime":"上贷距今",
            "Debt":"贷后负债",
            "RatioAmountHighest":"贷款比",
            "RatioOwingAmount":"还贷比",
            "RatioOwingAmountHighestDebt":"还债比",
            "RatioDebtHighest":"负债比",
            "RatioTotalPaySuccessLoan":"还借比",
            "RatioTotalOverdueNormalPay":"逾还比",
            "RatioWasteNormalPay":"流还比"
        }
        policy_data = []

        for key, value in data.items():
            policy_children = []
            values_list = list(value['info'].values())
            info = dict(dict(values_list[0], **values_list[1]), **values_list[2])
            for k, v in info.items():
                if k == "Gender":
                    policy_children.append({'name':''.join(("性别=",['', '男', '女'][v])),'value':2})  # 性别为男 1，，女 2
                elif k == "GraduateSchool":
                    policy_children.append({'name':''.join(("毕业院校=",['其他', '985、211'][v])),'value':2})
                elif k == "CertificateValidate":
                    policy_children.append({'name':''.join(("学历认证=",['不投', '只投'][v])),'value':2})
                elif k == "CreditValidate":
                    policy_children.append({'name':''.join(("征信认证=",['不投', '只投'][v])),'value':2})
                elif k == "NciicIdentityCheck":
                    policy_children.append({'name':''.join(("户籍认证=",['不投', '只投'][v])),'value':2})
                else:
                    policy_children.append({'name':''.join((translate_dict[k],'=',str(v))),'value':2})
            policy_data.append({"name": key, "value":1, "children":policy_children})
        tree_map.add('参数展示', policy_data, is_label_show=True, label_pos='inside', treemap_left_depth=1)
        return tree_map

    # 策略自选
    class DebtPolicySelfForm(FlaskForm):
        all_self_policy = SelectField('所有自选债权策略', choices=self_policy_list)
        new_policy_name = StringField('新策略名', validators=[Optional(), Length(min=3, max=60, message='策略名长度必须在 2~60 个字节之间')], render_kw={"placeholder":"策略名若与既有策略同名，则既有策略将被重置"})

        # Optional() 无输入值时跳过同字段验证函数
        Amount = StringField('借款金额', validators=[Optional(), Length(min=7, max=13, message='借款金额必须在 100~999999 之间')])
        CreditCode = SelectMultipleField('等级', choices=[('A', 'A'), ('B', 'B'), ('C', 'C'), ('D', 'D'), ('-999999', '不限')])
        CurrentRate = StringField('利率', validators=[Optional(), Length(min=3, max=5, message='利率必须在 1~99 之间')])
        Months = StringField('期限', validators=[Optional(), Length(min=3, max=5, message='期限必须为整数，且在 1~99 之间')])
        Gender = SelectField('性别', choices=[('', ''), ('1', '男'), ('2', '女'), ('-999999', '不限')], default='')
        Age = StringField('年龄', validators=[Optional(), Length(min=3, max=5, message='年龄必须为整数，且在 1~99 之间')])
        EducationDegree = SelectMultipleField('文化程度', choices=[('专科(高职)', '专科(高职)'), ('专科', '专科'), ('专升本', '专升本'), ('本科', '本科'), ('硕士', '硕士'), ('硕士研究生', '硕士研究生'), ('博士', '博士'), ('博士研究生', '博士研究生'), ('无', '无'), ('-999999', '不限')])
        GraduateSchool = SelectField('毕业院校', choices=[('', ''), ('1', '985、211'), ('-999999', '不限')], default='')
        StudyStyle = SelectMultipleField('学习形式', choices=[('普通', '普通'),('普通全日制', '普通全日制'),('全日制', '全日制'), ('研究生', '研究生'), ('自学考试', '自学考试'), ('自考', '自考'), ('成人', '成人'), ('网络教育', '网络教育'), ('函授', '函授'), ('业余', '业余'), ('夜大学', '夜大学'), ('脱产', '脱产'), ('开放教育', '开放教育'), ('-999999', '不限')])
        CertificateValidate = SelectField('学历认证', choices=[('', ''), ('1', '只投'), ('0', '不投'),('-999999', '不限')], default='')
        CreditValidate = SelectField('征信认证', choices=[('', ''), ('1', '只投'), ('0', '不投'),('-999999', '不限')], default='')
        NciicIdentityCheck = SelectField('户籍认证', choices=[('', ''), ('1', '只投'), ('0', '不投'),('-999999', '不限')], default='')
        SuccessCount = StringField('成功借款次数', validators=[Optional(), Length(min=3, max=7, message='次数必须为整数，且在 0~999 之间')])
        WasteCount = StringField('流标', validators=[Optional(), Length(min=3, max=7, message='次数必须为整数，且在 0~999 之间')])
        CancelCount = StringField('撤标', validators=[Optional(), Length(min=3, max=7, message='次数必须为整数，且在 0~999 之间')])
        FailedCount = StringField('失败', validators=[Optional(), Length(min=3, max=7, message='次数必须为整数，且在 0~999 之间')])
        NormalCount = StringField('正常还清次数', validators=[Optional(), Length(min=3, max=9, message='次数必须为整数，且在 0~9999 之间')])
        OverdueLessCount = StringField('逾期(0-15天)还清次数', validators=[Optional(), Length(min=3, max=9, message='次数必须为整数，且在 0~9999 之间')])
        OverdueMoreCount = StringField('逾期(15天以上)还清次数', validators=[Optional(), Length(min=3, max=9, message='次数必须为整数，且在 0~9999 之间')])
        TotalPrincipal = StringField('累计借款金额', validators=[Optional(), Length(min=3, max=15, message='金额必须为整数，且在 0~9999999 元之间')])
        OwingPrincipal = StringField('待还本金', validators=[Optional(), Length(min=3, max=13, message='金额必须为整数，且在 0~999999 元之间')])
        OwingAmount = StringField('待还金额', validators=[Optional(), Length(min=3, max=13, message='金额必须为整数，且在 0~999999 元之间')])
        AmountToReceive = StringField('待收金额', validators=[Optional(), Length(min=3, max=17, message='金额必须为整数，且在 0~99999999 元之间')])
        HighestPrincipal = StringField('单笔最高借款金额', validators=[Optional(), Length(min=3, max=13, message='金额必须为整数，且在 0~999999 元之间')])
        HighestDebt = StringField('历史最高负债', validators=[Optional(), Length(min=3, max=13, message='金额必须为整数，且在 0~999999 元之间')])
        FirstRegTime = StringField('首贷距注册时间', validators=[Optional(), Length(min=3, max=9, message='天数必须为整数，且在 0~9999 之间')])
        NowLastTime = StringField('上贷距今', validators=[Optional(), Length(min=3, max=9, message='天数必须为整数，且在 0~9999 之间')])
        Debt = StringField('贷后负债', validators=[Optional(), Length(min=3, max=15, message='金额必须为整数，且在 0~9999999 之间')], render_kw={"placeholder":"借款金额+待还金额"})
        RatioAmountHighest = StringField('贷款比', validators=[Optional(), Length(min=3, max=13, message='比值可以为浮点数或整数，但字符串整体长度须小于 13 字节')], render_kw={"placeholder":"借款金额/最高借款金额"})
        RatioOwingAmount = StringField('还贷比', validators=[Optional(), Length(min=3, max=13, message='比值可以为浮点数或整数，但字符串整体长度须小于 13 字节')], render_kw={"placeholder":"待还金额/借款金额"})
        RatioOwingAmountHighestDebt = StringField('还债比', validators=[Optional(), Length(min=3, max=13, message='比值可以为浮点数或整数，但字符串整体长度须小于 13 字节')], render_kw={"placeholder":"待还金额/最高负债"})
        RatioDebtHighest = StringField('负债比', validators=[Optional(), Length(min=3, max=13, message='比值可以为浮点数或整数，但字符串整体长度须小于 13 字节')], render_kw={"placeholder":"待还金额+借款金额/最高负债"})
        RatioTotalPaySuccessLoan = StringField('还借比', validators=[Optional(), Length(min=3, max=13, message='比值可以为浮点数或整数，但字符串整体长度须小于 13 字节')], render_kw={"placeholder":"总还款次数/借款次数"})
        RatioTotalOverdueNormalPay = StringField('逾还比', validators=[Optional(), Length(min=3, max=13, message='比值为浮点数或整数，但字符串整体长度须小于 13 字节')], render_kw={"placeholder":"总逾期次数/正常还清次数"})
        RatioWasteNormalPay = StringField('流还比', validators=[Optional(), Length(min=3, max=13, message='比值可以为浮点数或整数，但字符串整体长度须小于 13 字节')], render_kw={"placeholder":"流标次数/正常还清次数"})


        submit = SubmitField('添加/修改')

    form = DebtPolicySelfForm()
    if form.validate_on_submit():
        form_data = form.data
        if form_data.get('all_self_policy') or (form_data.get('new_policy_name') and len(self_policy_dict) <= 12):
            policy_name = form_data.get('all_self_policy') or form_data.get('new_policy_name')
            if policy_name not in policy_dict['自选策略']:
                policy_dict['自选策略'][policy_name] = {'info':{'is':{}, 'in':{}, 'interval':{}}}

            pop_key_list = ['submit', 'csrf_token', 'all_self_policy', 'new_policy_name']
            for key in pop_key_list:
                del form_data[key]

            ed, ss, gs = [form_data.get('EducationDegree'), form_data.get('StudyStyle'), form_data.get('GraduateSchool')]
            for each in ed,ss,gs:
                if each and ('-999999' not in each):
                    del form_data['CertificateValidate']
                    break

            if gs:
                if gs == '-999999':
                    del policy_dict['自选策略'][policy_name]['info']['in']['GraduateSchool']
                else:
                    policy_dict['自选策略'][policy_name]['info']['in']['GraduateSchool'] = gs
            del form_data['GraduateSchool']

            for key, value in form_data.items():
                if value:
                    try:
                        if '-999999' in value:
                            if key in ('CreditCode', 'EducationDegree', 'StudyStyle'):
                                del policy_dict['自选策略'][policy_name]['info']['in'][key]
                            elif key in ('Gender', 'CertificateValidate', 'CreditValidate', 'NciicIdentityCheck'):
                                del policy_dict['自选策略'][policy_name]['info']['is'][key]
                            else:
                                del policy_dict['自选策略'][policy_name]['info']['interval'][key]
                        else:
                            if isinstance(value, (str)):
                                if value in ('0', '1', '2'):
                                    policy_dict['自选策略'][policy_name]['info']['is'][key] = int(value)
                                else:
                                    value_split = value.split(':')
                                    if len(value_split) is 2:
                                        policy_dict['自选策略'][policy_name]['info']['interval'][key] = list(map(float, value_split))
                                    else:
                                        return '{"success":["%s 区间数据输入错误，请输入正确的区间格式，比如：10:20"]}' % key
                            else:
                                policy_dict['自选策略'][policy_name]['info']['in'][key] = value
                    except KeyError as e:
                        return '{"danger":["自选债权策略添加/修改失败，存在错误：%s"]}' % e
            else:
                policy_str = str(policy_dict).replace('\'', '\"').replace(' ','')
                current_user.DebtPolicy = policy_str
                db.session.commit()
                return '{"success":["自选债权策略添加/修改成功"]}'
        else:
            return '{"danger":["自选债权策略“添加/修改”失败，请在“新债权策略名”或“所有自选债权策略”中选择一项“填写/选择”，以执行“添加/修改”操作，如若错误依旧，那么请确保策略总数不超过 12 个。"]}'
    else:
        if form.errors:
            errors_list = [f"{form[field].label.text}：{', '.join(errors)}" for field, errors in form.errors.items()]
            return json.dumps({"danger":errors_list})

    if self_policy_dict:
        treeMapChart = debt_tree_map_chart(self_policy_dict)
    else:
        treeMapChart = None

    return render_template('debt_policy_self.html', form=form, treeMapChart=treeMapChart and treeMapChart.render_embed() or None)

# 投标统计
@account.route('/counter/<name>', methods=['GET', 'POST'])
@login_required
@cached(timeout=86400)
def counter(name=None):
    yesterday = date.today() - timedelta(days = 1)
    binding_list = list(json.loads(current_user.AuthorizeBinding).keys())
    policy_dict = json.loads(current_user.Policy)
    policy_list = list(policy_dict['自选策略'].keys())
    user_bids = gentable(current_user.Name, '_Bids')  # 动态建表
    user_bids_query = user_bids.query
    count_arg = [[1,[1, 10]], [1,[11, 30]], [2,[31, 60]], [3,[61, 90]], [4,[91, 9999]]]

    count_list = [[policy_name, [[i, rate_query(user_bids, yesterday, i+1, i, policy_name), [count_query(user_bids, user_bids_query, yesterday, each[0], i+1, i, policy_name, binding_list, each[1]) for each in count_arg]] for i in range(1, 19)]] for policy_name in policy_list]

    return render_template('counter.html', count_list=count_list, enumerate=enumerate, round=round)

def count_query(user_bids, user_bids_query, baseDate, back, start_now, end_now, policy_name, binding_list, overdue_days):
    from dateutil.relativedelta import relativedelta
    if start_now > back > end_now:
        end_date = str(baseDate-relativedelta(months=back)) + ' 23:59:59'
    elif start_now <= back:
        return [0, 0, 0]
    else:
        end_date = str(baseDate-relativedelta(months=end_now)) + ' 23:59:59'
    start_date = str(baseDate-relativedelta(months=start_now)) + ' 00:00:00'

    user_bids_query_all = user_bids_query.filter(user_bids.PolicyName == policy_name, user_bids.BidTime >= start_date, user_bids.BidTime <= end_date, user_bids.User.in_(binding_list))

    user_bids_query_black = user_bids_query_all.filter(user_bids.Black >= overdue_days[0], user_bids.Black <= overdue_days[1])
    # 采用 with_entities 方法，可以使用 sql 原生函数，利于优化性能
    count_all = user_bids_query_all.with_entities(func.count(user_bids.ListingId)).scalar()
    if count_all:
        count_black = user_bids_query_black.with_entities(func.count(user_bids.ListingId)).scalar()
        overdue_rate = round((count_black / count_all) * 100, 3)  # 百分比
        return [count_black, count_all, overdue_rate]
    else:
        return [0, 0, 0]

def rate_query(user_bids, baseDate, start_now, end_now, policy_name):
    from dateutil.relativedelta import relativedelta

    start_date_pre = str(baseDate-relativedelta(months=start_now))
    end_date_pre = str(baseDate-relativedelta(months=end_now))
    start_date = start_date_pre + ' 00:00:00'
    end_date = end_date_pre + ' 23:59:59'

    all_bids_query = db.session.query(AllBids.CurrentRate, AllBids.Months).join(user_bids, user_bids.ListingId==AllBids.ListingId).filter(user_bids.PolicyName == policy_name, user_bids.BidTime >= start_date, user_bids.BidTime <= end_date)
    all_bids_query_all = all_bids_query.all()
    len_all_bids_query_all = len(all_bids_query_all)
    if len_all_bids_query_all:
        rate_list, months_list = list(zip(*all_bids_query_all))
        months_Average = round(sum(months_list)/len_all_bids_query_all, 2)
        rate_Average = round(sum(rate_list)/len_all_bids_query_all, 2)
        return (start_date_pre, end_date_pre, months_Average, rate_Average)
    else:
        return (start_date_pre, end_date_pre, 0, 0)

# 投标记录
@account.route('/bid-list/<name>', methods=['GET', 'POST'])
@login_required
@cached(timeout=300)
def bid_list(name=None):
    #offset = int(request.args.get('offset', 0))
    #limit = int(request.args.get('limit', 20))
    today = date.today()
    offset = 0
    limit = 20
    # 读取标信息
    user_bids = gentable(current_user.Name, '_Bids')  # 动态建表
    bid_list_sql = user_bids.query

    # 读取用户信息
    policy_dict = json.loads(current_user.Policy)
    sys_policy_dict = policy_dict['系统策略']
    self_policy_dict = policy_dict['自选策略']
    all_policy_dict = dict(sys_policy_dict, **self_policy_dict)
    all_policy = [(each, each) for each in all_policy_dict]
    all_policy = [('', '')] + all_policy


    # 策略自选
    class BidListForm(FlaskForm):
        policy_name = SelectField('策略名称', choices=all_policy)
        # Optional() 无输入值时跳过同字段验证函数
        start_date = DateField('起始日期', format='%Y-%m-%d', default=today)
        end_date = DateField('截止日期', format='%Y-%m-%d', default=today)

        submit_today_filter = SubmitField('今日查询')
        submit_date_filter = SubmitField('日期查询')
        submit_no_filter = SubmitField('直接查询')


    form = BidListForm()
    policy_name = start_date = end_date = ''

    if request.form and request.form.get('offset'):
        offset = int(request.form.get('offset'))
        policy_name = request.form.get('policy_name')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        current_page = int(request.form.get('current_page'))
        total_page = int(request.form.get('total_page'))

        if policy_name:
            bid_list_sql = bid_list_sql.filter(user_bids.PolicyName == policy_name)
        if start_date:
            bid_list_sql = bid_list_sql.filter(user_bids.BidTime >= (start_date+' 00:00:00'), user_bids.BidTime <= (end_date+' 23:59:59'))

        bid_list = bid_list_sql.order_by(user_bids.ID.desc()).limit(limit).offset(offset).all()
        record_list = [{"PolicyName":bid.PolicyName,
            "ListingId":bid.ListingId,
            "ParticipationAmount":bid.ParticipationAmount,
            "BidTime":str(bid.BidTime),
            "User":bid.User if bid.User else '空'
            } for bid in bid_list]

        return '{"success":["查询成功"], "record_list":{"record_list":%s, "policy_name":"%s", "start_date":"%s", "end_date":"%s", "current_page":%s, "total_page":%s}}' % (str(record_list).replace("'",'"'), policy_name, start_date, end_date, current_page, total_page)
    elif form.validate_on_submit():
        if form.policy_name.data:
            policy_name = form.policy_name.data
            bid_list_sql = bid_list_sql.filter(user_bids.PolicyName == policy_name)
        if form.submit_today_filter.data:
            start_date = end_date = str(today)
            bid_list_sql = bid_list_sql.filter(user_bids.BidTime >= (start_date+' 00:00:00'), user_bids.BidTime <= (end_date+' 23:59:59'))
        elif form.submit_date_filter.data:
            try:
                start_date, end_date = str(form.start_date.data), str(form.end_date.data)
                bid_list_sql = bid_list_sql.filter(user_bids.BidTime >= (start_date+' 00:00:00'), user_bids.BidTime <= (end_date+' 23:59:59'))
            except:
                return '{"danger":["查询失败，请检查您所输入的日期格式是否正确！"]}'
        # 采用 with_entities 方法，可以使用 sql 原生函数，利于优化性能
        count = bid_list_sql.with_entities(func.count(user_bids.ListingId)).scalar()
        bid_list = bid_list_sql.order_by(user_bids.ID.desc()).limit(limit).offset(offset).all()
        record_list = [{"PolicyName":bid.PolicyName,
            "ListingId":bid.ListingId,
            "ParticipationAmount":bid.ParticipationAmount,
            "BidTime":str(bid.BidTime),
            "User":bid.User if bid.User else '空'
        } for bid in bid_list]

        return '{"success":["查询成功"], "record_list":{"record_list":%s, "policy_name":"%s", "start_date":"%s", "end_date":"%s", "count":%s, "limit":%s, "current_page":1}}' % (str(record_list).replace("'",'"'), policy_name, start_date, end_date, count, limit)
    else:
        if form.errors:
            errors_list = [f"{form[field].label.text}：{', '.join(errors)}" for field, errors in form.errors.items()]
            return json.dumps({"danger":errors_list})
        # 默认查询今日投标记录
        start_date = end_date = str(today)
        bid_list_sql = bid_list_sql.filter(user_bids.BidTime >= (start_date+' 00:00:00'), user_bids.BidTime <= (end_date+' 23:59:59'))
        count = bid_list_sql.with_entities(func.count(user_bids.ListingId)).scalar()

    bid_list = bid_list_sql.order_by(user_bids.ID.desc()).limit(limit).offset(offset).all()
    db.session.commit()

    return render_template('bid_list.html', form=form, bid_list=bid_list, count=count, offset=offset, limit=limit, policy_name=policy_name, start_date=start_date, end_date=end_date)

# 购债记录
@account.route('/debt-list/<name>', methods=['GET', 'POST'])
@login_required
@cached(timeout=300)
def debt_list(name=None):
    #offset = int(request.args.get('offset', 0))
    #limit = int(request.args.get('limit', 20))
    today = date.today()
    offset = 0
    limit = 20
    # 读取标信息
    user_debts = gentable(current_user.Name, '_Debts')  # 动态建表
    debt_list_sql = user_debts.query

    # 读取用户信息
    policy_dict = json.loads(current_user.DebtPolicy)
    sys_policy_dict = policy_dict['系统策略']
    self_policy_dict = policy_dict['自选策略']
    all_policy_dict = dict(sys_policy_dict, **self_policy_dict)
    all_policy = [(each, each) for each in all_policy_dict]
    all_policy = [('', '')] + all_policy


    # 债权策略自选
    class debtListForm(FlaskForm):
        policy_name = SelectField('策略名称', choices=all_policy)
        # Optional() 无输入值时跳过同字段验证函数
        start_date = DateField('起始日期', format='%Y-%m-%d', default=today)
        end_date = DateField('截止日期', format='%Y-%m-%d', default=today)

        submit_today_filter = SubmitField('今日查询')
        submit_date_filter = SubmitField('日期查询')
        submit_no_filter = SubmitField('直接查询')


    form = debtListForm()
    policy_name = start_date = end_date = ''

    if request.form and request.form.get('offset'):
        offset = int(request.form.get('offset'))
        policy_name = request.form.get('policy_name')
        start_date = request.form.get('start_date')
        end_date = request.form.get('end_date')
        current_page = int(request.form.get('current_page'))
        total_page = int(request.form.get('total_page'))

        if policy_name:
            debt_list_sql = debt_list_sql.filter(user_debts.PolicyName == policy_name)
        if start_date:
            debt_list_sql = debt_list_sql.filter(user_debts.BuyDate >= start_date, user_debts.BuyDate <= end_date)

        debt_list = debt_list_sql.order_by(user_debts.BuyDate.desc(), user_debts.DebtdealId.desc()).limit(limit).offset(offset).all()
        record_list = [{"PolicyName":debt.PolicyName,
            "ListingId":debt.ListingId,
            "PriceForSaleRate":debt.PriceForSaleRate,
            "PriceForSale":debt.PriceForSale,
            "BuyDate":str(debt.BuyDate),
            "User":debt.User if debt.User else '空'
        } for debt in debt_list]

        return '{"success":["查询成功"], "record_list":{"record_list":%s, "policy_name":"%s", "start_date":"%s", "end_date":"%s", "current_page":%s, "total_page":%s}}' % (str(record_list).replace("'",'"'), policy_name, start_date, end_date, current_page, total_page)

    elif form.validate_on_submit():
        if form.policy_name.data:
            policy_name = form.policy_name.data
            debt_list_sql = debt_list_sql.filter(user_debts.PolicyName == policy_name)
        if form.submit_today_filter.data:
            start_date = end_date = str(today)
            debt_list_sql = debt_list_sql.filter(user_debts.BuyDate >= start_date, user_debts.BuyDate <= end_date)
        elif form.submit_date_filter.data:
            try:
                start_date, end_date = str(form.start_date.data), str(form.end_date.data)
                debt_list_sql = debt_list_sql.filter(user_debts.BuyDate >= start_date, user_debts.BuyDate <= end_date)
            except:
                return '{"danger":["查询失败，请检查您所输入的日期格式是否正确！"]}'
        # 采用 with_entities 方法，可以使用 sql 原生函数，利于优化性能
        count = debt_list_sql.with_entities(func.count(user_debts.DebtdealId)).scalar()
        debt_list = debt_list_sql.order_by(user_debts.BuyDate.desc(), user_debts.DebtdealId.desc()).limit(limit).offset(offset).all()
        record_list = [{"PolicyName":debt.PolicyName,
            "ListingId":debt.ListingId,
            "PriceForSaleRate":debt.PriceForSaleRate,
            "PriceForSale":debt.PriceForSale,
            "BuyDate":str(debt.BuyDate),
            "User":debt.User if debt.User else '空'
        } for debt in debt_list]

        return '{"success":["查询成功"], "record_list":{"record_list":%s, "policy_name":"%s", "start_date":"%s", "end_date":"%s", "count":%s, "limit":%s, "current_page":1}}' % (str(record_list).replace("'",'"'), policy_name, start_date, end_date, count, limit)

    else:
        if form.errors:
            errors_list = [f"{form[field].label.text}：{', '.join(errors)}" for field, errors in form.errors.items()]
            return json.dumps({"danger":errors_list})
        # 默认查询今日购债记录
        start_date = end_date = str(today)
        debt_list_sql = debt_list_sql.filter(user_debts.BuyDate >= start_date, user_debts.BuyDate <= end_date)
        count = debt_list_sql.with_entities(func.count(user_debts.DebtdealId)).scalar()

    debt_list = debt_list_sql.order_by(user_debts.BuyDate.desc(), user_debts.DebtdealId.desc()).limit(limit).offset(offset).all()
    db.session.commit()

    return render_template('debt_list.html', form=form, debt_list=debt_list, count=count, offset=offset, limit=limit, policy_name=policy_name, start_date=start_date, end_date=end_date)

# 当日预警
@account.route('/warning/<name>', methods=['GET', 'POST'])
@login_required
def warning(name=None):
    #offset = int(request.args.get('offset', 0))
    #limit = int(request.args.get('limit', 20))
    today = date.today()
    offset = 0
    limit = 20
    # 读取列表信息
    user_lists = gentable(current_user.Name, '_Lists')  # 动态建表
    lists_sql = user_lists.query

    # 策略自选
    class WarningForm(FlaskForm):
        start_date = DateField('起始日期', format='%Y-%m-%d', default=today)
        end_date = DateField('截止日期', format='%Y-%m-%d', default=today)

        submit_today_filter = SubmitField('今日查询')
        submit_date_filter = SubmitField('日期查询')
        submit_get = SubmitField('获取信息')

    form = WarningForm()
    start_date = end_date = ''

    if request.args:
        offset, limit, count = int(request.args.get('offset')), int(request.args.get('limit')), int(request.args.get('count'))
        if request.args.get('startDate'):
            start_date, end_date = request.args.get('startDate'), request.args.get('endDate')
            lists_sql = lists_sql.filter(user_lists.InfoUpdateTime >= start_date, user_lists.InfoUpdateTime <= end_date)
    elif form.validate_on_submit():
        if form.submit_today_filter.data:
            start_date = end_date = str(today)
            lists_sql = lists_sql.filter(user_lists.InfoUpdateTime >= start_date, user_lists.InfoUpdateTime <= end_date)
        elif form.submit_date_filter.data:
            try:
                start_date, end_date = str(form.start_date.data), str(form.end_date.data)
                lists_sql = lists_sql.filter(user_lists.InfoUpdateTime >= start_date, user_lists.InfoUpdateTime <= end_date)
            except:
                flash('查询失败，请检查您所输入的日期格式是否正确！','danger')
                return render_template('warning.html', form=form, warning_list=None, count=0, offset=0, limit=0, start_date=start_date, end_date=end_date)
        elif form.submit_get.data:
            now = str(today)
            if now != current_user.WarningUpdateTime:
                logger(f'开始更新 {current_user.Name} 的预警数据')
                current_user.OverdueUpdateStamp = stamp_now
                db.session.commit()

                async def get_warning(bid_lists):
                    bid_lists_split = [bid_lists[i:i+bid_lists_split_len] for i in range(0, len(bid_lists), bid_lists_split_len)]  # 分割列表，便于循环更新请求头及保存数据到数据库

                    url = "https://openapi.ppdai.com/creditor/openapi/fetchLenderRepayment"
                    sign_decode_get_overdue = 'S+GZ4Cx08eGWUWAEzEVex4FdGX9aHLcDb1sVcMvvQ2IlHw0d6nviFqB1yv6rIOxCo+tRtTtXU89AoUg17+t6IXy1gsesJiD8pvv7MJCINXcNd15Kg1cGwviKfYnQtvcupKZJM62m5pSTBWXUGdAtymZmR2Wl/eQmSbNEo0pR7bg='
                    access_token = current_user.AccessToken
                    timeout = aiohttp.ClientTimeout(total=20)
                    #sem = asyncio.Semaphore(coroutine_burst)  # 控制并发数
                    async with aiohttp.ClientSession() as session:

                        @limit_time_get_overdue
                        async def _get_overdue(bid_list):
                            utctime = datetime.utcnow()
                            timestamp = utctime.strftime('%Y-%m-%d %H:%M:%S')
                            headers = {
                                "X-PPD-APPID":appid,
                                "X-PPD-TIMESTAMP":timestamp,
                                "X-PPD-TIMESTAMP-SIGN":rsa.sign("%s%s" % (appid, timestamp)).decode(),
                                "X-PPD-SIGN":sign_decode_get_overdue,
                                "Accept":"application/json;charset=UTF-8"
                                }

                            async def client_send(bid):
                                resp = await client.send(session, timeout, url, json.dumps({"ListingId":bid.ListingId}), headers, access_token)
                                return bid, resp

                            future_overdue = [client_send(bid) for bid in bid_list]
                            for each in asyncio.as_completed(future_overdue):
                                bid, resp = await each
                                if resp:  # 防止响应为空
                                    result = json.loads(resp)
                                    if result['ListingRepayment']:
                                        OverdueDays = max(int(each['OverdueDays']) for each in result['ListingRepayment'])
                                        if OverdueDays > 0:
                                            bid.Black = OverdueDays
                            db.session.commit()

                        for bid_list in bid_lists_split:
                            await _get_overdue(bid_list)
                        logger(f'{current_user.Name} 的预警数据更新成功')

                user_bids = gentable(current_user.Name, 'Lists')  # 动态建表
                user_bids.query.update({'PayBack':PayBack, 'PayBack':PayBack, 'OwingAmount':OwingAmount, 'BalAmount':BalAmount, 'OverdueType':OverdueType, 'WarningLevel':WarningLevel, 'InfoUpdateTime':str(today)})
                db.session.commit()

                bid_lists = user_bids.query.all()
                loop_task(get_warning(bid_lists))
                flash('预警数据更新成功','success')
            else:
                flash('今日重复获取预警数据，请改日再试！','danger')
                return render_template('warning.html', form=form, warning_list=None, count=0, offset=0, limit=0, start_date=start_date, end_date=end_date)
        # 采用 with_entities 方法，可以使用 sql 原生函数，利于优化性能
        count = lists_sql.with_entities(func.count(user_lists.ListingId)).scalar()
    else:
        # 默认查询今日更新预警数据
        start_date = end_date = str(today)
        lists_sql = lists_sql.filter(user_lists.InfoUpdateTime >= start_date, user_lists.InfoUpdateTime <= end_date)
        count = lists_sql.with_entities(func.count(user_lists.ListingId)).scalar()

    warning_list = lists_sql.limit(limit).offset(offset).all()
    db.session.commit()

    return render_template('warning.html', form=form, warning_list=warning_list, count=count, offset=offset, limit=limit, start_date=start_date, end_date=end_date)

# 购买债权
@account.route('/buy-debt/<name>', methods=['GET', 'POST'])
@login_required
def buy_debt(name=None):

    class BuyDebtForm(FlaskForm):
        request_interval_market = DecimalField('市场间隔(秒)', validators=[NumberRange(min=0, max=20, message=f'输入区间为：0.01~20.00')], places=2, default=2.2)
        request_interval_api = DecimalField('接口间隔(秒)', validators=[NumberRange(min=0, max=20, message=f'输入区间为：0.01~20.00')], places=2, default=6.1)
        waiting_time_for_rerty = IntegerField('重试间隔(秒)', validators=[NumberRange(min=60, max=1200, message='输入必须为整数，且在 60~1200 之间')], default=60)
        rate = DecimalField('利率', validators=[NumberRange(min=0, max=99, message='输入区间为：0.01~99.00')], places=1, default=11)
        submit_refresh = SubmitField('刷新')
        submit_exit = SubmitField('停止')

    form = BuyDebtForm()

    if form.validate_on_submit():
        if form.submit_refresh.data:
            request_interval_market = float(form.request_interval_market.data)
            request_interval_api = float(form.request_interval_api.data)
            waiting_time_for_rerty = form.waiting_time_for_rerty.data
            rate = float(form.rate.data)

            module_logger.warning(f'开始抢购赔标债权，利率 {rate} 以上')
            loop = Loop()
            buy_debt = BuyDebt(loop, waiting_time_for_rerty)
            loop.add_future_loop(request_interval_market, buy_debt.refresh_debt(rate, request_interval_market), loop_host='transfer.ppdai.com', create_free_sockets=6, min_free_sockets=4, max_free_sockets=20)
            loop.add_future_loop(request_interval_api, buy_debt.refresh_debt_api(rate, request_interval_api), loop_host='openapi.ppdai.com', create_free_sockets=3, min_free_sockets=1, max_free_sockets=5)
            loop.run_forever()
        else:
            if os.path.exists('AutoReload.py'):
                with open('AutoReload.py', 'r+') as f:
                    f.write('#')

    return render_template('buy_debt.html', form=form)

# 账户信息
@account.route('user-info/<name>', methods=['GET', 'POST'])
@login_required
def user_info(name=None):
    form = SwitchForm()
    if form.validate_on_submit():
        if form.submit_bid.data:
            try:
                current_user.BidSwitch = not current_user.BidSwitch
                db.session.commit()
                return '{"success":["总投标状态修改成功"]}'
            except:
                return '{"danger":["总投标状态修改成功失败，请联系管理员处理数据异常！"]}'
        elif form.submit_over_due.data:
            try:
                current_user.GetOverDueTimes = 30
                db.session.commit()
                return '{"success":["获取逾期次数修改成功"]}'
            except:
                return '{"danger":["获取逾期次数修改成功失败，请联系管理员处理数据异常！"]}'
        else:
            try:
                current_user.DebtSwitch = not current_user.DebtSwitch
                db.session.commit()
                return '{"success":["总债转状态修改成功"]}'
            except:
                return '{"danger":["总债转状态修改成功失败，请联系管理员处理数据异常！"]}'
    return render_template('user_info.html', form=form, admin_list=admin_list)

# 授权管理
@account.route('/authorize/<name>', methods=['GET', 'POST'])
@login_required
def authorize(name=None):
    futures_running = set()
    balance_url = "https://openapi.ppdai.com/balance/balanceService/QueryBalance"
    authorize_binding_dict = json.loads(current_user.AuthorizeBinding) if current_user.AuthorizeBinding else {}
    authorize_binding_list = [(k, k) for k in authorize_binding_dict]
    authorize_binding_list.insert(0, ('', '请选择'))

    # 授权管理
    class AuthorizeForm(FlaskForm):
        authorize_binding = SelectField('授权列表', choices=authorize_binding_list)
        authorize_name = StringField('授权名称', validators=[Optional(), Length(min=1, max=20, message='授权名称长度为1~20个字节，请正确输入')], render_kw={"placeholder":"授权名称", "onfocus":"this.placeholder=''", "onblur":"this.placeholder='授权名称'"})
        submit_new = SubmitField('新建授权')
        submit_auth = SubmitField('开启授权')
        submit_del = SubmitField('删除授权')
        submit_balance = SubmitField('查询余额')
        submit_bid = SubmitField('关闭投标')
        submit_debt = SubmitField('关闭购债')


    async def get_save_user_balance(headers):
        future_balance = []
        async with aiohttp.ClientSession() as session:
            for bind_name, bind_info in authorize_binding_dict.items():
                if bind_info["Authorized"]:
                    headers_bind = headers.copy()
                    headers_bind['X-PPD-ACCESSTOKEN'] = bind_info['AccessToken']
                    future_balance.append(_get_save_user_balance(session, authorize_binding_dict[bind_name], headers_bind))
            for each in asyncio.as_completed(future_balance):
                await each

    async def _get_save_user_balance(session, bind_info, headers):
        async with session.post(balance_url, headers=headers, data='{}') as resp:
            res = await resp.text()
            if res:
                result = json.loads(res)
                if result.get("Result") == 0:
                    bind_info['Balance'] = result['Balance'][0]['Balance']


    form = AuthorizeForm()
    if form.validate_on_submit():
        if form.submit_balance.data:
            from open_api.core.rsa_client import rsa_client as rsa

            timestamp = str(datetime.utcnow())[:19]
            headers = {
                "X-PPD-APPID":appid,
                "X-PPD-TIMESTAMP":timestamp,
                "X-PPD-TIMESTAMP-SIGN":rsa.sign(appid+timestamp).decode(),
                "X-PPD-SIGN":"S+GZ4Cx08eGWUWAEzEVex4FdGX9aHLcDb1sVcMvvQ2IlHw0d6nviFqB1yv6rIOxCo+tRtTtXU89AoUg17+t6IXy1gsesJiD8pvv7MJCINXcNd15Kg1cGwviKfYnQtvcupKZJM62m5pSTBWXUGdAtymZmR2Wl/eQmSbNEo0pR7bg=",
                "Accept":"application/json;charset=UTF-8",
                "Connection":"keep-alive",
                "Cache-Control":"no-cache",
                "Accept-Language":"en-US,en;q=0.8,zh-CN;q=0.6,zh;q=0.4",
                "Content-Type":"application/json;charset=utf-8"
                }

            loop_task(get_save_user_balance(headers))

            current_user.AuthorizeBinding = str(authorize_binding_dict).replace('\'', '\"').replace(' ','')
            db.session.commit()
            content = str([{"id":bind_name, "balance":bind_info["Balance"]} for bind_name, bind_info in authorize_binding_dict.items() if bind_info["Authorized"]]).replace('\'', '\"').replace(' ','')
            return '{"success":["拍拍贷余额查询成功"], "content":%s}' % content
        authorize_name = form.authorize_binding.data or form.authorize_name.data
        if authorize_name:
            if form.submit_bid.data:
                policy_dict = json.loads(current_user.Policy)
                for policy_type, policys in policy_dict.items():
                    for policy_name, policy_info in policys.items():
                        try:
                            policy_info['AuthorizeBinding'].remove(authorize_name)
                        except:
                            pass
                current_user.Policy = str(policy_dict).replace("'",'"')
                db.session.commit()
                return '{"success":["%s 投标功能关闭成功，解除与所有散标策略的绑定关系。"]}' % authorize_name
            elif form.submit_debt.data:
                authorize_binding_dict[authorize_name]['Debt'] = int(not authorize_binding_dict[authorize_name]['Debt']) if 'Debt' in authorize_binding_dict[authorize_name] else 1
                if not authorize_binding_dict[authorize_name]['Debt']:
                    policy_dict = json.loads(current_user.DebtPolicy)
                    for policy_type, policys in policy_dict.items():
                        for policy_name, policy_info in policys.items():
                            try:
                                policy_info['AuthorizeBinding'].remove(authorize_name)
                            except:
                                pass
                    current_user.DebtPolicy = str(policy_dict).replace("'",'"')
                current_user.AuthorizeBinding = str(authorize_binding_dict).replace("'",'"')
                db.session.commit()
                return '{"success":["%s 购债功能关闭成功，解除与所有债权策略的绑定关系。"]}' % authorize_name
            elif form.submit_auth.data:
                for bind_name, bind_info in authorize_binding_dict.items():
                    bind_info['State'] = 1
                authorize_binding_dict[authorize_name]['State'] = 0
                current_user.AuthorizeBinding = str(authorize_binding_dict).replace("'",'"')
                db.session.commit()
                return '{"success":["%s 已被设为待授权状态，请授权！"]}' % authorize_name
            elif form.submit_del.data:
                policy_dict = json.loads(current_user.Policy)
                for policy_type, policys in policy_dict.items():
                    for policy_name, policy_info in policys.items():
                        try:
                            policy_info['AuthorizeBinding'].remove(authorize_name)
                        except:
                            pass
                current_user.Policy = str(policy_dict).replace("'",'"')

                policy_dict = json.loads(current_user.DebtPolicy)
                for policy_type, policys in policy_dict.items():
                    for policy_name, policy_info in policys.items():
                        try:
                            policy_info['AuthorizeBinding'].remove(authorize_name)
                        except:
                            pass
                current_user.DebtPolicy = str(policy_dict).replace("'",'"')

                del authorize_binding_dict[authorize_name]
                current_user.AuthorizeBinding = str(authorize_binding_dict).replace("'",'"')
                db.session.commit()
                return '{"warning":["%s 授权删除成功"]}'% authorize_name
            else:
                if authorize_name not in authorize_binding_dict:
                    if len(authorize_binding_dict) >= max_authorize_binding:
                        return '{"danger":["授权数量已达上限，请使用已有授权绑定拍拍贷账户信息！"]}'
                    authorize_binding_dict[authorize_name] = {}
                    authorize_binding_dict[authorize_name]['Authorized'] = 0
                    authorize_binding_dict[authorize_name]['Balance'] = 1000
                    current_user.AuthorizeBinding = str(authorize_binding_dict).replace("'",'"')
                    db.session.commit()
                    return '{"success":["%s 新建授权成功"]}' % authorize_name
                else:
                    return '{"danger":["新建授权失败，授权已存在，请更换名称后，再执行相关操作！"]}'
        else:
            return '{"danger":["请选择一个授权或填入新授权名称后，再执行相关操作！"]}'
    else:
        if form.errors:
            errors_list = [f"{form[field].label.text}：{', '.join(errors)}" for field, errors in form.errors.items()]
            return json.dumps({"danger":errors_list})

    return render_template('authorize.html', form=form, authorize_binding_dict=authorize_binding_dict)

# 模拟授权
@account.route('/http-authorize/<name>', methods=['GET', 'POST'])
@login_required
def http_authorize(name=None):
    import requests

    loginHeaders = {
            "Host":"ac.ppdai.com",
            "Connection":"keep-alive",
            "Accept":"*/*",
            "Origin":"https://ac.ppdai.com",
            "X-Requested-With":"XMLHttpRequest",
            "User-Agent":"Mozilla/5.0 (Windows NT 6.1) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/63.0.3239.26 Safari/537.36 Core/1.63.5050.400 QQBrowser/10.0.941.400",
            "Content-Type":"application/x-www-form-urlencoded",
            "Referer":"https://ac.ppdai.com/User/Login?Redirect=https://m.invest.ppdai.com/user/UserProfitCenter",
            "Accept-Encoding":"gzip, deflate, br",
            "Accept-Language":"zh-CN,zh;q=0.9"
        }
    authorize_binding_dict = json.loads(current_user.AuthorizeBinding)
    authorize_binding_list = [(k, k) for k in authorize_binding_dict]
    authorize_binding_list.insert(0, ('', '请选择'))

    # 策略管理
    class HttpAuthorizeForm(FlaskForm):
        ValidateCode = StringField('验证码', validators=[Optional(), Length(min=4, max=4, message='验证码长度为4个字节，请输入正确的格式')])
        PPDID = StringField('拍拍贷账户', validators=[Optional(), Length(min=1, max=25, message='账户长度为1~25个字节，请正确输入')], render_kw={"placeholder":"拍拍贷账户", "onfocus":"this.placeholder=''", "onblur":"this.placeholder='拍拍贷账户'"})
        PPDPW = StringField('拍拍贷密码', validators=[Optional(), Length(min=1, max=36, message='密码长度为1~36个字节，请正确输入')], render_kw={"placeholder":"拍拍贷密码", "type":"password", "onfocus":"this.placeholder=''", "onblur":"this.placeholder='拍拍贷密码'", "onmouseover":"this.type='text'", "onmouseout":"this.type='password'"})
        PPDUN = StringField('拍拍贷用户', validators=[Optional(), Length(min=1, max=25, message='账户长度为1~25个字节，请正确输入')], render_kw={"placeholder":"拍拍贷用户", "onfocus":"this.placeholder=''", "onblur":"this.placeholder='拍拍贷用户'"})
        authorize_binding = SelectField('授权列表', choices=authorize_binding_list)
        submit_commit = SubmitField('获取令牌')
        submit_save = SubmitField('绑定帐密')

    form = HttpAuthorizeForm()
    if form.validate_on_submit():
        authorize_name = form.authorize_binding.data
        if authorize_name:
            authorize_binding_info = authorize_binding_dict[authorize_name]
        else:
            return '{"danger":["未选择授权，请先填写或选择一个授权"]}'
        if form.submit_commit.data:
            if authorize_binding_info.get('PPDID') and authorize_binding_info.get('PPDPW'):
                ValidateCode = form.ValidateCode.data
                if ValidateCode:
                    loginUrl = 'https://ac.ppdai.com/User/Login'
                    loginData = {'IsAsync':'true', 'Redirect':'https://tz.ppdai.com/account/indexV2', 'UserName':authorize_binding_info['PPDID'], 'Password':authorize_binding_info['PPDPW'], 'RememberMe':'true', 'ValidateCode':int(ValidateCode)}
                    # 读取并赋值临时 cookies
                    cookies_temp = json.loads(current_user.CookiesTemp)
                    with requests.Session() as session:
                        session_cookies = requests.cookies.RequestsCookieJar()
                        session_cookies.set('uniqueid', cookies_temp['uniqueid'], domain='.ppdai.com')
                        session_cookies.set('aliyungf_tc', cookies_temp['aliyungf_tc'], domain='ac.ppdai.com')
                        session.cookies = session_cookies
                        with session.post(loginUrl, headers=loginHeaders, data=loginData, verify=False) as resp:
                            res = resp.json()
                            if res.get('Code') == 1:
                                authorize_binding_info['PPDUN'] = resp.cookies['ppd_uname']
                                authorize_binding_info['Cookies'] = 'token=' + resp.cookies['token']
                                authorize_binding_info['CookiesEnable'] = 1
                                for bind_name, bind_info in authorize_binding_dict.items():
                                    if bind_info.get('CookiesEnable') == 0:
                                        current_user.HttpAuthorized = 1
                                        break
                                else:
                                    current_user.HttpAuthorized = 2
                                current_user.AuthorizeBinding = str(authorize_binding_dict).replace("'",'"')
                                db.session.commit()
                                return '{"success":["%s 授权 %s 令牌获取成功"], "policy":{"id":"%s", "state":"有效"}}' % (authorize_name, authorize_binding_info['PPDID'], authorize_name)
                            else:
                                return '{"danger":["令牌获取失败，验证码不正确"]}'
                else:
                    return '{"danger":["令牌获取失败，验证码为空，请填入图中所示的数字或字母"]}'
            else:
                return '{"danger":["拍拍贷帐密为空，请先保存帐密"]}'
        else:
            if form.PPDID.data and form.PPDPW.data:
                if authorize_binding_info.get('BindingDate') != date.today().month:
                    authorize_binding_info['BindingDate'] = date.today().month
                    authorize_binding_info['PPDID'] = form.PPDID.data
                    authorize_binding_info['PPDPW'] = form.PPDPW.data
                    current_user.AuthorizeBinding = str(authorize_binding_dict).replace("'",'"')
                    db.session.commit()
                    return '{"success":["%s 绑定 %s 账户成功"], "policy":{"id":"%s", "PPDID":"%s"}}' % (authorize_name, authorize_binding_info['PPDID'], authorize_name, form.PPDID.data)
                else:
                    return '{"danger":["绑定账户失败，本月已绑定过账户，请下个月再试。"]}'
            elif form.PPDUN.data:
                if authorize_binding_info.get('BindingDate') != date.today().month:
                    authorize_binding_info['BindingDate'] = date.today().month
                    authorize_binding_info['PPDUN'] = form.PPDUN.data
                    current_user.AuthorizeBinding = str(authorize_binding_dict).replace("'",'"')
                    db.session.commit()
                    return '{"success":["%s 绑定 %s 用户成功"], "policy":{"id":"%s", "PPDUN":"%s"}}' % (authorize_name, authorize_binding_info['PPDUN'], authorize_name, form.PPDUN.data)
                else:
                    return '{"danger":["绑定用户失败，本月已绑定过用户，请下个月再试。"]}'
            else:
                return '{"danger":["绑定失败，拍拍贷帐密、用户名均为空"]}'
    else:
        if form.errors:
            errors_list = [f"{form[field].label.text}：{', '.join(errors)}" for field, errors in form.errors.items()]
            return json.dumps({"danger":errors_list})

    import random
    import base64
    captcha_url = "https://ac.ppdai.com/ValidateCode/Image?tmp=" + str(random.random())
    with requests.get(captcha_url, headers=loginHeaders, verify=False) as resp:
        image_byte = resp.content
        # 保存临时 cookies
        current_user.CookiesTemp = str(requests.utils.dict_from_cookiejar(resp.cookies)).replace('\'', '\"').replace(' ','')
        db.session.commit()
    img_b64_string = base64.b64encode(image_byte).decode()
    return render_template('http_authorize.html', form=form, img_b64_string=img_b64_string, authorize_binding_dict=authorize_binding_dict)

# 充值提现
@account.route('/pay/<name>', methods=['GET', 'POST'])
@login_required
def pay(name=None):
    from decimal import Decimal

    form = PayForm()
    if form.validate_on_submit() and current_user.Name in admin_list:
        user = Users.query.filter_by(Name=form.name.data).first()
        if user:
            if form.pay_amount.data and form.submit_pay.data:
                user.CC = user.CC + form.pay_amount.data
                user.TotalCC = int(user.TotalCC + form.pay_amount.data)
                db.session.commit()
                #flash('充值成功，测试充值代码，正式上线须屏蔽','danger')
                #return redirect(url_for('account.index',name=current_user.Name))

                if user.AlertWeiXin:
                    import requests

                    url = 'http://u.ifeige.cn/api/message/send-user'
                    headers = {"content-type":"application/json"}
                    data = {
                        'secret': 'c0f7bf6c5017745d351372afaf1fb9a8',
                        'uid': json.loads(user.AlertWeiXin)['uid'],
                        'template_id': 'hyiStj66j7bgtgVRgQ7bWjKfO3-fZE9M3Q1zL9DiLuo',
                        'data': {
                            'first': {
                                'value': '拍拍猫充值成功',
                                'color': '#173177'
                            },
                            'keyword1': {
                                'value': f'{form.name.data}_{date.today()}',
                                'color': '#173177'
                            },
                            'keyword2': {
                                'value': '充值金额',
                                'color': '#173177'
                            },
                            'keyword3': {
                                'value': str(form.pay_amount.data.quantize(Decimal('0.0'))),
                                'color': '#173177'
                            },
                            'remark': {
                                'value': '感谢您的支持！',
                                'color': '#173177'
                            }
                        }
                    }
                    while 1:
                        with requests.post(url, headers=headers, data=json.dumps(data)) as resp:
                            result = resp.json()
                            if result.get('code') == 200:
                                break
                            elif result.get('code') == 10010:
                                logger(f"\033[46;1m信息发送对象不存在！\033[0m")
                                user.AlertWeiXin = ''
                                db.session.commit()
                                break
                        logger(f"\033[46;1m充值信息发送失败，600秒后重试！\033[0m{result}")
                        time.sleep(600)

                return '{"success":["账户：%s&nbsp;&nbsp;充值金额：%s 元"]}' % (form.name.data, form.pay_amount.data)
            elif form.authorize_binding.data and form.submit_verify_true.data:
                authorize_binding_dict = json.loads(user.AuthorizeBinding)
                if form.authorize_binding.data in authorize_binding_dict:
                    authorize_binding_dict[form.authorize_binding.data]['Verify'] = 1
                    user.AuthorizeBinding = str(authorize_binding_dict).replace("'",'"')
                    db.session.commit()
                    return '{"success":["账户：%s&nbsp;&nbsp;授权名：%s&nbsp;&nbsp;贷后授权成功"]}' % (form.name.data, form.authorize_binding.data)
                else:
                    return '{"danger":["授权名不存在，请确认输入是否正确"]}'
            elif form.authorize_binding.data and form.submit_verify_false.data:
                authorize_binding_dict = json.loads(user.AuthorizeBinding)
                if form.authorize_binding.data in authorize_binding_dict:
                    authorize_binding_dict[form.authorize_binding.data]['Verify'] = 0
                    user.AuthorizeBinding = str(authorize_binding_dict).replace("'",'"')
                    db.session.commit()
                    return '{"success":["账户：%s&nbsp;&nbsp;授权名：%s&nbsp;&nbsp;贷后停权成功"]}' % (form.name.data, form.authorize_binding.data)
                else:
                    return '{"danger":["授权名不存在，请确认输入是否正确"]}'
            else:
                return '{"danger":["操作失败，请确认充值金额或授权名不为空"]}'
        else:
            return '{"danger":["账户不存在，请确认输入是否正确"]}'
    else:
        if form.errors:
            errors_list = [f"{form[field].label.text}：{', '.join(errors)}" for field, errors in form.errors.items()]
            return json.dumps({"danger":errors_list})

    return render_template('pay.html', form=form)

# 修改密码
@account.route('/modify-pw/<name>', methods=['GET', 'POST'])
@login_required
def modify_pw(name=None):
    form = ModifyPasswordForm()
    if form.validate_on_submit():
        import hashlib
        if current_user.Password == hashlib.md5(form.old_password.data.encode()).hexdigest():
            current_user.Password = hashlib.md5(form.new_password.data.encode()).hexdigest()
            db.session.commit()
            logger(f'{current_user.Name} 密码修改成功')
            return '{"success":["密码修改成功"]}'
        else:
            return '{"danger":["密码错误"]}'
    return render_template('modify-pw.html', form=form)

# 更新日志
@account.route('/app-log')
@login_required
@cached(timeout=86400)
def app_log():
    return render_template('app_log.html')

# 软件下载
@account.route('/download')
@login_required
@cached(timeout=86400)
def download():
    if request.args:
        file_name = request.args.get('filename')
        directory = os.getcwd() + '/download'
        response = make_response(send_from_directory(directory, file_name, as_attachment=True))
        response.headers["Content-Disposition"] = f"attachment; filename={file_name.encode().decode('latin-1')}"
        return response
    return render_template('download.html')

def loop_task(func):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            result = asyncio.ensure_future(func)
            while not result.done():
                time.sleep(1)
        else:
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            result = loop.run_until_complete(func)
            loop.close()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(func)
        loop.close()
    return result

#在您的应用当中以一个显式调用 SQLAlchemy , 您只需要将如下代码放置在您应用 的模块中。Flask 将会在请求结束时自动移除数据库会话
@app.teardown_request
def shutdown_session(exception=None):
    db.session.remove()