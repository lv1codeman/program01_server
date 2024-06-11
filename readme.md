## 介紹

Program01 的 server 端

## 執行前安裝

```
pip install fastapi uvicorn python-jose[cryptography] python-dotenv
```

## 執行方式

### 經由 debug 模式開啟

已經在.vscode/launch.json 設定好啟動參數，按快捷鍵 F5 即可執行

### 手動輸入指令

開在預設的 PORT

```
uvicorn main:app --reload
```

指定開在 PORT 1202

```
uvicorn main:app --host '0.0.0.0' --port 1202 --reload
```

## 虛擬環境

新建

```
python -m venv env
```

執行

```
env\Scripts\activate
```
