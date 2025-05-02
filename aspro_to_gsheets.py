# aspro_to_gsheets.py

import os
import base64
import json
import requests
import gspread
from datetime import datetime
from google.oauth2.credentials import Credentials

# --- Load credentials from GOOGLE_TOKEN env var ---
token_info = json.loads(base64.b64decode(os.getenv("GOOGLE_TOKEN")))
creds = Credentials.from_authorized_user_info(token_info)
client = gspread.authorize(creds)

# --- CONFIG FROM ENV ---
ASPRO_API_KEY = os.getenv("ASPRO_API_KEY")
ASPRO_DOMAIN = os.getenv("ASPRO_DOMAIN")
SPREADSHEET_NAME = os.getenv("SPREADSHEET_NAME")
sheet = client.open(SPREADSHEET_NAME).sheet1

# --- Helpers ---
def aspro_get(endpoint, params=None):
    url = f"https://{ASPRO_DOMAIN}/api/v1{endpoint}"
    if params is None:
        params = {}
    params['api_key'] = ASPRO_API_KEY
    response = requests.get(url, params=params)
    return response.json().get('response', {}).get('items', [])

def get_project_name(model_id):
    if not model_id:
        return ""
    try:
        url = f"https://{ASPRO_DOMAIN}/api/v1/module/st/project/get/{model_id}"
        response = requests.get(url, params={"api_key": ASPRO_API_KEY})
        return response.json()['response'].get('name', '')
    except:
        return ""

def get_currency_map():
    items = aspro_get("/module/fin/currencies/list")
    return {item['id']: item['code'] for item in items}

# --- Main Logic ---
def collect_financial_data():
    currency_map = get_currency_map()
    rows = [["Дата", "Тип", "Статья", "Проект", "План", "Валюта (План)", "Факт", "Валюта (Факт)", "Комментарий"]]

    # --- PLAN ---
    plans = aspro_get("/module/fin/plan_money/list")
    for p in plans:
        plan_date = p.get("startdate", "")
        plan_amount = p.get("amount", 0)
        plan_currency = currency_map.get(p.get("currency_id", None), "")
        type_str = "Доход" if p.get("type") == 10 else "Расход"
        project_name = get_project_name(p.get("model_id"))
        comment = p.get("description", "")
        article = p.get("title", "")

        rows.append([plan_date, type_str, article, project_name, plan_amount, plan_currency, "", "", comment])

    # --- FACT ---
    facts = aspro_get("/module/fin/transaction/list")
    for f in facts:
        fact_date = f.get("date", "")
        income = f.get("income", 0)
        outcome = f.get("outcome", 0)
        fact_amount = income if income else -outcome
        fact_currency = currency_map.get(f.get("currency_id", None), "")
        type_str = "Доход" if income else "Расход"
        project_name = get_project_name(f.get("model_id"))
        comment = f.get("description", "")
        article = f.get("title", "")

        rows.append([fact_date, type_str, article, project_name, "", "", fact_amount, fact_currency, comment])

    return rows

# --- Upload to Google Sheets ---
def update_sheet():
    data = collect_financial_data()
    sheet.clear()
    sheet.update("A1", data)

if __name__ == "__main__":
    update_sheet()
    print("Данные успешно обновлены в таблице.")
