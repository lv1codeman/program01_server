import pandas as pd
import sqlite3
import argparse

# 設置命令行參數解析
parser = argparse.ArgumentParser(description='Import Excel data into SQLite database.')
parser.add_argument('excel_file', type=str, help='Path to the Excel file')
parser.add_argument('table_name', type=str, help='Name of the table to create in SQLite')
parser.add_argument('--header', type=int, default=0, help='Row number to use as the column names. Default is 0 (first row).')
args = parser.parse_args()

# 讀取 Excel 文件，指定 header 行
df = pd.read_excel(args.excel_file, header=args.header, dtype=str)


# 所有表的第一個欄位不匯入（ID欄位由sqlite資料庫自動累加）
df.drop(df.columns[0], axis=1, inplace=True)

# 指定int的欄位
# integer_columns = ['id', 'age']
integer_columns = []

for col in integer_columns:
    df[col] = df[col].astype(int)

# 連接到 SQLite 資料庫
targer_db = 'program01.db'
conn = sqlite3.connect(targer_db)
cursor = conn.cursor()

# 清空指定的表
cursor.execute(f"DELETE FROM {args.table_name};")
conn.commit()

# 將該表對應到 sqlite_sequence 中的 seq 值歸零
cursor.execute(f"DELETE FROM sqlite_sequence WHERE name='{args.table_name}';")
conn.commit()

# 將 DataFrame 寫入 SQLite 資料庫的表中
df.to_sql(args.table_name, conn, if_exists='append', index=False)

# 確保資料已提交
conn.commit()

# 關閉連接
conn.close()

print(f"Data from {args.excel_file} has been successfully imported into table {args.table_name} in {targer_db}")
