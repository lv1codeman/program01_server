from typing import Union
from typing import List
from fastapi import FastAPI, Response
from fastapi.encoders import jsonable_encoder
from fastapi.middleware.cors import CORSMiddleware
import sqlite3
import json

app = FastAPI()

# origins = [
#     "http://localhost.tiangolo.com",
#     "https://localhost.tiangolo.com",
#     "http://localhost",
#     "http://localhost:8080",
#     "http://localhost:8000",
#     "http://localhost:5173",
# ]

origins = ["*"]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/", response_model=List[dict])
async def get_data(response: Response):
    data = selectdb()
    json_data = []

    # 遍历原始数据，将每个元组转换为字典，并添加到列表中
    for item in data:
        json_item = {"id": item[0], "name": item[1]}
        json_data.append(json_item)

    # 使用jsonable_encoder确保正确的JSON编码
    response.headers["Content-Type"] = "application/json; charset=utf-8"
    return jsonable_encoder(json_data)


@app.get("/items/{item_id}")
def read_item(item_id: int, q: Union[str, None] = None):
    return {"item_id": item_id, "q": q}

@app.get("/program/all")
def get_program():
    query = """
      SELECT * from program
  """
    res = queryDB(query)
    # print(jsonable_encoder(res))
    return res

@app.get("/program/{program_id}")
def get_program(program_id: int):
    query = """
      SELECT * from program WHERE id = ?
  """
    res = queryDB(query,(program_id,))
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
    """
    Executes a query on the database and returns the results as JSON.
    
    :param query: The SQL query string with placeholders for parameters.
    :param params: A tuple of parameters to substitute into the query.
    :return: The results of the query as a JSON string.
    """
    conn = sqlite3.connect("db.sqlite3")
    cursor = conn.cursor()

    # Execute the query with parameters if provided
    if params is not None:
        cursor.execute(query, params)
    else:
        cursor.execute(query)

    # Fetch all rows
    rows = cursor.fetchall()

    # Get column names
    column_names = [description[0] for description in cursor.description]

    # Convert rows to list of dictionaries
    results = [dict(zip(column_names, row)) for row in rows]

    # Convert list of dictionaries to JSON
    # json_results = json.dumps(results, ensure_ascii=False)

    conn.commit()
    conn.close()
    
    return results

# def queryDB(query, params=None):
#     """
#     Executes a query on the database and returns the results.
    
#     :param query: The SQL query string with placeholders for parameters.
#     :param params: A tuple of parameters to substitute into the query.
#     :return: The results of the query.
#     """
#     conn = sqlite3.connect("db.sqlite3")
#     cursor = conn.cursor()

#     # Execute the query with parameters if provided
#     if params is not None:
#         cursor.execute(query, params)
#     else:
#         cursor.execute(query)

#     res = cursor.fetchall()
#     conn.commit()
#     conn.close()
    
#     return res
