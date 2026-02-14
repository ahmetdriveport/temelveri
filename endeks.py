import requests,pandas as pd,os
from io import BytesIO

URL="https://kap.org.tr/tr/api/company/indices/excel"

def fetch_bist_tum():
    r=requests.get(URL,timeout=30);r.raise_for_status()
    df=pd.read_excel(BytesIO(r.content),header=None)
    codes=[];in_tum=False
    for i in range(len(df)):
        vals=[str(df.iat[i,j]).strip() if pd.notna(df.iat[i,j]) else "" for j in range(min(5,df.shape[1]))]
        if any(v.upper()=="BIST TÜM" for v in vals):in_tum=True;continue
        if in_tum and vals and vals[0].isdigit() and len(vals)>1 and vals[1]:codes.append(vals[1])
        if in_tum and any(v.upper().startswith("BIST") and v.upper()!="BIST TÜM" for v in vals):break
    if not codes:raise ValueError("BIST TÜM endeksi altında hisse bulunamadı.")
    return codes

def save_to_csv(codes,path="data/bist_tum.csv"):
    os.makedirs(os.path.dirname(path),exist_ok=True)
    pd.DataFrame({"stockCode":codes}).to_csv(path,index=False,encoding="utf-8")
    print(f"✅ {len(codes)} hisse kodu {path} dosyasına yazıldı.")

if __name__=="__main__":
    save_to_csv(fetch_bist_tum())
