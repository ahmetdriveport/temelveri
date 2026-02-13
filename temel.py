import os, json
import requests
import pandas as pd
from datetime import datetime, timedelta

# Tek secret: TOKEN (JSON içerikli)
secret_value = os.getenv("TOKEN")
data = json.loads(secret_value)
TOKEN = data["TOKEN"]
CHAT_ID = data["CHAT_ID"]

cache_file = "data/cache.csv"
filter_file = "data/filters.csv"

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

def normalize(text):
    if text is None:
        return ""
    return str(text).replace(",", "").replace("  ", " ").strip().lower()

def apply_filter(rows):
    if os.path.exists(filter_file):
        filt = pd.read_csv(filter_file, encoding="utf-8", usecols=[0])
        exclude_titles = set(normalize(t) for t in filt.iloc[:, 0].dropna())
        return [row for row in rows if normalize(row["title"]) not in exclude_titles]
    return rows

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

    rows = apply_filter(rows)
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
                   f"Link: {link}")
            send_message(msg)
        send_message(f"Son index: {new_index}\nSon çalıştırma zamanı: {now}")
    else:
        send_message("Yeni bildirim yok.")

if __name__ == "__main__":
    run()
