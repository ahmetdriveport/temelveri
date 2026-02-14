import requests
import pandas as pd
from io import BytesIO
import os

URL = "https://kap.org.tr/tr/api/company/indices/excel"

def fetch_tum():
    resp = requests.get(URL, timeout=30)
    resp.raise_for_status()
    df_raw = pd.read_excel(BytesIO(resp.content), header=None)

    endeks_dict = {}
    cur = None
    for i in range(len(df_raw) - 1):
        vals = [str(df_raw.iat[i, j]).strip() if pd.notna(df_raw.iat[i, j]) else "" 
                for j in range(min(5, df_raw.shape[1]))]
        nxt = str(df_raw.iat[i+1, 0]).strip() if pd.notna(df_raw.iat[i+1, 0]) else ""
        baslik = next((v for v in vals if v.upper().startswith("BIST") or v.upper()=="TÜM"), None)
        if baslik and nxt == "1":
            cur = baslik
            endeks_dict[cur] = []
            continue
        if vals and vals[0].isdigit() and cur:
            endeks_dict[cur].append(vals[1] if len(vals) > 1 else "")

    df_endeks = pd.DataFrame({k: pd.Series(v) for k, v in endeks_dict.items()})

    # TÜM kolonunu al
    tum_list = df_endeks.get("TÜM").dropna().astype(str).str.strip().unique()
    return tum_list

def save_to_csv(codes, path="data/bist_tum.csv"):
    os.makedirs(os.path.dirname(path), exist_ok=True)
    pd.DataFrame({"stockCode": codes}).to_csv(path, index=False, encoding="utf-8")
    print(f"✅ {len(codes)} hisse kodu {path} dosyasına yazıldı.")

if __name__ == "__main__":
    codes = fetch_tum()
    save_to_csv(codes)
