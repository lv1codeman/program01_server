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
# ]
origins = [
    "https://*",
    "http://*",
]

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
