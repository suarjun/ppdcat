#coding=utf-8
__author__ = "yangl"
'''''
全局变量
'''
'''''
publickey为服务端的公钥
privatekey为自己客户端的私钥
PS：python的密钥都是PKCS1的
站点上的客户端私钥需要剔除
-----BEGIN RSA PRIVATE KEY-----
AND
-----END RSA PRIVATE KEY-----
并且将回车符剔除

备注：Python只支持pkcs1密钥，不支持pkcs8
'''

privatekey='''
-----BEGIN RSA PRIVATE KEY-----
MIICXQIBAAKBgQCFzwBFjfX8veUzhUM4JsRrMyIKRNiGKGzVktUeSEPxdNvywhk9A1otl104/jxEsZbiktV6In3t3MIxEvWt3Epy2mGwkfgGCEQ9e1NKS8ZilUDIymzp2y4sSlv8y1E7LN6qQiLBgZVAe+Kcn3KrxdYpX++tRkWXUdOgVeEj28KszQIDAQABAoGACl+/HKVh8eNjFrh5Oqw+xDTlqbgmtVgDABfvL/bYVasCtnJ39HQDFM/MaXPEhmriUNSjemGcM8nOwHFA3ObcWqhhKidSvNyZSCICwVLBeEDHBdeUVR4y7tRaYIRbQ69kS9b3ziHygQstDuJ30vkVuopLFDOdmGYmYuVmrhXIyD0CQQDLrLV9pdUUpJuNRjzUXPlcfCIxiY4DE9vOIWvCN6FCqf8kfDU69M8bnFqxgjnpqN9YaoEWKd8KkiLnVMOUpVc/AkEAqC9WDEPfdtDSFQDXyC/5Gvo6V67F+dt8AKB/3jwC4bEazai1mmIEkC8tv9pN1xpqBZ/zrDa5jP9vO/wAhnQk8wJBAJ0oSe6G7DD+hsxu2vceOodjfVruAfdb9mpKnYSCOltfIvF7KfOw/LIYZl671oX2eUgW/j4k1uaoNmh7nmJvZi8CQEQJYjXz/yKBt3rnrGM/hPZ048U03sIFGFTomNG+VSwYCU/JQC4EGPR7IXbLSVILTXiZDGpOeSGg887AUzYRJiECQQClsdPbZZxgDl8JEFBvdArvtiL9kRJfwSFTPqDCHGTLrXlMR7Hy9mXXMOJ4WecMd16e6rNBj2HXul+5TF3FnHYR
-----END RSA PRIVATE KEY-----
'''

publickey='''
-----BEGIN PUBLIC KEY-----
MIGfMA0GCSqGSIb3DQEBAQUAA4GNADCBiQKBgQCFzwBFjfX8veUzhUM4JsRrMyIKRNiGKGzVktUeSEPxdNvywhk9A1otl104/jxEsZbiktV6In3t3MIxEvWt3Epy2mGwkfgGCEQ9e1NKS8ZilUDIymzp2y4sSlv8y1E7LN6qQiLBgZVAe+Kcn3KrxdYpX++tRkWXUdOgVeEj28KszQIDAQAB
-----END PUBLIC KEY-----
'''
