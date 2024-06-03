from typing import Union, List
from fastapi import FastAPI, Response, Depends, HTTPException, status
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from pydantic import BaseModel
import sqlite3
import os
from dotenv import load_dotenv
from datetime import datetime, timedelta

# 加載 .env 文件中的環境變量
load_dotenv()

app = FastAPI()
origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 獲取環境變量中的 SECRET_KEY
SECRET_KEY = os.getenv("SECRET_KEY")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 1  # 設置Token在2分鐘後過期

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="token")

# 創建Token的函數
def create_access_token(data: dict, expires_delta: timedelta = None):
    to_encode = data.copy()
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=15)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

# 獲取當前Token
async def get_current_token(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        exp = payload.get("exp")
        if exp and datetime.utcfromtimestamp(exp) < datetime.utcnow():
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Token has expired",
                headers={"WWW-Authenticate": "Bearer"},
            )
        if payload.get("sub") != "data_access":
            raise credentials_exception
    except JWTError:
        raise credentials_exception

@app.post("/token", response_model=dict)
async def login_for_access_token():
    access_token_expires = timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": "data_access"}, expires_delta=access_token_expires
    )
    return {"access_token": access_token, "token_type": "bearer"}

@app.get("/", response_model=List[dict])
async def get_data(response: Response, token: str = Depends(get_current_token)):
    data = selectdb()
    json_data = []
    for item in data:
        json_item = {"id": item[0], "name": item[1]}
        json_data.append(json_item)
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return jsonable_encoder(json_data)

@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None, token: str = Depends(get_current_token)):
    return {"item_id": item_id, "q": q}

@app.get("/program/all")
def get_program(token: str = Depends(get_current_token)):
    query = """
        SELECT * from program
    """
    res = queryDB(query)
    return res

@app.get("/program/{program_id}")
def get_program(program_id: int, token: str = Depends(get_current_token)):
    query = """
        SELECT * from program WHERE id = ?
    """
    res = queryDB(query, (program_id,))
    print(res)
    return jsonable_encoder(res)

def selectdb():
    conn = sqlite3.connect("db.sqlite3")
    cursor = conn.cursor()
    query = """
        SELECT * from category
    """
    cursor.execute(query)
    res = cursor.fetchall()

    conn.commit()
    conn.close()
    return res

def queryDB(query, params=None):
    conn = sqlite3.connect("db.sqlite3")
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
