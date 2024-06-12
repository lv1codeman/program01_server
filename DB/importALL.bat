@echo off

python .\xlsxToDB.py .\members.xlsx members --header 0
python .\xlsxToDB.py .\programs.xlsx programs --header 0
python .\xlsxToDB.py .\categories.xlsx categories --header 0
python .\xlsxToDB.py .\domains.xlsx domains --header 0
python .\xlsxToDB.py .\subjects.xlsx subjects --header 0
python .\xlsxToDB.py .\scores.xlsx scores --header 0

echo All data has been successfully imported.
pause
