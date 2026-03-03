import akshare as ak
import requests
import pandas as pd
import datetime
import os

# ================= 配置区域 =================
# 替换为您钉钉机器人的 Webhook 地址
WEBHOOK_URL = os.getenv("https://oapi.dingtalk.com/robot/send?access_token=e93016e501629177abdb46f4c076877450c63a453449867ca634f3cd42d39ec4") 
# 监控的指数代码 (国证半导体芯片)
INDEX_SYMBOL = "sz980017" 
# 阈值设置
PE_LOW_THRESHOLD = 20    # 百分位低于 20% 提醒买入
PE_HIGH_THRESHOLD = 80   # 百分位高于 80% 提醒止盈
DROP_THRESHOLD = -0.03   # 单日跌幅超过 3% 提醒
# ===========================================

def send_message(text):
    """发送消息到钉钉"""
    if not WEBHOOK_URL:
        print("未配置 Webhook 地址")
        return
        
    headers = {'Content-Type': 'application/json'}
    # 注意：内容必须包含您在钉钉机器人设置的关键词，例如 "监控"
    data = {
        "msgtype": "text",
        "text": {
            "content": f"🚨 半导体监控提醒\n时间：{datetime.datetime.now().strftime('%Y-%m-%d %H:%M')}\n\n{text}"
        }
    }
    try:
        requests.post(WEBHOOK_URL, json=data, headers=headers, timeout=10)
        print("消息发送成功")
    except Exception as e:
        print(f"消息发送失败：{e}")

def get_index_data():
    """获取指数估值和行情数据"""
    try:
        # 1. 获取历史 PE 数据 (用于计算百分位)
        # 注意：AkShare 接口可能会更新，如果报错请查阅最新文档
        df_pe = ak.stock_index_value_hist(symbol=INDEX_SYMBOL, period="pe")
        
        # 2. 获取当前行情 (涨跌幅)
        df_quote = ak.stock_zh_index_spot(symbol=[INDEX_SYMBOL])
        
        return df_pe, df_quote
    except Exception as e:
        return None, None

def calculate_percentile(current_pe, history_pe):
    """计算 PE 百分位"""
    # 取最近 5 年数据 (约 1200 个交易日)
    recent_data = history_pe.dropna()
    if len(recent_data) == 0:
        return 50.0 # 默认值
    
    # 计算当前 PE 在历史数据中的位置
    percentile = (recent_data < current_pe).sum() / len(recent_data) * 100
    return percentile

def main():
    print("开始运行监控脚本...")
    df_pe, df_quote = get_index_data()
    
    if df_pe is None or df_quote is None:
        send_message("❌ 监控脚本出错：无法获取数据，请检查接口。")
        return

    # 获取当前 PE (取最新一行)
    current_pe = df_pe['估值'].iloc[-1]
    
    # 计算百分位
    pe_percentile = calculate_percentile(current_pe, df_pe['估值'])
    
    # 获取涨跌幅 (注意不同接口字段名可能不同，需调试)
    # 这里假设 df_quote 中有 '涨跌幅' 列，如果没有需调整
    try:
        change_percent = df_quote['涨跌幅'].iloc[0] / 100.0 # 转换为小数
    except:
        change_percent = 0.0

    msg_list = []
    msg_list.append(f📊 指数：国证半导体芯片 ({INDEX_SYMBOL})")
    msg_list.append(f📈 当前 PE-TTM: {current_pe:.2f}")
    msg_list.append(f📉 PE 百分位：{pe_percentile:.2f}% (近 5 年)")
    msg_list.append(f🔻 今日涨跌：{change_percent*100:.2f}%")
    msg_list.append("-" * 30)

    trigger_alert = False

    # 逻辑判断
    if pe_percentile < PE_LOW_THRESHOLD:
        msg_list.append(f"✅ 触发低估信号：百分位<{PE_LOW_THRESHOLD}%，建议加大定投！")
        trigger_alert = True
    
    if pe_percentile > PE_HIGH_THRESHOLD:
        msg_list.append(f"⚠️ 触发高估信号：百分位>{PE_HIGH_THRESHOLD}%，建议止盈！")
        trigger_alert = True
        
    if change_percent < DROP_THRESHOLD:
        msg_list.append(f"📉 触发大跌信号：跌幅>{abs(DROP_THRESHOLD)*100}%，可能是加仓机会！")
        trigger_alert = True

    # 发送消息
    if trigger_alert:
        send_message("\n".join(msg_list))
    else:
        print("今日无特殊信号，不发送通知。")

if __name__ == "__main__":
    main()
