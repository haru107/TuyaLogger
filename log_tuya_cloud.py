import tinytuya
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import time
import datetime
import os
import json

# ==========================================
# 1. Tuya Cloud設定
# ==========================================
API_KEY = os.environ["TUYA_ID"]
API_SECRET = os.environ["TUYA_SECRET"]
REGION = "us"

# ==========================================
# 2. Google Sheets設定
# ==========================================
# スプレッドシート自体の名前（ファイル名）
SPREADSHEET_FILENAME = '温湿度記録'

# タブ（シート）の名前をここで指定！
TAB_NAME_SENSOR = '温湿度'
TAB_NAME_OTHER = 'その他'

json_creds = json.loads(os.environ["GSPREAD_JSON"])

# ==========================================
# 3. デバイスリスト
# ==========================================
DEVICES = [
    # --- 【温湿度】グループ ---
    {"name": "01アガベ種",      "id": "eb340b51uem4uu9k",       "group": "sensor"},
    {"name": "ビカク周辺",      "id": "eb1774fyiacplrm3",       "group": "sensor"},
    {"name": "私の部屋",        "id": "ebcb8b0g9wxpzlqs",       "group": "sensor"},
    {"name": "T＆Hセンサー",    "id": "eb73ceeaaec3d87393hgkk", "group": "sensor"},
    {"name": "玄関",            "id": "ebd3f89c8e6e6678808y5z", "group": "sensor"},
    {"name": "温度管理 温室",    "id": "eb3cd4vbwxrrng2l",       "group": "sensor"},

    # --- 【その他】グループ ---
    {"name": "温室ストーブ電力", "id": "ebae8c42a6cd87d5aacis2", "group": "other"},
    {"name": "管理温室 電力",    "id": "ebb6d9b930e29483e2vxfa", "group": "other"},
    {"name": "温室換気扇",      "id": "eb7114169986e12834bj5k", "group": "other"},
    {"name": "温室扇風機",      "id": "eb7310355c82ff5416tqla", "group": "other"},
    {"name": "温室ストーブSW",  "id": "ebca9ehq84qoa0ss",       "group": "other"},
    {"name": "温室東窓",        "id": "eb73efeb305ac565a1fcsh", "group": "other"},
    {"name": "温室西窓",        "id": "eb2582756f99566475rvhj", "group": "other"},
    {"name": "水やり 外",       "id": "ebd3f89c8e6e6678808y5z", "group": "other"},
    {"name": "水やりスイッチ",   "id": "eb81072f59ecc4e7f8gbuk", "group": "other"},
    {"name": "イチゴの水やり",   "id": "ebb36e2a6c5bb44f3fi4ak", "group": "other"}
]

def get_cloud_data(cloud_connection, device):
    """Tuyaクラウドからデータを取得"""
    try:
        result = cloud_connection.getstatus(device['id'])
        if not result or 'result' not in result:
            print(f"  × {device['name']}: 取得失敗 (Offine?)")
            return None

        status_list = result['result']
        
        # --- センサー用変数 ---
        temp = ""
        humid = ""
        battery = ""
        
        # --- その他用変数 ---
        switch = ""
        power = ""
        
        # デバッグ用：何が返ってきているか全部見る
        raw_data = str(status_list)

        for item in status_list:
            code = item.get('code')
            value = item.get('value')

            # --- 温度・湿度・電池 ---
            if code in ['va_temperature', 'temp_current']:
                temp = value / 10.0
            elif code in ['va_humidity', 'humidity_value']:
                humid = value
            elif code == 'battery_percentage':
                battery = value
            
            # --- スイッチ (いろんな名前のパターンに対応) ---
            elif code in ['switch_1', 'switch', 'led_switch']:
                switch = "ON" if value else "OFF"
            
            # --- 電力 (いろんな名前のパターンに対応) ---
            elif code in ['cur_power', 'power', 'power_w']:
                power = value / 10.0

        # グループに応じて返すデータを変える
        if device['group'] == 'sensor':
            return [device['name'], temp, humid, battery]
        else:
            # その他グループは [名前, スイッチ, 電力, (念のため生データ)]
            return [device['name'], switch, power, raw_data]

    except Exception as e:
        print(f"  × {device['name']}: エラー {e}")
        return None

def write_to_sheet(rows, tab_name):
    """指定された名前のタブに書き込み"""
    if not rows:
        print(f"  No data to write for {tab_name}.")
        return
    
    print(f"Writing {len(rows)} rows to sheet '{tab_name}'...")
    
    scope = ['https://spreadsheets.google.com/feeds','https://www.googleapis.com/auth/drive']
    creds = ServiceAccountCredentials.from_json_keyfile_dict(json_creds, scope)
    client = gspread.authorize(creds)
    
    try:
        # ファイルを開く
        spreadsheet = client.open(SPREADSHEET_FILENAME)
        # タブを名前で探す
        sheet = spreadsheet.worksheet(tab_name)
    except gspread.exceptions.WorksheetNotFound:
        print(f"エラー: シート名 '{tab_name}' が見つかりません！スプレッドシートのタブ名を変更してください。")
        return
    except Exception as e:
        print(f"スプレッドシートエラー: {e}")
        return

    # 日本時間 (UTC+9)
    JST = datetime.timezone(datetime.timedelta(hours=9), 'JST')
    now = datetime.datetime.now(JST).strftime('%Y-%m-%d %H:%M:%S')
    
    for row in rows:
        full_row = [now] + row
        sheet.append_row(full_row)
        print(f"  Recorded to {tab_name}: {full_row}")

if __name__ == "__main__":
    print("Connecting to Tuya Cloud...")
    c = tinytuya.Cloud(apiRegion=REGION, apiKey=API_KEY, apiSecret=API_SECRET)
    
    sensor_rows = []
    other_rows = []

    for dev in DEVICES:
        data = get_cloud_data(c, dev)
        if data:
            if dev.get('group') == 'sensor':
                sensor_rows.append(data)
            else:
                other_rows.append(data)
            time.sleep(1)

    print("--- Processing Sensors ---")
    write_to_sheet(sensor_rows, TAB_NAME_SENSOR)
    
    print("--- Processing Others ---")
    write_to_sheet(other_rows, TAB_NAME_OTHER)
