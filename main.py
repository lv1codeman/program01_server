from typing import Union, List, Optional
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
import itertools
from sqlalchemy import text

def get_current_time():
    current_time = datetime.now()
    formatted_time = current_time.strftime("[%Y-%m-%d %H:%M:%S] ")
    return formatted_time

# 加載 .env 文件中的環境變量
load_dotenv()
class Course(BaseModel):
    subject_id: int
    subject_unit: str
    subject_sub_id: str
    subject_sys: str
    subject_name: str
    subject_eng_name: Optional[str] = None
    subject_credit: int
    subject_hour: int
class Domain(BaseModel):
    domain_id: int
    domain_name: str
    domain_goal: str
    domain_goalCredit: int
    course: List[Course]
class Category(BaseModel):
    category_id: int
    category_name: str
    category_hasDomain: int
    category_goal: str
    category_goalCredit: int
    domain: List[Domain] = []
    course: List[Course] = []
class Program(BaseModel):
    program_id: Optional[int] = None
    program_name: str
    program_url: str
    program_type: str
    program_unit: str
    program_minCredit: int
    program_nonSelfCredit: int
    program_criteria: str
    category: List[Category]


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
        detail="請先登入(Token驗證失敗)",
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

def parse_json(program: Program, is_update: bool = False):
    if is_update:
        parse_json_update(program)
    else:
        print("Parsing JSON data...")
        result = []
        # 找出DB中program_structure_id、program_id、category_id、domain_id的最大值
        query = """
            SELECT 
                MAX(program_structure_id) as program_structure_id_max,
                MAX(program_id) as program_id_max,
                MAX(category_id) as category_id_max,
                MAX(domain_id) as domain_id_max
            from program_structure
        """
        max_values = queryDB(query)[0]
        print('MAX(program_structure_id) = ', max_values['program_structure_id_max'])
        program_structure_id = max_values['program_structure_id_max'] + 1
        program_id = max_values['program_id_max'] + 1    
        # 每個program可以有多個category和domain，所以在foreach每個category和domain的時候才對他們的id+1
        category_id = max_values['category_id_max']
        domain_id = max_values['domain_id_max']
        
        # 寫入programs表
        query = """
            INSERT INTO programs (program_id, program_name, program_url, program_unit, program_type, program_minCredit, program_nonSelfCredit, program_criteria)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """
        params = (program_id, program.program_name, program.program_url, program.program_unit, program.program_type, program.program_minCredit, program.program_nonSelfCredit, program.program_criteria)
        insertDB(query, params)

        print('data preloaded success...')
        # 寫入categories表
        for category in program.category:
            category_id += 1
            print('category.category_id = ', category.category_id)
            print('category_id = ', category_id)
            query = """
                INSERT INTO categories (category_id, category_name, category_hasDomain, category_goal, category_goalCredit)
                VALUES (?, ?, ?, ?, ?)
            """
            params = (category_id, category.category_name, category.category_hasDomain, category.category_goal, category.category_goalCredit)
            print('有跑到這喔')
            insertDB(query, params)
            
            if category.course:
                for course in category.course:
                    result.append({
                        'program_structure_id': program_structure_id,
                        'program_id': program_id,
                        'category_id': category_id,
                        'domain_id': 0,
                        'subject_sub_id': course.subject_sub_id
                    })
                    program_structure_id += 1
            elif category.domain:
                for domain in category.domain:
                    domain_id += 1
                    query = """
                        INSERT INTO domains (domain_id, domain_name, domain_goal, domain_goalCredit)
                        VALUES (?, ?, ?, ?)
                    """
                    params = (domain_id, domain.domain_name, domain.domain_goal, domain.domain_goalCredit)
                    insertDB(query, params)
                    for course in domain.course:
                        result.append({
                            'program_structure_id': program_structure_id,
                            'program_id': program_id,
                            'category_id': category_id,
                            'domain_id': domain_id,
                            'subject_sub_id': course.subject_sub_id
                        })
                        program_structure_id += 1

        print("Finished parsing JSON data")
    return result

@app.post("/program/create")
async def create_program(data: Program):
    try:
        parsed_data = parse_json(data, is_update=False)
        if not parsed_data:
            raise HTTPException(status_code=400, detail="Parsed data is empty")
        print('parsed_data=',parsed_data)
        # 寫入program_structure
        for item in parsed_data:
            query = """
            INSERT INTO program_structure (category_id, domain_id, program_id, program_structure_id, subject_sub_id)
            VALUES (?, ?, ?, ?, ?)
            """
            params = (item['category_id'], item['domain_id'], item['program_id'], item['program_structure_id'], item['subject_sub_id'])
            insertDB(query, params)

        return {"message": "Data inserted successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))



# @app.post("/program/getUnitPrograms")
# async def select_program(unit: UnitName):
#     print('unit = ',unit.unit)
#     query = """
#         SELECT 
#         *
#         FROM program_structure ps
#         INNER JOIN programs p ON p.program_id = ps.program_id
#         INNER JOIN categories c ON ps.category_id = c.category_id
#         LEFT JOIN domains d ON ps.domain_id = d.domain_id
#         INNER JOIN subjects s ON ps.subject_sub_id = s.subject_sub_id
#         where program_unit = ?
#     """
#     params = (unit.unit,)  # 修改成元组形式
#     res = queryDB(query, params)
#     print(res)
#     return {"data": res}

class Pdata(BaseModel):
    unit: str
    program_id: int
@app.post("/program/getUnitPGById")
async def browse_program_edit(p: Pdata):
    print('unit = ',p.unit)
    print('p.program_id = ',p.program_id)
    
    if p.unit == '教務處課務組':
        query = """
            SELECT 
            *
            FROM program_structure ps
            INNER JOIN programs p ON p.program_id = ps.program_id
            INNER JOIN categories c ON ps.category_id = c.category_id
            LEFT JOIN domains d ON ps.domain_id = d.domain_id
            INNER JOIN subjects s ON ps.subject_sub_id = s.subject_sub_id
            where ps.program_id = ?
        """
        params = (p.program_id,) 
    else:
        query = """
            SELECT 
            *
            FROM program_structure ps
            INNER JOIN programs p ON p.program_id = ps.program_id
            INNER JOIN categories c ON ps.category_id = c.category_id
            LEFT JOIN domains d ON ps.domain_id = d.domain_id
            INNER JOIN subjects s ON ps.subject_sub_id = s.subject_sub_id
            where program_unit = ? and ps.program_id = ?
        """
        params = (p.unit,p.program_id)  # 修改成元组形式
    res = queryDB(query, params)
    print(res)
    return {"data": res}

class UnitName(BaseModel):
    unit: str
@app.post("/program/getUnitPG")
async def browse_program(input: UnitName):
    # print('unit = ',input.unit)
    if input.unit == '教務處課務組':
        query = "SELECT * FROM programs"
        params = ()
    else:
        query = """
            SELECT * FROM programs
            where program_unit = ?
        """
        params = (input.unit,)  # 修改成元组形式
    res = queryDB(query, params)
    # print(res)
    return {"data": res}

class ProgramID(BaseModel):
    program_id: int
@app.post("/program/delete_program")
async def deleteProgram(p: ProgramID):
    print('program_id = ', p.program_id)
    queries = [
        ("DELETE FROM domains WHERE domain_id IN (SELECT DISTINCT domain_id FROM program_structure WHERE program_id = ?);", (p.program_id,)),
        ("DELETE FROM categories WHERE category_id IN (SELECT DISTINCT category_id FROM program_structure WHERE program_id = ?);", (p.program_id,)),
        ("DELETE FROM programs WHERE program_id = ?;", (p.program_id,)),
        ("DELETE FROM program_structure WHERE program_id = ?;", (p.program_id,))
    ]
    
    for query, params in queries:
        queryDB_nores(query, params)
    
    return {"data": "Program and related entries deleted successfully"}

@app.get("/program/all")
def get_program():
    query = """
        SELECT * from programs
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

class TargetProgram(BaseModel):
    program_id: int

@app.get("/student/getPassedProgram")
def get_passed_program(p: TargetProgram):
    query = """
        select * from program_structure
        where program_id = ?
    """

    params = (p.program_id)

    res = queryDB(query, params)
    print(res)
    return {"message": "檢查完畢。"}


@app.get("/subject/all")
def get_subject_all():
    query = """
        SELECT * from subjects
    """
    res = queryDB(query)
    return res

def insertDB(query, params=None):
    conn = sqlite3.connect("./DB/program01.db")
    cursor = conn.cursor()
    try:
        if params is not None:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"SQLite error executing query: {e}")
        conn.rollback()
        return False
    finally:
        conn.close()

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

def queryDB_nores(query, params=None):
    conn = sqlite3.connect("./DB/program01.db")
    cursor = conn.cursor()
    try:
        if params is not None:
            cursor.execute(query, params)
        else:
            cursor.execute(query)
        conn.commit()
    except sqlite3.Error as e:
        conn.rollback()
        print(f"An error occurred: {e}")
    finally:
        conn.close()

def parse_json_update(program: Program):
    print('updating program_id = ', program.program_id)

    queries = [
        ("DELETE FROM domains WHERE domain_id IN (SELECT DISTINCT domain_id FROM program_structure WHERE program_id = ?);", (program.program_id,)),
        ("DELETE FROM categories WHERE category_id IN (SELECT DISTINCT category_id FROM program_structure WHERE program_id = ?);", (program.program_id,)),
        ("DELETE FROM programs WHERE program_id = ?;", (program.program_id,)),
        ("DELETE FROM program_structure WHERE program_id = ?;", (program.program_id,))
    ]
    for query, params in queries:
        queryDB_nores(query, params)
    
    result = []
    # 找出DB中program_structure_id、category_id、domain_id的最大值
    query = """
        SELECT 
            MAX(program_structure_id) as program_structure_id_max,
            MAX(program_id) as program_id_max,
            MAX(category_id) as category_id_max,
            MAX(domain_id) as domain_id_max
        from program_structure
    """
    max_values = queryDB(query)[0]
    print('MAX(program_structure_id) = ', max_values['program_structure_id_max'])
    program_structure_id = max_values['program_structure_id_max'] + 1
    # 與create的差別就在這，program_id不需要從DB找最大值
    program_id = program.program_id
    # 每個program可以有多個category和domain，所以在foreach每個category和domain的時候才對他們的id+1
    category_id = max_values['category_id_max']
    domain_id = max_values['domain_id_max']
    
    # 寫入programs表
    query = """
        INSERT INTO programs (program_id, program_name, program_url, program_unit, program_type, program_minCredit, program_nonSelfCredit, program_criteria)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    """
    params = (program_id, program.program_name, program.program_url, program.program_unit, program.program_type, program.program_minCredit, program.program_nonSelfCredit, program.program_criteria)
    insertDB(query, params)

    print('data preloaded success...')
    # 寫入categories表
    for category in program.category:
        category_id += 1
        print('category.category_id = ', category.category_id)
        print('category_id = ', category_id)
        query = """
            INSERT INTO categories (category_id, category_name, category_hasDomain, category_goal, category_goalCredit)
            VALUES (?, ?, ?, ?,?)
        """
        params = (category_id, category.category_name, category.category_hasDomain, category.category_goal, category.category_goalCredit)
        insertDB(query, params)
        
        if category.course:
            for course in category.course:
                result.append({
                    'program_structure_id': program_structure_id,
                    'program_id': program_id,
                    'category_id': category_id,
                    'domain_id': 0,
                    'subject_sub_id': course.subject_sub_id
                })
                program_structure_id += 1
        elif category.domain:
            for domain in category.domain:
                domain_id += 1
                query = """
                    INSERT INTO domains (domain_id, domain_name, domain_goal, domain_goalCredit)
                    VALUES (?, ?, ?, ?)
                """
                params = (domain_id, domain.domain_name, domain.domain_goal, domain.domain_goalCredit)
                insertDB(query, params)
                for course in domain.course:
                    result.append({
                        'program_structure_id': program_structure_id,
                        'program_id': program_id,
                        'category_id': category_id,
                        'domain_id': domain_id,
                        'subject_sub_id': course.subject_sub_id
                    })
                    program_structure_id += 1
    return result

@app.post("/program/update")
async def update_program(data: Program):
    try:
        parsed_data = parse_json_update(data)
        if not parsed_data:
            raise HTTPException(status_code=400, detail="Parsed data is empty")
        # 寫入program_structure
        for item in parsed_data:
            query = """
            INSERT INTO program_structure (category_id, domain_id, program_id, program_structure_id, subject_sub_id)
            VALUES (?, ?, ?, ?, ?)
            """
            params = (item['category_id'], item['domain_id'], item['program_id'], item['program_structure_id'], item['subject_sub_id'])
            insertDB(query, params)

        return {"message": "Data update successfully"}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))


@app.get("/program/program_structure/{pid}")
async def getPCnum(pid: int):

    query = """
        select DISTINCT category_id,domain_id
        from program_structure ps
        where ps.program_id = ?
    """
    params = (pid, )
    res = queryDB(query,params)

    return res


@app.get("/program/categories/{pid}")
async def getPCnum(pid: int):

    query = """
        SELECT * from categories
        WHERE category_id in
        (select DISTINCT category_id
        from program_structure ps
        where ps.program_id = ?)
    """
    params = (pid, )
    res = queryDB(query,params)

    return res

@app.get("/program/categories/{sid}/{pid}/{cid}")
async def getCATEpass(sid: str ,pid: int, cid: int):

    query = """
SELECT s.subject_sub_id, s.subject_unit, s.subject_sys, s.subject_name, s.subject_credit, sc.score from subjects s
join scores sc on sc.subject_sub_id = s.subject_sub_id
WHERE 
sc.student_id = ?
AND
s.subject_sub_id in (
	SELECT subject_sub_id FROM (
		select * from program_structure ps
		join categories c on ps.category_id = c.category_id
		left join domains d on ps.domain_id = d.domain_id
		where ps.program_id = ? and ps.category_id = ?
	) 
	WHERE subject_sub_id in (
		SELECT subject_sub_id FROM scores sc
		WHERE sc.student_id = ? AND sc.score >= 60
	)
)
    """
    params = (sid, pid, cid, sid)
    res = queryDB(query,params)

    return res
    
@app.get("/program/domains/{sid}/{pid}/{cid}")
async def getDOMpass(sid: str ,pid: int, cid: int):

    query = """
SELECT s.subject_sub_id, s.subject_unit, s.subject_sys, s.subject_name, s.subject_credit, sc.score from subjects s
join scores sc on sc.subject_sub_id = s.subject_sub_id
WHERE 
sc.student_id = ?
AND
s.subject_sub_id in (
	SELECT subject_sub_id FROM (
		select * from program_structure ps
		join categories c on ps.category_id = c.category_id
		left join domains d on ps.domain_id = d.domain_id
		where ps.program_id = ? and ps.domain_id = ?
	) 
	WHERE subject_sub_id in (
		SELECT subject_sub_id FROM scores sc
		WHERE sc.student_id = ? AND sc.score >= 60
	)
)
    """
    params = (sid, pid, cid, sid)
    res = queryDB(query,params)

    return res

@app.get("/program/getPS/{pid}")
async def getPS(pid: int):

    query = """
SELECT DISTINCT 
ps.program_id, ps.category_id, ps.domain_id, 
c.category_name,c.category_hasDomain, c.category_goal, c.category_goalCredit, 
d.domain_name,d.domain_goal, d.domain_goalCredit
from program_structure ps
join categories c on ps.category_id = c.category_id
left join domains d on ps.domain_id = d.domain_id
WHERE ps.program_id=?
    """
    params = (pid, )
    res = queryDB(query,params)

    return res

@app.get("/program/getTargetStruct/{pid}/{cid}/{did}")
async def getTargetStruct(pid: int, cid: int, did: int):
    if did == 0:
        query = """
select * from program_structure ps
join categories c on ps.category_id = c.category_id
left join domains d on ps.domain_id = d.domain_id
where ps.program_id = ? and ps.category_id = ? and ps.domain_id = ?
    """
        params = (pid, cid, did)
    else:
        query = """
select * from program_structure ps
join categories c on ps.category_id = c.category_id
left join domains d on ps.domain_id = d.domain_id
where ps.program_id = ? and ps.category_id = ? and ps.domain_id = ps.domain_id
    """
        params = (pid, cid, )

    
    res = queryDB(query,params)

    return res


