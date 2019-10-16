# coding=utf-8

__author__ = "yangl"


import base64
import rsa
from . import Global
from OpenSSL.crypto import load_privatekey, FILETYPE_PEM, sign

class rsa_client(object):

    @staticmethod
    def sign(signdata):
        signdata = signdata.encode('utf-8')
        signdata = signdata.lower()
        PrivateKey = load_privatekey(FILETYPE_PEM, Global.privatekey)
        signature = base64.b64encode(sign(PrivateKey, signdata, 'sha1'))
        return signature

    @staticmethod
    def sort(dicts):
        dics = sorted(dicts.items(), key=lambda k : k[0])
        params = ""
        for dic in dics:
            if type(dic[1]) is str:
                params += dic[0] + dic[1]
        return params


    @staticmethod
    def encrypt(encryptdata):
        PublicKey = rsa.PublicKey.load_pkcs1_openssl_pem(Global.publickey)
        encrypted = base64.b64encode(rsa.encrypt(encryptdata, PublicKey))
        return encrypted

    @staticmethod
    def decrypt(decryptdata):
        PrivateKey = rsa.PrivateKey.load_pkcs1(Global.privatekey)
        decrypted = rsa.decrypt(base64.b64decode(decryptdata), PrivateKey)
        return decrypted