from typing import Union, List
from typing import Annotated
from fastapi import FastAPI, Response, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from ipaddress import IPv4Address, IPv6Address, ip_address
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from jose import JWTError, jwt
from pydantic import BaseModel
import sqlite3
import pandas as pd
import json
import os
from Crypto.Cipher import AES, DES
from binascii import b2a_hex, a2b_hex
import hashlib
import base64
from dotenv import load_dotenv
from datetime import datetime, timedelta

def get_current_time():
    current_time = datetime.now()
    formatted_time = current_time.strftime("[%Y-%m-%d %H:%M:%S] ")
    return formatted_time

# 加載 .env 文件中的環境變量
load_dotenv()

app = FastAPI()
# origins = ["http://localhost:5173"]
origins = ['*']

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

current_directory = os.path.dirname(os.path.abspath(__file__))
templates = Jinja2Templates(directory=current_directory)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 獲取環境變量中的 SECRET_KEY
SECRET_KEY = os.getenv("SECRET_KEY")
SECRET_AES_KEY = os.getenv("SECRET_AES_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 60  # 設置Token在2分鐘後過期

class User(BaseModel):
    id: str
    password: str

def pad(data):
    # Zero Padding to ensure data length is a multiple of 16 bytes
    while len(data) % 16 != 0:
        data += '\x00'
    return data

# AES解密
def decrypt_aes(encrypted_data, key):
    key = key.encode('utf-8')
    encrypted_data = base64.b64decode(encrypted_data)
    cipher = AES.new(key, AES.MODE_ECB)
    decrypted_data = cipher.decrypt(encrypted_data)
    decrypted_data = decrypted_data.rstrip(b'\x00')
    return decrypted_data.decode('utf-8')

# AES加密
def encrypt_aes(data, key):
    key = key.encode('utf-8')
    padded_data = pad(data)
    cipher = AES.new(key, AES.MODE_ECB)
    encrypted_data = cipher.encrypt(padded_data.encode('utf-8'))
    encrypted_data_base64 = base64.b64encode(encrypted_data).decode('utf-8')
    return encrypted_data_base64

# SERVER端根目錄
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    title = '學程檢查平台server'
    message = '學程檢查平台Server端'
    return templates.TemplateResponse("index.html", {"request": request, "title": title, "message": message})

# 創建Token的function
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 登入的API接口：接收client端傳來的id, password,回傳token與user data
@app.post("/login", response_model=dict)
async def login_for_access_token(user: User):
    auth_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="錯誤的使用者名稱或密碼",
        headers={"WWW-Authenticate": "Bearer"},
    )
    # 將密碼解密(可以一直加密，但加密2次就要解密2次，每次加密/解密的結果是固定的)
    decrypted_data = decrypt_aes(user.password, SECRET_AES_KEY)
    query = """
        SELECT * from members WHERE member_account = ? AND member_password = ?
    """
    res = queryDB(query, (user.id, decrypted_data))
    print('user data: ',res)
    
    if not res:
        raise auth_exception
    else:
        access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
        access_token = create_access_token(
            data={"sub": "data_access"}, expires_delta=access_token_expires
        )
        return {"access_token": access_token, "token_type": "bearer", "user_data": res}

# 驗證token合法性的function
async def verify_token(token: str = Depends(oauth2_scheme)):
    """
    藉由Depends(oauth2_scheme)，從header中提取Authorization
    Authorization: 'Bearer token_string'
    並驗證token_string是否合法
    若不合法回傳401 Unauthorized訊息
    """
    timestamp = get_current_time()
    print(f'{timestamp} token: {token}')

    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token驗證失敗",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = payload.get("exp")
        if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token逾期",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if payload.get("sub") != "data_access":
            raise credentials_exception
        return payload
    except JWTError:
        raise credentials_exception

class TokenData(BaseModel):
    token: str

# 驗證token合法性的API接口
@app.post("/checkToken")
async def checkToken(token_data: TokenData):
    """
    使用client端傳來的token資料進行verify_token
    ## verify_token:
    -   藉由Depends(oauth2_scheme)，從header中提取Authorization
    >   Authorization: 'Bearer token_string'  
    -   驗證token_string是否合法  
    -   若不合法回傳401 Unauthorized訊息
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token驗證失敗",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = await verify_token(token_data.token)
        return {"status": "success", "data": payload}
    except HTTPException as e:
        raise credentials_exception

@app.get("/program/all")
def get_program(token: dict = Depends(verify_token)):
    query = """
        SELECT * from programs where id = ? and password = ?
    """
    res = queryDB(query)
    return res

@app.get("/fakeprogram/all")
def get_fakeprogram_all():
    """
    獲取假資料，沒有做token驗證  
    Returns:
    - 各學程資料
    """

    query = """
        SELECT * from fakeprogram
    """
    res = queryDB(query)
    return res

@app.get("/subject/all")
def get_subject_all():
    query = """
        SELECT * from subjects
    """
    res = queryDB(query)
    return res

def queryDB(query, params=None):
    conn = sqlite3.connect("./DB/program01.db")
    cursor = conn.cursor()
    if params is not None:
        cursor.execute(query, params)
    else:
        cursor.execute(query)
    rows = cursor.fetchall()
    column_names = [description[0] for description in cursor.description]
    results = [dict(zip(column_names, row)) for row in rows]

    conn.commit()
    conn.close()
    
    return results
