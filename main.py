from typing import Union, List
from fastapi import FastAPI, Response, Request, Depends, HTTPException, status
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from ipaddress import IPv4Address, IPv6Address, ip_address
from starlette.middleware.base import BaseHTTPMiddleware, RequestResponseEndpoint
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
import sqlite3
import pandas as pd
import json
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

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

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="login")
class User(BaseModel):
    id: str
    password: str

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    title = '學程檢查平台server'
    message = '學程檢查平台Server端'
    return templates.TemplateResponse("index.html", {"request": request, "title": title, "message": message})


# 獲取環境變量中的 SECRET_KEY
SECRET_KEY = os.getenv("SECRET_KEY")
print(SECRET_KEY)
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1  # 設置Token在2分鐘後過期

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
    print('---/login START---')
    auth_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="錯誤的使用者名稱或密碼",
        headers={"WWW-Authenticate": "Bearer"},
    )
    print('ID=',user.id)
    print('password=',user.password)

    query = """
        SELECT * from members WHERE member_id = ? AND member_password = ?
    """
    res = queryDB(query, (user.id,user.password))
    # print('password=',user.password)
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
    try:
        payload = await verify_token(token_data.token)
        return {"status": "success", "data": payload}
    except HTTPException as e:
        return {"status": "error", "detail": e.detail}



@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

@app.get("/program/all")
def get_program(token: str = Depends(oauth2_scheme)):
    query = """
        SELECT * from programs
    """
    res = queryDB(query)
    return res

@app.get("/program/{program_id}")
def get_program(program_id: int):
    conn = sqlite3.connect('db2.db')
    
    query = f"""
SELECT 
    p.program_id AS program_id,
    p.program_name AS program_name,
    c.category_id AS category_id,
    c.category_name AS category_name,
    COALESCE(d.domain_id, 0) AS domain_id,
    COALESCE(d.domain_name, '0') AS domain_name,
    s.subject_id AS subject_id,
    s.subject_name AS subject_name,
    s.subject_sub_id AS subject_sub_id,
	s.subject_sys AS subject_sys,
	s.subject_unit AS subject_unit,
	s.subject_eng_name AS subject_eng_name,
    s.subject_credit AS subject_credit,
    s.subject_hour AS subject_hour
FROM 
    programs p
    INNER JOIN courses co ON p.program_id = co.program_id
    INNER JOIN categories c ON co.category_id = c.category_id
    LEFT JOIN domains d ON co.domain_id = d.domain_id
    INNER JOIN subjects s ON co.subject_id = s.subject_id
    where co.program_id = {program_id}
    """
    
    df = pd.read_sql_query(query, conn)
    print(df)
    json_data = json.loads(df.to_json(orient='records', force_ascii=False))
    # with open('data.json', 'w', encoding='utf-8') as file:
    #     file.write(json_data)
    
    return json_data

# def selectdb():
#     conn = sqlite3.connect("db.sqlite3")
#     cursor = conn.cursor()
#     query = """
#         SELECT * from category
#     """
#     cursor.execute(query)
#     res = cursor.fetchall()

#     conn.commit()
#     conn.close()
#     return res

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
