import os, json
import requests
import pandas as pd
from datetime import datetime, timedelta

secret_value = os.getenv("TOKEN")
data = json.loads(secret_value)
TOKEN = data["TOKEN"]
CHAT_ID = data["CHAT_ID"]

cache_file = "data/cache.csv"
stock_filter_file = "data/bist_tum.csv"
title_filter_file = "data/title.txt"
summary_filter_file = "data/summary.txt"

def load_last_index():
    if os.path.exists(cache_file):
        df = pd.read_csv(cache_file)
        if "last_index" in df.columns and not df.empty:
            return int(df["last_index"].iloc[0])
    return 0

def save_last_index(value):
    df = pd.DataFrame({"last_index": [value]})
    df.to_csv(cache_file, index=False, encoding="utf-8")

def send_message(text):
    url = f"https://api.telegram.org/bot{TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": text}
    requests.post(url, data=payload)

def load_stock_filters():
    if os.path.exists(stock_filter_file):
        return set(pd.read_csv(stock_filter_file, encoding="utf-8", usecols=[0]).iloc[:,0].dropna().str.strip().str.upper())
    return set()

def load_title_filters():
    if os.path.exists(title_filter_file):
        with open(title_filter_file, "r", encoding="utf-8") as f:
            return set(line.strip().lower() for line in f if line.strip())
    return set()

def load_summary_filters():
    if os.path.exists(summary_filter_file):
        with open(summary_filter_file, "r", encoding="utf-8") as f:
            filters = []
            for line in f:
                if line.strip():
                    words = [w.strip().lower() for w in line.split(",") if w.strip()]
                    filters.append(words)
            return filters
    return []

def parse_stock_codes(raw_code):
    if not raw_code or str(raw_code).strip() == "":
        return []
    return [c.strip().upper() for c in str(raw_code).split(",") if c.strip()]

def filter_rows(rows):
    stock_filters = load_stock_filters()
    title_filters = load_title_filters()
    summary_filters = load_summary_filters()
    accepted = []
    for row in rows:
        codes = parse_stock_codes(row["stockCode"])
        if not codes:
            pass
        else:
            valid = [c for c in codes if c in stock_filters]
            if not valid:
                continue
            row["stockCode"] = ", ".join(valid)

        title = (row.get("title") or "").lower()
        if title in title_filters:
            continue

        summary = (row.get("summary") or "").lower()
        blocked = False
        for group in summary_filters:
            if all(word in summary for word in group):
                blocked = True
                break
        if blocked:
            continue

        accepted.append(row)
    return accepted

def run():
    session = requests.Session()
    session.headers.update({"User-Agent": "Mozilla/5.0", "Accept": "application/json"})
    url = "https://www.kap.org.tr/tr/api/disclosure/list/main"

    today = datetime.now().strftime("%d.%m.%Y")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%d.%m.%Y")

    payload = {
        "fromDate": yesterday,
        "toDate": today,
        "disclosureTypes": None,
        "fundTypes": None,
        "memberTypes": ["IGS"],
        "mkkMemberOid": None
    }

    try:
        r = session.post(url, json=payload, timeout=30)
        data = r.json()
    except Exception as e:
        send_message(f"API hatası: {e}")
        return

    last_index = load_last_index()
    rows = []
    if isinstance(data, list):
        for item in data:
            basic = item.get("disclosureBasic", {})
            disclosure_index = basic.get("disclosureIndex", 0)
            if disclosure_index > last_index:
                rows.append({
                    "stockCode": basic.get("stockCode"),
                    "title": basic.get("title"),
                    "publishDate": basic.get("publishDate"),
                    "summary": basic.get("summary"),
                    "disclosureIndex": disclosure_index
                })

    rows = filter_rows(rows)
    rows.sort(key=lambda x: x["disclosureIndex"])

    if rows:
        new_index = max([row["disclosureIndex"] for row in rows])
        save_last_index(new_index)
        now = datetime.now().strftime("%d %B %Y, %H:%M")
        for row in rows:
            link = f"https://www.kap.org.tr/tr/Bildirim/{row['disclosureIndex']}"
            msg = (f"{row['stockCode']} | {row['title']}\n"
                   f"{row['publishDate']}\n"
                   f"Özet: {row['summary']}\n"
                   f"Link: {link}\n\n")
            send_message(msg)
        send_message(f"Son index: {new_index}\nSon çalıştırma zamanı: {now}")
    else:
        send_message("Yeni bildirim yok.")

if __name__ == "__main__":
    run()
