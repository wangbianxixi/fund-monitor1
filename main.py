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

def main():
    print("开始运行监控脚本...")
    
    # 初始化消息列表
    msg_list = []
    msg_list.append(f"指数：国证半导体芯片 ({INDEX_SYMBOL}).")
    
    try:
        # 1. 获取当前行情 (核心功能，必须成功)
        df_quote = ak.stock_zh_index_spot(symbol=[INDEX_SYMBOL])
        change_percent = df_quote['涨跌幅'].iloc[0] / 100.0
        current_price = df_quote['最新价'].iloc[0]
        
        msg_list.append(f"当前点位：{current_price}.")
        msg_list.append(f"今日涨跌：{change_percent*100:.2f}%.")
        
        # 2. 获取 PE 数据 (辅助功能，失败不影响脚本运行)
        pe_status = "PE 数据暂不可用."
        percentile = 50.0
        try:
            # 使用东财接口 (更稳定)
            df_pe = ak.stock_index_value_hist_em(symbol=INDEX_SYMBOL, period="pe")
            if not df_pe.empty:
                current_pe = df_pe['估值'].iloc[-1]
                history_pe = df_pe['估值'].dropna()
                if len(history_pe) > 0:
                    percentile = (history_pe < current_pe).sum() / len(history_pe) * 100
                    pe_status = f"PE-TTM: {current_pe:.2f}, 百分位：{percentile:.2f}%."
        except Exception as pe_err:
            print(f"PE 接口获取失败：{pe_err}")
            pe_status = "PE 数据维护中."
            
        msg_list.append(pe_status)
        msg_list.append("-" * 30)
        
        # 3. 判断信号
        trigger_alert = False
        
        # 涨跌幅信号
        if change_percent < DROP_THRESHOLD:
            msg_list.append(f"[买入信号] 跌幅>{abs(DROP_THRESHOLD)*100}%，关注加仓！.")
            trigger_alert = True
        
        # PE 信号 (仅在 PE 数据有效时判断)
        if "百分位" in pe_status:
            if percentile < PE_LOW_THRESHOLD:
                msg_list.append(f"[买入信号] 百分位<{PE_LOW_THRESHOLD}%，建议定投！.")
                trigger_alert = True
            if percentile > PE_HIGH_THRESHOLD:
                msg_list.append(f"[止盈信号] 百分位>{PE_HIGH_THRESHOLD}%，建议止盈！.")
                trigger_alert = True
        
        # 4. 发送消息
        if trigger_alert:
            send_message("\n".join(msg_list))
        else:
            # 即使无信号也发送，方便您确认脚本每天正常运行
            msg_list.append("今日无特殊信号，监控正常运行.")
            send_message("\n".join(msg_list))
            
    except Exception as e:
        # 万一核心行情获取失败，发送报错消息
        send_message(f"[监控] 核心行情获取出错：{str(e)}.")
        print(f"错误详情：{e}")

if __name__ == "__main__":
    main()
