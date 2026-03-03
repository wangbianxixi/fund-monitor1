# -*- coding: utf-8 -*-
import requests
import datetime
import os
import pytz

# ================= 配置区域 =================
WEBHOOK_URL = os.getenv("DINGTALK_WEBHOOK")
# 尝试多种指数代码格式
INDEX_SYMBOLS = [
    "sz980017",    # 国证半导体芯片 (深市)
    "zs980017",    # 另一种格式
    "bk0917",      # 半导体板块
    "sh000001",    # 上证指数 (备用测试)
]
DROP_THRESHOLD = -3.0  # 跌幅超过 3% 提醒
# ===========================================

def send_message(text):
    """发送消息到钉钉"""
    if not WEBHOOK_URL:
        print("未配置 Webhook")
        return
    headers = {'Content-Type': 'application/json'}
    data = {
        "msgtype": "text",
        "text": {
            "content": f"[监控] 时间：{get_beijing_time()}\n\n{text}."
        }
    }
    try:
        res = requests.post(WEBHOOK_URL, json=data, headers=headers, timeout=10)
        if res.status_code == 200:
            print("消息发送成功")
        else:
            print(f"发送失败：{res.status_code}")
    except Exception as e:
        print(f"发送异常：{e}")

def get_beijing_time():
    """获取北京时间"""
    try:
        tz = pytz.timezone('Asia/Shanghai')
        beijing_time = datetime.datetime.now(tz)
        return beijing_time.strftime('%Y-%m-%d %H:%M')
    except:
        utc_time = datetime.datetime.utcnow()
        beijing_time = utc_time + datetime.timedelta(hours=8)
        return beijing_time.strftime('%Y-%m-%d %H:%M')

def get_index_data(symbol):
    """从新浪财经获取指数数据"""
    url = f"http://hq.sinajs.cn/list={symbol}"
    headers = {
        "Referer": "http://finance.sina.com.cn/",
        "User-Agent": "Mozilla/5.0"
    }
    resp = requests.get(url, headers=headers, timeout=10)
    resp.encoding = 'gbk'
    text = resp.text
    
    print(f"尝试代码：{symbol}")
    print(f"原始响应：{text[:200]}")
    
    # 检查是否返回有效数据
    if '=' not in text or '"' not in text:
        return None
    
    data_part = text.split('"')[1]
    data = data_part.split(',')
    
    print(f"解析后字段数：{len(data)}")
    
    if len(data) < 7:
        return None
    
    return {
        'symbol': symbol,
        'name': data[0],
        'price': data[1],
        'change_percent': float(data[6]) if data[6] else 0.0
    }

def main():
    print("开始运行监控脚本...")
    print(f"当前北京时间：{get_beijing_time()}")
    
    try:
        # 尝试多个指数代码
        data = None
        for symbol in INDEX_SYMBOLS:
            result = get_index_data(symbol)
            if result and result['name']:  # 确保有名称
                data = result
                print(f"成功获取数据：{data['name']}")
                break
        
        if not data:
            raise Exception("所有指数代码都未能获取有效数据")
        
        msg_list = []
        msg_list.append(f"指数：{data['name']} ({data['symbol']}).")
        msg_list.append(f"当前点位：{data['price']}.")
        msg_list.append(f"今日涨跌：{data['change_percent']:.2f}%.")
        msg_list.append("-" * 30)
        
        trigger_alert = False
        
        if data['change_percent'] < DROP_THRESHOLD:
            msg_list.append(f"[买入信号] 跌幅>{abs(DROP_THRESHOLD)}%，关注加仓！.")
            trigger_alert = True
        elif data['change_percent'] > 3.0:
            msg_list.append(f"[止盈信号] 涨幅>3%，注意波动！.")
            trigger_alert = True
        
        if trigger_alert:
            send_message("\n".join(msg_list))
        else:
            msg_list.append("今日无特殊信号，监控正常运行.")
            send_message("\n".join(msg_list))
            
    except Exception as e:
        send_message(f"[监控] 脚本运行出错：{str(e)}.")
        print(f"错误详情：{e}")

if __name__ == "__main__":
    main()
