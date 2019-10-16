#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2017/8/1 14:45
# @File    : Model.py
"""
数据模型

"""

from flask_login import UserMixin
from Start_multi_datetime import db


class Users(UserMixin, db.Model):

    '''
    可选参数       描述
    primary_key    如果设置为True，则为该列表的主键
    unique         如果设置为True，该列不允许相同值
    index          如果设置为True，为该列创建索引，查询效率会更高
    nullable       如果设置为True，该列允许为空。如果设置为False，该列不允许空值
    default        定义该列的默认值
    '''


    __tablename__ = 'Users'#对应数据库表
    ID = db.Column(db.Integer, primary_key=True)
    Name = db.Column(db.String(25), unique=True, index=True)
    Password = db.Column(db.String(36), unique=False, index=True)
    CC = db.Column(db.DECIMAL(11,6), unique=False, default=0, index=True) # 猫币余额
    Balance = db.Column(db.Integer, unique=False, default=2, index=True)  # 拍拍贷账户状态，0：所有绑定账户余额不足，1：部分不足，2：全部充足
    Policy = db.Column(db.String(13000), unique=False, default='{"系统策略":{},"自选策略":{}}', index=True)  # 散标策略
    BidSwitch = db.Column(db.Boolean, unique=False, default=True, index=True)  # 投标总开关
    DebtPolicy = db.Column(db.String(5000), unique=False, default='{"系统策略":{},"自选策略":{}}', index=True)  # 债权策略
    DebtSwitch = db.Column(db.Boolean, unique=False, default=True, index=True)  # 债转总开关
    Authorized = db.Column(db.Integer, unique=False, default=0, index=True)  # 拍拍贷账户授权状态，0：均未授权，1：部分授权，2：全部授权
    HttpAuthorized = db.Column(db.Integer, unique=False, default=0, index=True)  # 拍拍贷账户授权状态，0：均未授权，1：部分授权，2：全部授权
    CookiesTemp = db.Column(db.String(200), unique=False, index=True)
    AlertWeiXin = db.Column(db.String(200), unique=False, index=True)
    TotalCC = db.Column(db.Integer, unique=False, default=0, index=True)  # 猫币充值总额
    AuthorizeBinding = db.Column(db.String(2000), unique=False, index=True, default='{}')  # 授权绑定的拍拍贷账户
    OpenIdBinding = db.Column(db.String(500), unique=False, index=True)  # 本账户曾经绑定过的拍拍贷账户的 OpenId
    GetOverDueTimes = db.Column(db.Integer, unique=False, default=0, index=True)
    WarningUpdateTime = db.Column(db.Date, unique=False, index=True)

    def __init__(self, name, password):
        self.Name = name
        self.Password = password

    def get_id(self):
        return str(self.ID)

    def __repr__(self):
        return '<User %r>' % self.Name

    def is_authenticated(self):
        return True

    def is_active(self):
        return True

    def is_anonymous(self):
        return False


class AllBids(db.Model):

    '''
    可选参数       描述
    primary_key    如果设置为True，则为该列表的主键
    unique         如果设置为True，该列不允许相同值
    index          如果设置为True，为该列创建索引，查询效率会更高
    nullable       如果设置为True，该列允许为空。如果设置为False，该列不允许空值
    default        定义该列的默认值
    '''


    __tablename__ = 'All_Bids'#对应mysql数据库表
    ListingId = db.Column(db.Integer, primary_key=True)
    CreditCode = db.Column(db.String(2), unique=False, index=True)
    Amount = db.Column(db.Integer, unique=False, index=True)
    CurrentRate = db.Column(db.Integer, unique=False, index=True)
    Months = db.Column(db.Integer, unique=False, index=True)
    Gender = db.Column(db.Integer, unique=False, index=True)
    Age = db.Column(db.Integer, unique=False, index=True)
    EducationDegree = db.Column(db.String(12), unique=False, index=True)
    GraduateSchool = db.Column(db.String(60), unique=False, index=True)
    StudyStyle = db.Column(db.String(10), unique=False, index=True)
    CertificateValidate = db.Column(db.Boolean, unique=False, index=True)
    CreditValidate = db.Column(db.Boolean, unique=False, index=True)
    NciicIdentityCheck = db.Column(db.Boolean, unique=False, index=True)
    SuccessCount = db.Column(db.Integer, unique=False, index=True)
    WasteCount = db.Column(db.Integer, unique=False, index=True)
    CancelCount = db.Column(db.Integer, unique=False, index=True)
    FailedCount = db.Column(db.Integer, unique=False, index=True)
    NormalCount = db.Column(db.Integer, unique=False, index=True)
    OverdueLessCount = db.Column(db.Integer, unique=False, index=True)
    OverdueMoreCount = db.Column(db.Integer, unique=False, index=True)
    TotalPrincipal = db.Column(db.Integer, unique=False, index=True)
    OwingPrincipal = db.Column(db.Float, unique=False, index=True)
    OwingAmount = db.Column(db.Float, unique=False, index=True)
    AmountToReceive = db.Column(db.Float, unique=False, index=True)
    HighestPrincipal = db.Column(db.Integer, unique=False, index=True)
    HighestDebt = db.Column(db.Float, unique=False, index=True)
    FirstRegTime = db.Column(db.Integer, unique=False, index=True)
    NowLastTime = db.Column(db.Integer, unique=False, index=True)


    def __init__(self, **kwargs):
        self.ListingId = kwargs.get('ListingId')
        self.CreditCode = kwargs.get('CreditCode')
        self.Amount = kwargs.get('Amount')
        self.CurrentRate = kwargs.get('CurrentRate')
        self.Months = kwargs.get('Months')
        self.Gender = kwargs.get('Gender')
        self.Age = kwargs.get('Age')
        self.EducationDegree = kwargs.get('EducationDegree')
        self.GraduateSchool = kwargs.get('GraduateSchool')
        self.StudyStyle = kwargs.get('StudyStyle')
        self.CertificateValidate = kwargs.get('CertificateValidate')
        self.CreditValidate = kwargs.get('CreditValidate')
        self.NciicIdentityCheck = kwargs.get('NciicIdentityCheck')
        self.SuccessCount = kwargs.get('SuccessCount')
        self.WasteCount = kwargs.get('WasteCount')
        self.CancelCount = kwargs.get('CancelCount')
        self.FailedCount = kwargs.get('FailedCount')
        self.NormalCount = kwargs.get('NormalCount')
        self.OverdueLessCount = kwargs.get('OverdueLessCount')
        self.OverdueMoreCount = kwargs.get('OverdueMoreCount')
        self.TotalPrincipal = kwargs.get('TotalPrincipal')
        self.OwingPrincipal = kwargs.get('OwingPrincipal')
        self.OwingAmount = kwargs.get('OwingAmount')
        self.AmountToReceive = kwargs.get('AmountToReceive')
        self.HighestPrincipal = kwargs.get('HighestPrincipal')
        self.HighestDebt = kwargs.get('HighestDebt')
        self.FirstRegTime = kwargs.get('FirstRegTime')
        self.NowLastTime = kwargs.get('NowLastTime')

    def get_id(self):
        return str(self.ListingId)

    def __repr__(self):
        return f'编号：{self.ListingId}'


"""class UserBids(db.Model):

        '''
        可选参数       描述
        primary_key    如果设置为True，则为该列表的主键
        unique         如果设置为True，该列不允许相同值
        index          如果设置为True，为该列创建索引，查询效率会更高
        nullable       如果设置为True，该列允许为空。如果设置为False，该列不允许空值
        default        定义该列的默认值
        '''

        ListingId = db.Column(db.Integer, primary_key=True,)
        PolicyName = db.Column(db.String(10), unique=False, index=True)
        ParticipationAmount = db.Column(db.Integer, unique=False, index=True)
        BidTime = db.Column(db.Date, unique=False, index=True)
        Black = db.Column(db.Integer, unique=False, default=False, index=True)
        '''detail = db.relationship('All_Bids',backref='BlackInfo',lazy='dynamic')
        # 建立两表之间的关系，其中backref是定义反向关系，lazy是禁止自动执行查询（什么鬼？）'''

        def __init__(self, **kwargs):
            self.ListingId = kwargs['ListingId']
            self.PolicyName = kwargs['PolicyName']
            self.ParticipationAmount = kwargs['ParticipationAmount']
            self.BidTime = kwargs['BidTime']

        def get_id(self):
            return str(self.ListingId)

        def __repr__(self):
            return '<策略名为 %r>' % self.ListingId"""


# 动态新建映射表类
def gentable(username, tabletype):
    if tabletype == '_Bids':
        infos = {
            "__tablename__":username + tabletype,
            "__table_args__":{"extend_existing": True},  # 使用该参数，防止多次新建类是出现模型已存在的错误
            'ID':db.Column(db.Integer, primary_key=True),
            'ListingId':db.Column(db.Integer, unique=False, index=True),
            'PolicyName':db.Column(db.String(40), unique=False, index=True),
            'ParticipationAmount':db.Column(db.Integer, unique=False, index=True),
            'BidTime':db.Column(db.DateTime, unique=False, index=True),
            'User':db.Column(db.String(20), unique=False, index=True),
            'Black':db.Column(db.Integer, unique=False, index=True, default=0),
            'PayOff':db.Column(db.Boolean, unique=False, index=True, default=0)
            # 'AllBidsListingId':db.Column(db.Integer, db.ForeignKey('AllBids.ListingId')),
            # 'LoanInfo':db.relationship('AllBids', lazy='dynamic')
            }
    elif tabletype == '_Debts':
        infos = {
            "__tablename__":username + tabletype,
            "__table_args__":{"extend_existing": True},
            'DebtdealId':db.Column(db.Integer, primary_key=True),
            'ListingId':db.Column(db.Integer, unique=False, index=True),
            'PolicyName':db.Column(db.String(40), unique=False, index=True),
            'PriceForSaleRate':db.Column(db.Float, unique=False, index=True),
            'PriceForSale':db.Column(db.Float, unique=False, index=True),
            'BuyDate':db.Column(db.Date, unique=False, index=True),
            'Black':db.Column(db.Integer, unique=False, index=True, default=0),
            'User':db.Column(db.String(20), unique=False, index=True)
            }
    elif tabletype == '_Lists':
        infos = {
            "__tablename__":username + tabletype,
            "__table_args__":{"extend_existing": True},
            'ID':db.Column(db.Integer, primary_key=True),
            'ListingId':db.Column(db.Integer, unique=False, index=True),
            'BidAmount':db.Column(db.Integer, unique=False, index=True),
            'BidTime':db.Column(db.Date, unique=False, index=True),
            'PayBack':db.Column(db.Boolean, unique=False, index=True),
            'OverdueMore':db.Column(db.Boolean, unique=False, index=True),  # 是否曾长逾期
            'OverdueType':db.Column(db.Integer, unique=False, index=True),  # 平台外逾期类型
            'OwingAmount':db.Column(db.Float, unique=False, index=True),
            'BalAmount':db.Column(db.Integer, unique=False, index=True),  # 包括拍拍贷在内的网贷待还
            'WarningLevel':db.Column(db.Integer, unique=False, index=True),
            'InfoUpdateTime':db.Column(db.Date, unique=False, index=True)
            }
    model = type("UserLists", (db.Model,), infos)
    return model