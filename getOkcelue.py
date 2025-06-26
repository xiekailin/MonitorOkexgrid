import requests
import json
import hmac
import base64
from datetime import datetime, timezone # 修正点 1: 引入timezone
import os
from dotenv import load_dotenv

load_dotenv()

# --- 1. 配置你的API信息 ---
API_KEY = os.getenv('API_KEY')
SECRET_KEY = os.getenv('SECRET_KEY')
PASSPHRASE = os.getenv('PASSPHRASE')

# --- 2. 签名和请求函数 ---
def get_sign(timestamp, method, request_path, body, secret_key):
    if str(body) == '{}' or str(body) == 'None':
        body = ''
    message = str(timestamp) + str.upper(method) + request_path + str(body)
    mac = hmac.new(bytes(secret_key, encoding='utf-8'), bytes(message, encoding='utf-8'), digestmod='sha256')
    d = mac.digest()
    return base64.b64encode(d)

def okx_request(method, request_path, body=''):
    base_url = "https://www.okx.com"
    url = base_url + request_path
    
    # 修正点 2: 使用推荐的方式获取UTC时间
    timestamp = datetime.now(timezone.utc).isoformat("T", "milliseconds").replace('+00:00', 'Z')
    
    headers = {
        'Content-Type': 'application/json',
        'OK-ACCESS-KEY': API_KEY,
        'OK-ACCESS-SIGN': get_sign(timestamp, method, request_path, body, SECRET_KEY),
        'OK-ACCESS-TIMESTAMP': timestamp,
        'OK-ACCESS-PASSPHRASE': PASSPHRASE,
        # 'x-simulated-trading': '1' # 如果是模拟盘，取消此行注释
    }
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"API请求出错: {e}")
        return None

# --- 3. 主函数：获取并打印所有运行中的网格策略 ---
def get_running_grid_strategies():
    print("正在获取您运行中的网格策略列表...")
    
    # 修正点 3: 使用了正确的API端点路径
    request_path = '/api/v5/tradingBot/grid/orders-algo-pending?algoOrdType=grid'
    
    result = okx_request('GET', request_path)
    
    # 修正点 4: 增强错误处理，防止因API失败导致程序崩溃
    if not result:
        print("无法从API获取数据，请检查网络或API配置。")
        return

    if result.get('code') == '0':
        strategies = result.get('data')
        if not strategies:
            print("未找到任何正在运行的网格策略。")
            return
            
        print("\n--- 以下是您正在运行的网格策略 ---")
        for strategy in strategies:
            # 将时间戳从毫秒转换为可读日期
            create_time = datetime.fromtimestamp(int(strategy.get('cTime'))/1000).strftime('%Y-%m-%d %H:%M:%S')
            
            print(f"交易对 (instId): {strategy.get('instId')}")
            print(f"状态 (state): {strategy.get('state')}")
            print(f"创建时间 (cTime): {create_time}")
            print(f"策略ID (algoId): {strategy.get('algoId')}  <-- 这就是您需要的ID")
            print("-" * 20)
        print("------------------------------------")
        
    else:
        print(f"获取失败，错误代码: {result.get('code')}, 错误信息: {result.get('msg', '未知错误')}")

if __name__ == '__main__':
    get_running_grid_strategies()

