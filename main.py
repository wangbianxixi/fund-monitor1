# -*- coding: utf-8 -*-
import requests
import datetime
import os

# ================= 配置区域 =================
WEBHOOK_URL = os.getenv("DINGTALK_WEBHOOK")
INDEX_SYMBOL = "zs980017"  # 国证半导体芯片 (新浪财经格式)
DROP_THRESHOLD = -3.0  # 跌幅超过 3% 提醒
# ===========================================

def send_message(text):
    """发送消息到钉钉"""
    if not WEBHOOK_URL:
        print("未配置 Webhook")
        return
    headers = {'Content-Type': 'application/json'}
    # 确保内容包含句号 .，否则钉钉会拦截
    data = {
        "msgtype": "text",
        "text": {
            "content": f"[监控] 时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}.\n\n{text}."
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

def get_index_data():
    """从新浪财经获取指数数据"""
    # 新浪财经接口，非常稳定
    url = f"http://hq.sinajs.cn/rn=/js/zs.js?list={INDEX_SYMBOL}"
    # 需要设置 referer，否则可能被拦截
    headers = {
        "Referer": "http://finance.sina.com.cn/",
        "User-Agent": "Mozilla/5.0"
    }
    resp = requests.get(url, headers=headers, timeout=10)
    resp.encoding = 'gbk'  # 新浪财经是 gbk 编码
    text = resp.text
    
    # 解析数据格式：var hq_str_zs980017="名称，当前价，昨收，今开，最高，最低，..."
    data = text.split('"')[1].split(',')
    
    result = {
        'name': data[0],
        'price': data[1],
        'yesterday_close': data[2],
        'open': data[3],
        'high': data[4],
        'low': data[5],
        'change_percent': float(data[6])  # 涨跌幅
    }
    return result

def main():
    print("开始运行监控脚本...")
    
    try:
        # 获取指数数据
        data = get_index_data()
        
        msg_list = []
        msg_list.append(f"指数：{data['name']}.")
        msg_list.append(f"当前点位：{data['price']}.")
        msg_list.append(f"今日涨跌：{data['change_percent']:.2f}%.")
        msg_list.append("-" * 30)
        
        trigger_alert = False
        
        # 涨跌幅信号
        if data['change_percent'] < DROP_THRESHOLD:
            msg_list.append(f"[买入信号] 跌幅>{abs(DROP_THRESHOLD)}%，关注加仓！.")
            trigger_alert = True
        elif data['change_percent'] > 3.0:
            msg_list.append(f"[止盈信号] 涨幅>3%，注意波动！.")
            trigger_alert = True
        
        # 发送消息
        if trigger_alert:
            send_message("\n".join(msg_list))
        else:
            # 即使无信号也发送，方便您确认脚本每天正常运行
            msg_list.append("今日无特殊信号，监控正常运行.")
            send_message("\n".join(msg_list))
            
    except Exception as e:
        # 发送报错消息
        send_message(f"[监控] 脚本运行出错：{str(e)}.")
        print(f"错误详情：{e}")

if __name__ == "__main__":
    main()
