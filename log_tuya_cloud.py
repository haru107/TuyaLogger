import tinytuya
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import datetime
import os
import json

# ==========================================
# 1. Tuya Cloud設定 (金庫から読み込む)
# ==========================================
# GitHubのSecretsから値を取得します
API_KEY = os.environ["TUYA_ID"]
API_SECRET = os.environ["TUYA_SECRET"]
REGION = "us"

# ==========================================
# 2. Google Sheets設定 (金庫から読み込む)
# ==========================================
SHEET_NAME = '温湿度記録'
# JSONファイルではなく、環境変数の文字列から認証情報を作ります
json_creds = json.loads(os.environ["GSPREAD_JSON"])

# ==========================================
# 3. デバイスリスト
# ==========================================
SENSORS = [
    {"name": "01アガベ種", "id": "eb340b51uem4uu9k"},
    {"name": "ビカク周辺", "id": "eb1774fyiacplrm3"},
    {"name": "私の部屋",   "id": "ebcb8b0g9wxpzlqs"},
    {"name": "T＆Hセンサー", "id": "eb73ceeaaec3d87393hgkk"},
    {"name": "玄関",       "id": "ebd3f89c8e6e6678808y5z"}
]

def get_cloud_data(cloud_connection, device):
    """Tuyaクラウドからデータを取得"""
    try:
        result = cloud_connection.getstatus(device['id'])
        if not result or 'result' not in result:
            print(f"  × {device['name']}: データ取得失敗")
            return None

        status_list = result['result']
        temp = None
        humid = None
        battery = None

        for item in status_list:
            code = item.get('code')
            value = item.get('value')
            if code == 'va_temperature':
                temp = value / 10.0
            elif code == 'va_humidity':
                humid = value
            elif code == 'battery_percentage':
                battery = value

        return [device['name'], temp, humid, battery]
    except Exception as e:
        print(f"  × {device['name']}: エラー {e}")
        return None

def write_to_sheet(rows):
    """スプレッドシートに書き込み"""
    if not rows:
        return
    
    print(f"Writing {len(rows)} rows to Google Sheets...")
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    # ファイル読み込みではなく、辞書データから認証
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json_creds, scope)
    client = gspread.authorize(creds)
    sheet = client.open(SHEET_NAME).sheet1
    
    # 日本時間 (UTC+9)
    JST = datetime.timezone(datetime.timedelta(hours=9), 'JST')
    now = datetime.datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
    
    for row in rows:
        full_row = [now] + row
        sheet.append_row(full_row)
        print(f"  Recorded: {full_row}")

if __name__ == "__main__":
    print("Connecting to Tuya Cloud...")
    c = tinytuya.Cloud(apiRegion=REGION, apiKey=API_KEY, apiSecret=API_SECRET)
    
    valid_data_rows = []

    for sensor in SENSORS:
        data = get_cloud_data(c, sensor)
        if data:
            valid_data_rows.append(data)
            time.sleep(1)

    if valid_data_rows:
        write_to_sheet(valid_data_rows)
    else:
        print("データが取得できませんでした。")