import requests
import time
import json
import hmac
import base64
from datetime import datetime, timezone
import os
from dotenv import load_dotenv

load_dotenv()

# --- 1. 配置信息 (请确认无误) ---
API_KEY = os.getenv('API_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
PASSPHRASE = os.getenv('PASSPHRASE')
BARK_DEVICE_KEY = os.getenv('BARK_DEVICE_KEY')
ALGO_ID = os.getenv('ALGO_ID')

# --- 2. OKX API请求签名函数 (无需改动) ---
def get_sign(timestamp, method, request_path, body, secret_key):
    if str(body) == '{}' or str(body) == 'None':
        body = ''
    message = str(timestamp) + str.upper(method) + request_path + str(body)
    mac = hmac.new(bytes(secret_key, encoding='utf-8'), bytes(message, encoding='utf-8'), digestmod='sha256')
    d = mac.digest()
    return base64.b64encode(d)

# --- 3. OKX API请求函数 (无需改动) ---
def okx_request(method, request_path, body=''):
    base_url = "https://www.okx.com"
    url = base_url + request_path
    timestamp = datetime.now(timezone.utc).isoformat("T", "milliseconds").replace('+00:00', 'Z')
    headers = {
        'Content-Type': 'application/json',
        'OK-ACCESS-KEY': API_KEY,
        'OK-ACCESS-SIGN': get_sign(timestamp, method, request_path, body, SECRET_KEY),
        'OK-ACCESS-TIMESTAMP': timestamp,
        'OK-ACCESS-PASSPHRASE': PASSPHRASE,
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API请求出错: {e}")
        if e.response:
            try:
                print(f"服务器返回错误详情: {e.response.json()}")
            except json.JSONDecodeError:
                print(f"无法解析服务器返回的错误内容: {e.response.text}")
        return None

# --- 4. Bark通知函数 (无需改动) ---
def send_bark_message(title, body, group="OKX网格监控"):
    if not BARK_DEVICE_KEY or BARK_DEVICE_KEY == '你的Bark设备Key':
        print("未配置Bark设备Key，跳过通知。")
        return
    bark_api_url = "https://api.day.app/push"
    payload = {"device_key": BARK_DEVICE_KEY, "title": title, "body": body, "group": group, "sound": "calypso"}
    headers = {'Content-Type': 'application/json'}
    try:
        requests.post(bark_api_url, headers=headers, data=json.dumps(payload), timeout=10)
        print("Bark消息已发送。")
    except Exception as e:
        print(f"发送Bark消息失败: {e}")

# --- 5. 主监控循环 (已重构，增加"防御性"编程) ---
def get_combined_strategy_data(algo_id):
    # API Call 1: 获取策略总览信息
    details_path = f'/api/v5/tradingBot/grid/orders-algo-details?algoId={algo_id}&algoOrdType=grid'
    details_result = okx_request('GET', details_path)
    
    # API Call 2: 获取策略持仓详情 (为了准确的浮动盈亏)
    # 修正：为positions接口也加上algoOrdType=grid参数
    positions_path = f'/api/v5/tradingBot/grid/positions?algoId={algo_id}&algoOrdType=grid'
    positions_result = okx_request('GET', positions_path)
    
    if not details_result or not positions_result or details_result.get('code') != '0' or positions_result.get('code') != '0':
        print("获取数据失败，一个或多个API调用出错。")
        return None

    details_data = details_result['data'][0]
    
    # --- 核心修正：处理positions_result['data']为空列表的情况 ---
    positions_data_list = positions_result.get('data', [])
    floating_pnl = 0.0 # 默认浮动盈亏为0

    if positions_data_list: # 只有当列表不为空时，才从中提取数据
        positions_data = positions_data_list[0]
        floating_pnl = float(positions_data.get('upl', 0))
    # --- 修正结束 ---

    combined_data = {
        "gridProfit": float(details_data.get('gridProfit', 0)),
        "totalPnl": float(details_data.get('totalPnl', 0)),
        "actualPnl": float(details_data.get('actualPnl', 0)),
        "state": details_data.get('state'),
        "floatingPnl": floating_pnl, # 使用我们安全获取到的值
    }
    return combined_data

def main():
    if '你的' in API_KEY or '你的' in SECRET_KEY or '你的' in PASSPHRASE:
        print("致命错误：请填写完整的API配置信息。")
        return
        
    print("配置信息检查通过，启动OKX网格利润监控脚本 (使用Bark通知)...")
    last_grid_profit = 0.0
    is_first_run = True
    
    while True:
        strategy_data = get_combined_strategy_data(ALGO_ID)
        
        if not strategy_data:
            print("60秒后重试...")
            time.sleep(60)
            continue

        grid_profit = strategy_data["gridProfit"]
        floating_pnl = strategy_data["floatingPnl"]
        total_pnl = strategy_data["totalPnl"]
        withdrawable_profit = strategy_data["actualPnl"]
        state = strategy_data["state"]

        print(f"[{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}] 状态:{state} | 网格利润:{grid_profit:.4f} | 浮动盈亏:{floating_pnl:.4f} | 总盈亏:{total_pnl:.4f} | 可提取:{withdrawable_profit:.4f}")

        if is_first_run:
            last_grid_profit = grid_profit
            is_first_run = False
            title = "✅ OKX网格监控已启动"
            body = (f"总收益: {total_pnl:+.4f} USDT\n"
                    f"--------------------\n"
                    f"网格收益: {grid_profit:.4f} USDT\n"
                    f"未配对收益: {floating_pnl:+.4f} USDT\n"
                    f"当前可提取: {withdrawable_profit:.4f} USDT")
            send_bark_message(title, body)
        
        elif grid_profit > last_grid_profit:
            new_profit = grid_profit - last_grid_profit
            print(f"检测到新利润！新增: {new_profit:.4f}")
            title = f"🎉 网格新利润 +{new_profit:.4f} USDT"
            body = (f"总收益: {total_pnl:+.4f} USDT\n"
                    f"--------------------\n"
                    f"网格收益: {grid_profit:.4f} USDT\n"
                    f"未配对收益: {floating_pnl:+.4f} USDT\n"
                    f"当前可提取: {withdrawable_profit:.4f} USDT")
            send_bark_message(title, body)
            last_grid_profit = grid_profit

        time.sleep(60)

if __name__ == '__main__':
    main()