# -*- coding: utf-8 -*-
import akshare as ak
import requests
import pandas as pd
import datetime
import os

# ================= 配置区域 =================
WEBHOOK_URL = os.getenv("DINGTALK_WEBHOOK")
INDEX_SYMBOL = "980017"  # 国证半导体芯片
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
    # 修改点：确保 content 里包含句号 .，否则钉钉会拦截
    # 我们在末尾强制加了一个句号
    data = {
        "msgtype": "text",
        "text": {
            "content": f"[监控] 时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}.\n\n{text}。"
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
        # 1. 获取当前行情 (这个接口比较稳定)
        df_quote = ak.stock_zh_index_spot(symbol=[INDEX_SYMBOL])
        change_percent = df_quote['涨跌幅'].iloc[0] / 100.0
        current_price = df_quote['最新价'].iloc[0]
        
        # 2. 尝试获取 PE 数据 (不稳定，放在 try 块里，防止报错中断)
        pe_msg = "PE 数据获取失败."
        percentile = 50.0 
        try:
            df_pe = ak.stock_index_value_hist(symbol=INDEX_SYMBOL, period="pe")
            current_pe = df_pe['估值'].iloc[-1]
            history_pe = df_pe['估值'].dropna()
            percentile = (history_pe < current_pe).sum() / len(history_pe) * 100
            pe_msg = f"当前 PE-TTM: {current_pe:.2f}, 百分位：{percentile:.2f}%."
        except Exception as pe_err:
            pe_msg = f"PE 数据暂不可用."
            print(f"PE 接口报错：{pe_err}")
        
        # 3. 构建消息
        msg_list = []
        msg_list.append(f"指数：国证半导体芯片 ({INDEX_SYMBOL}).")
        msg_list.append(f"当前点位：{current_price}.")
        msg_list.append(f"今日涨跌：{change_percent*100:.2f}%.")
        msg_list.append(pe_msg)
        msg_list.append("-" * 30)
        
        trigger_alert = False
        
        # 只基于涨跌幅触发
        if change_percent < DROP_THRESHOLD:
            msg_list.append(f"[买入信号] 跌幅>{abs(DROP_THRESHOLD)*100}%，关注加仓！.")
            trigger_alert = True
        
        # 如果 PE 获取成功，再判断 PE 阈值
        if "百分位" in pe_msg:
            if percentile < PE_LOW_THRESHOLD:
                msg_list.append(f"[买入信号] 百分位<{PE_LOW_THRESHOLD}%，建议定投！.")
                trigger_alert = True
            if percentile > PE_HIGH_THRESHOLD:
                msg_list.append(f"[止盈信号] 百分位>{PE_HIGH_THRESHOLD}%，建议止盈！.")
                trigger_alert = True
        
        if trigger_alert:
            send_message("\n".join(msg_list))
        else:
            # 即使无信号，也发送一条日志消息方便您测试确认通道畅通
            # 如果您不想每天收到无信号消息，可以把下面这行注释掉
            send_message("今日无特殊信号，监控正常运行.") 
            
    except Exception as e:
        # 确保报错信息也包含句号
        send_message(f"[监控] 脚本运行出错：{str(e)}.")
        print(f"错误详情：{e}")

if __name__ == "__main__":
    main()
