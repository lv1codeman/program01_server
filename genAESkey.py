import secrets

# 生成一个32字节的安全密钥
secret_key = secrets.token_urlsafe(16)
print(secret_key)