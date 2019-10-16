"""
表单类
来源：网络
修改：西海岸
"""
#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Time    : 2017/8/1 14:46
# @File    : Form.py

import datetime

from wtforms import StringField, SubmitField, PasswordField, DecimalField
from wtforms.validators import InputRequired, Length, NumberRange, EqualTo, Optional
from flask_wtf import FlaskForm


# 登录账户
class LoginForm(FlaskForm):
    name = StringField('帐号', validators=[Length(min=4, max=25, message='帐号长度必须在 4~25 个字节之间')])
    password = PasswordField('密码', validators=[InputRequired(), Length(min=6, max=36, message='密码长度必须在 6~36 个字节之间')])
    submit = SubmitField('登录')


# 注册账户
class RegisterForm(FlaskForm):
    name = StringField('帐号', validators=[Length(min=4, max=25, message='帐号长度必须在 4~25 个字节之间')])
    password = PasswordField('密码', validators=[InputRequired(), Length(min=6, max=36, message='密码长度必须在 6~36 个字节之间'), EqualTo('confirm', message='两次密码输入必须一致')])
    confirm = PasswordField('重复密码')
    submit = SubmitField('注册')


# 修改密码
class ModifyPasswordForm(FlaskForm):
    old_password = PasswordField('旧的密码', validators=[InputRequired(), Length(min=6, max=36, message='密码长度必须在 6~36 个字节之间')], render_kw={"placeholder":"旧的密码"})
    new_password = PasswordField('新的密码', validators=[InputRequired(), Length(min=6, max=36, message='密码长度必须在 6~36 个字节之间'), EqualTo('confirm', message='两次密码输入必须一致')], render_kw={"placeholder":"新的密码"})
    confirm = PasswordField('重复密码', render_kw={"placeholder":"重复密码"})
    submit = SubmitField('修改密码')


# 投标开关
class SwitchForm(FlaskForm):
    submit_bid = SubmitField('开/关')
    submit_debt = SubmitField('开/关')
    submit_over_due = SubmitField('开/关')

# 充值提现
class PayForm(FlaskForm):
    name = StringField('帐号', validators=[Length(min=4, max=25, message='帐号长度必须在 4~25 个字节之间')], render_kw={"placeholder":"帐号"})
    pay_amount = DecimalField('充值金额', validators=[Optional(), NumberRange(min=2, max=99999, message='充值金额必须为整数，且在 2~99999 元之间')], places=1, render_kw={"placeholder":"充值金额"})
    authorize_binding = StringField('授权位', validators=[Optional(), Length(min=1, max=20, message='授权位长度必须在 1~20 个字节之间')], render_kw={"placeholder":"授权位"})
    submit_pay = SubmitField('充值')
    submit_verify_true = SubmitField('贷后授权')
    submit_verify_false = SubmitField('贷后停权')


'''class RegisterForm(Form):
    # Text Field类型，文本输入框，必填，用户名长度为4到25之间
    username = StringField('Username', validators=[Length(min=4, max=25)])
 
    # Text Field类型，文本输入框，Email格式
    email = StringField('Email Address', validators=[Email()])
 
    # Text Field类型，密码输入框，必填，必须同confirm字段一致
    password = PasswordField('Password', [
        DataRequired(),
        EqualTo('confirm', message='Passwords must match')
    ])
 
    # Text Field类型，密码输入框
    confirm = PasswordField('Repeat Password')
 
    # Text Field类型，文本输入框，必须输入整型数值，范围在16到70之间
    age = IntegerField('Age', validators=[NumberRange(min=16, max=70)])
 
    # Text Field类型，文本输入框，必须输入数值，显示时保留一位小数，格式要求和decimal.Decimal一样
    height = DecimalField('Height (Centimeter)', places=1)
    
    # FloatField 文本字段，值为浮点数
 
    # Text Field类型，文本输入框，必须输入是"年-月-日"格式的日期
    birthday = DateField('Birthday', format='%Y-%m-%d')
    
    # DateTimeField 文本字段，值为 datetime.datetime 格式
 
    # Radio Box类型，单选框，choices里的内容会在ul标签里，里面每个项是(值，显示名)对
    gender = RadioField('Gender', choices=[('m', 'Male'), ('f', 'Female')],
                                  validators=[DataRequired()])
 
    # Select类型，下拉单选框，choices里的内容会在Option里，里面每个项是(值，显示名)对
    job = SelectField('Job', choices=[
        ('teacher', 'Teacher'),
        ('doctor', 'Doctor'),
        ('engineer', 'Engineer'),
        ('lawyer', 'Lawyer')
    ])
 
    # Select类型，多选框，choices里的内容会在Option里，里面每个项是(值，显示名)对
    hobby = SelectMultipleField('Hobby', choices=[
        ('swim', 'Swimming'),
        ('skate', 'Skating'),
        ('hike', 'Hiking')
    ])
 
    # Text Area类型，段落输入框
    description = TextAreaField('Introduction of yourself')
 
    # Checkbox类型，加上default='checked'即默认是选上的
    accept_terms = BooleanField('I accept the Terms of Use', default='checked',
                                validators=[DataRequired()])
 
    # Submit按钮
    submit = SubmitField('Register')
    
    # FileField 文件上传字段
    
    # FormField 把表单作为字段嵌入另一个表单
    
    # FieldList 一组指定类型的字段
    
    # HiddenField 隐藏文本字段
    
    
    验证器函数   说明
    DataRequired/Required   代表内容是必填项 DataRequired(message='用户信息不能为空')
    Email                   验证电子邮件地址,要求正则模式 : ^.+@([^.@][^@]+)$
    EqualTo                 比较两个字段的值,常用于确认密码情况，EqualTo('要确认字段名',message='xxx')
    IPAddress               验证IPV4网络地址 参数默认ipv4=True,ipv6=False
    Length                  验证输入字符串的长度 参数类型是字符串，Length(min=6,max=30,message='个人信息的简介6-30个字')
    NumberRange             验证输入的值在数字范围内，NumberRange(min=6,max=90,message='年龄为6-90岁')
    Optional                无输入值时跳过其他验证函数
    Regexp                  使用正则表达式验证输入值 参数regex='正则模式'
    URL                     验证 URL URL(message=’请输入正确的url地址’)]，正则模式是^[a-z]+://(?P<host>[^/:]+)(?P<port>:[0-9]+)?(?P<path>\/.*)?$
    AnyOf                   确保输入值在可选值列表中
    NoneOf                  确保输入值不在可选值列表中
    '''