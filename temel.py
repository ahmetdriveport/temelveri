import os, json
import requests
import pandas as pd
from datetime import datetime, timedelta
import unicodedata
import re

secret_value = os.getenv("TOKEN")
data = json.loads(secret_value)
TOKEN = data["TOKEN"]
CHAT_ID = data["CHAT_ID"]

cache_file = "data/cache.csv"

def normalize_text(s):
    if not s:
        return ""
    s = unicodedata.normalize("NFKC", s)
    s = s.lower()
    s = re.sub(r"\s+", "", s)
    return s

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

def send_document(file_path, caption=""):
    url = f"https://api.telegram.org/bot{TOKEN}/sendDocument"
    with open(file_path, "rb") as f:
        payload = {"chat_id": CHAT_ID, "caption": caption}
        files = {"document": f}
        requests.post(url, data=payload, files=files)

def get_disclosure_detail(disclosure_index):
    url = f"https://www.kap.org.tr/tr/api/disclosure/detail/{disclosure_index}"
    r = requests.get(url, timeout=30)
    return r.json()

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

    rows.sort(key=lambda x: x["disclosureIndex"])

    if rows:
        new_index = max([row["disclosureIndex"] for row in rows])
        save_last_index(new_index)
        now = datetime.now().strftime("%d %B %Y, %H:%M")
        for row in rows:
            title_norm = normalize_text(row["title"])
            if title_norm == "payalımsatımbildirimi":
                detail = get_disclosure_detail(row["disclosureIndex"])
                attachments = detail.get("attachments", [])
                if attachments:
                    pdf_url = "https://www.kap.org.tr" + attachments[0].get("fileUrl")
                    try:
                        r_pdf = requests.get(pdf_url, timeout=30)
                        if "application/pdf" in r_pdf.headers.get("Content-Type", ""):
                            file_path = f"data/{row['disclosureIndex']}.pdf"
                            os.makedirs("data", exist_ok=True)
                            with open(file_path, "wb") as f:
                                f.write(r_pdf.content)
                            send_document(file_path, caption=row["title"])
                        else:
                            send_message("PDF bulunamadı veya dosya tipi desteklenmiyor.")
                    except Exception as e:
                        send_message(f"PDF indirilemedi: {e}")
                else:
                    send_message("Bu bildirimin ek dosyası yok.")
            else:
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
