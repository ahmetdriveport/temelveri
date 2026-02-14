import requests
import pandas as pd
from io import BytesIO
import os

URL = "https://kap.org.tr/tr/api/company/indices/excel"

def fetch_tum():
    resp = requests.get(URL, timeout=30)
    resp.raise_for_status()
    df_raw = pd.read_excel(BytesIO(resp.content), header=None)

    tum_codes = []
    cur = None
    for i in range(len(df_raw)):
        vals = [str(df_raw.iat[i, j]).strip() if pd.notna(df_raw.iat[i, j]) else "" 
                for j in range(min(5, df_raw.shape[1]))]

        # Başlık satırını yakala
        if any(v.upper() == "TÜM" for v in vals):
            cur = "TÜM"
            continue

        # Eğer TÜM başlığı altındaysak ve satır numara ile başlıyorsa → hisse satırı
        if cur == "TÜM" and vals and vals[0].isdigit():
            if len(vals) > 1 and vals[1]:
                tum_codes.append(vals[1])

        # Başka bir endeks başlığına geçerse TÜM biter
        if cur == "TÜM" and any(v.upper().startswith("BIST") for v in vals):
            break

    return tum_codes

def save_to_csv(codes, path="data/bist_tum.csv"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pd.DataFrame({"stockCode": codes}).to_csv(path, index=False, encoding="utf-8")
    print(f"✅ {len(codes)} hisse kodu {path} dosyasına yazıldı.")

if __name__ == "__main__":
    codes = fetch_tum()
    save_to_csv(codes)
