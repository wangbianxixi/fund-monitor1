# -*- coding: utf-8 -*-
import akshare as ak
import requests
import pandas as pd
import datetime
import os

# ================= 配置区域 =================
WEBHOOK_URL = os.getenv("DINGTALK_WEBHOOK")
INDEX_SYMBOL = "sz980017"  # 国证半导体芯片
PE_LOW_THRESHOLD = 20
PE_HIGH_THRESHOLD = 80
DROP_THRESHOLD = -0.03
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
            "content": f"[监控提醒] 时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n{text}"
        }
    }
    try:
        res = requests.post(WEBHOOK_URL, json=data, headers=headers, timeout=10)
        if res.status_code == 200:
            print("消息发送成功")
        else:
            print(f"发送失败：{res.status_code}")
    except Exception as e:
        print(f"异常：{e}")

def main():
    print("开始运行监控脚本...")
    try:
        # 1. 获取指数估值数据 (PE-TTM)
        df_pe = ak.stock_index_value_hist(symbol=INDEX_SYMBOL, period="pe")
        
        # 2. 获取当前行情
        df_quote = ak.stock_zh_index_spot(symbol=[INDEX_SYMBOL])
        
        # 3. 提取数据
        current_pe = df_pe['估值'].iloc[-1]
        history_pe = df_pe['估值'].dropna()
        
        # 4. 计算百分位 (近 5 年)
        percentile = (history_pe < current_pe).sum() / len(history_pe) * 100
        
        # 5. 获取涨跌幅
        change_percent = df_quote['涨跌幅'].iloc[0] / 100.0
        
        # 6. 构建消息
        msg_list = []
        msg_list.append(f"指数：国证半导体芯片 ({INDEX_SYMBOL})")
        msg_list.append(f"当前 PE-TTM: {current_pe:.2f}")
        msg_list.append(f"PE 百分位：{percentile:.2f}%")
        msg_list.append(f"今日涨跌：{change_percent*100:.2f}%")
        msg_list.append("-" * 30)
        
        trigger_alert = False
        
        if percentile < PE_LOW_THRESHOLD:
            msg_list.append(f"[买入信号] 百分位<{PE_LOW_THRESHOLD}%，建议定投！")
            trigger_alert = True
        
        if percentile > PE_HIGH_THRESHOLD:
            msg_list.append(f"[止盈信号] 百分位>{PE_HIGH_THRESHOLD}%，建议止盈！")
            trigger_alert = True
            
        if change_percent < DROP_THRESHOLD:
            msg_list.append(f"[大跌信号] 跌幅>{abs(DROP_THRESHOLD)*100}%，关注加仓！")
            trigger_alert = True
        
        if trigger_alert:
            send_message("\n".join(msg_list))
        else:
            print("无特殊信号，不发送通知")
            
    except Exception as e:
        send_message(f"[错误] 脚本运行出错：{str(e)}")
        print(f"错误详情：{e}")

if __name__ == "__main__":
    main()
