import streamlit as st
import pandas as pd
import os
import json
import time
from datetime import datetime
import pytz 

# --- 1. 檔案路徑與基本設定 ---
CONFIG_FILE = r"club_config.json"
REG_FILE = r"club_registrations.csv"
STUDENT_LIST_FILE = r"students.xlsx"

# --- 2. 核心：強制台灣時間函式 ---
def get_taiwan_now():
    """取得目前的台灣時間 (台北時區)"""
    tw_tz = pytz.timezone('Asia/Taipei')
    return datetime.now(tw_tz).replace(tzinfo=None)

# --- 3. 核心：設定檔讀寫 ---
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = json.load(f)
            if "admin_password" not in config: config["admin_password"] = "admin"
            return config
    return {
        "clubs": {"程式設計社": {"limit": 3, "wait_limit": 2}},
        "start_time": "2026-02-09 08:00:00",
        "end_time": "2026-02-09 17:00:00",
        "admin_password": "admin"
    }

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

config_data = load_config()

# 讀取報名紀錄
if os.path.exists(REG_FILE):
    reg_df = pd.read_csv(REG_FILE, dtype={"班級": str, "座號": str})
else:
    reg_df = pd.DataFrame(columns=["班級", "座號", "姓名", "社團", "報名時間", "狀態"])

# --- 4. 側邊欄導覽 ---
st.sidebar.title("🏫 社團管理系統")
mode = st.sidebar.selectbox("切換功能", ["📝 學生報名", "🔍 查詢報名", "🛠️ 管理員後台"])

# ----------------------------------------------------------------
# 【功能一：管理員後台】
# ----------------------------------------------------------------
if mode == "🛠️ 管理員後台":
    st.header("🛠️ 管理員安全後台")
    if "is_admin" not in st.session_state: st.session_state.is_admin = False

    if not st.session_state.is_admin:
        pwd = st.text_input("請輸入管理密碼", type="password")
        if st.button("登入"):
            if pwd == config_data["admin_password"]:
                st.session_state.is_admin = True
                st.rerun()
            else: st.error("❌ 密碼錯誤")
    else:
        if st.sidebar.button("登出後台"): 
            st.session_state.is_admin = False
            st.rerun()

        tab1, tab2, tab3 = st.tabs(["⚙️ 名額與時間", "📁 名冊與資料", "🔑 修改密碼"])
        
        with tab1:
            st.subheader("📅 報名時間設定 (台灣時間)")
            c_start = datetime.strptime(config_data["start_time"], "%Y-%m-%d %H:%M:%S")
            c_end = datetime.strptime(config_data["end_time"], "%Y-%m-%d %H:%M:%S")
            
            col_s1, col_s2 = st.columns(2)
            n_start_d = col_s1.date_input("開始日期", c_start.date())
            n_start_t = col_s1.time_input("開始時間", c_start.time())
            n_end_d = col_s2.date_input("結束日期", c_end.date())
            n_end_t = col_s2.time_input("結束時間", c_end.time())
            
            if st.button("儲存時間設定"):
                config_data["start_time"] = f"{n_start_d} {n_start_t.strftime('%H:%M:%S')}"
                config_data["end_time"] = f"{n_end_d} {n_end_t.strftime('%H:%M:%S')}"
                save_config(config_data)
                st.success("✅ 時間設定已更新！")

            st.divider()
            st.subheader("🏆 社團名額管理")
            with st.expander("➕ 新增/修改社團"):
                new_c = st.text_input("社團名稱")
                col_c1, col_c2 = st.columns(2)
                new_l = col_c1.number_input("正式名額", min_value=1, value=10)
                new_w = col_c2.number_input("備取名額", min_value=0, value=5)
                if st.button("確認儲存社團"):
                    config_data["clubs"][new_c] = {"limit": int(new_l), "wait_limit": int(new_w)}
                    save_config(config_data)
                    st.rerun()
            
            for c, cfg in list(config_data["clubs"].items()):
                col_d1, col_d2 = st.columns([4, 1])
                col_d1.write(f"**{c}** (正式: {cfg['limit']} / 備取: {cfg['wait_limit']})")
                if col_d2.button("刪除", key=f"del_{c}"):
                    del config_data["clubs"][c]
                    save_config(config_data)
                    st.rerun()

        with tab2:
            st.subheader("📥 資料匯出")
            if not reg_df.empty:
                csv = reg_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
                st.download_button("📥 下載目前報名清單 (CSV)", csv, f"報名結果_{get_taiwan_now().strftime('%m%d_%H%M')}.csv", "text/csv")
            
            st.divider()
            st.subheader("📁 學生名冊上傳")
            uploaded_excel = st.file_uploader("選擇名冊 Excel (.xlsx)", type=["xlsx"])
            if uploaded_excel:
                try:
                    df_std = pd.read_excel(uploaded_excel, dtype={"班級": str, "座號": str})
                    df_std.to_excel(STUDENT_LIST_FILE, index=False)
                    st.success("✅ 名冊上傳成功！")
                except Exception as e: st.error(f"❌ 錯誤：{e}")
            
            st.divider()
            st.subheader("⚠️ 危險區域")
            if st.checkbox("我確定要清空所有報名資料"):
                if st.button("🔥 執行一鍵重設", type="primary"):
                    if os.path.exists(REG_FILE): os.remove(REG_FILE)
                    st.rerun()

        with tab3:
            st.subheader("🔑 修改管理密碼")
            new_p = st.text_input("設定新密碼", type="password")
            if st.button("確認修改密碼"):
                config_data["admin_password"] = new_p
                save_config(config_data)
                st.success("✅ 密碼已更新！")

# ----------------------------------------------------------------
# 【功能二：學生報名】 (含雙向倒數與台灣時間)
# ----------------------------------------------------------------
elif mode == "📝 學生報名":
    st.header("🏫 社團線上報名")
    
    now = get_taiwan_now()
    start_dt = datetime.strptime(config_data["start_time"], "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.strptime(config_data["end_time"], "%Y-%m-%d %H:%M:%S")
    
    # 情況 A：報名尚未開始
    if now < start_dt:
        diff = start_dt - now
        st.warning("⏳ 報名尚未開始")
        if diff.total_seconds() < 60:
            st.error(f"🔥 即將開放！倒數 {int(diff.total_seconds())} 秒")
            time.sleep(1); st.rerun()
        else:
            st.metric("距離開放還有", f"{diff.days}天 {diff.seconds//3600}時 {(diff.seconds//60)%60}分")
            st.info(f"開放時間：{config_data['start_time']}")
            st.stop()
            
    # 情況 B：報名已結束
    elif now > end_dt:
        st.error(f"❌ 報名已結束 (截止時間：{config_data['end_time']})")
        st.stop()
        
    # 情況 C：開放報名中
    else:
        diff_end = end_dt - now
        total_sec_end = int(diff_end.total_seconds())
        
        # 顯示結束倒數
        if total_sec_end > 3600: # 1小時以上
            st.info(f"🔓 報名開放中！距離結束還有：{diff_end.days}天 {diff_end.seconds//3600}時 {(diff_end.seconds//60)%60}分")
        elif 60 < total_sec_end <= 3600: # 1小時內
            st.warning(f"⚠️ 把握時間！系統將在 {total_sec_end // 60} 分鐘後關閉")
        else: # 最後一分鐘
            st.error(f"🚨 系統關閉倒數：{total_sec_end} 秒")
            time.sleep(1); st.rerun()

    # --- 報名表單區 ---
    if not os.path.exists(STUDENT_LIST_FILE):
        st.info("👋 你好！請管理員先進入後台確認名單與時間設定。")
    else:
        std_df = pd.read_excel(STUDENT_LIST_FILE, dtype={"班級": str, "座號": str})
        all_cls = sorted(std_df["班級"].unique())
        
        col_f1, col_f2, col_f3 = st.columns(3)
        sel_cls = col_f1.selectbox("選擇班級", all_cls)
        df_cls = std_df[std_df["班級"] == sel_cls]
        sel_seat = col_f2.selectbox("選擇座號", sorted(df_cls["座號"].unique()))
        sel_name = df_cls[df_cls["座號"] == sel_seat].iloc[0]["姓名"]
        col_f3.text_input("姓名", value=sel_name, disabled=True)
        
        st.subheader("🎯 選擇社團")
        avail_clubs = []
        for c, cfg in config_data["clubs"].items():
            count = len(reg_df[reg_df["社團"] == c])
            if count < (cfg["limit"] + cfg["wait_limit"]):
                tag = "(正式)" if count < cfg["limit"] else "(備取)"
                avail_clubs.append(f"{c} {tag}")
        
        if avail_clubs:
            choice = st.selectbox("請選擇您想加入的社團：", avail_clubs)
            real_club = choice.split(" (")[0]
            
            if st.button("確認提交報名", use_container_width=True):
                # 再次檢查重複報名
                if not reg_df[(reg_df["班級"] == sel_cls) & (reg_df["座號"] == sel_seat)].empty:
                    st.warning("⚠️ 你已經完成過報名囉！")
                else:
                    current_count = len(reg_df[reg_df["社團"] == real_club])
                    status = "正式" if current_count < config_data["clubs"][real_club]["limit"] else "備取"
                    
                    new_r = pd.DataFrame({
                        "班級":[sel_cls], "座號":[sel_seat], "姓名":[sel_name], 
                        "社團":[real_club], "報名時間":[get_taiwan_now().strftime('%Y-%m-%d %H:%M:%S')], 
                        "狀態":[status]
                    })
                    new_r.to_csv(REG_FILE, mode='a', index=False, header=not os.path.exists(REG_FILE), encoding="utf-8-sig")
                    st.success(f"🎊 報名成功！您的狀態是：【{status}】")
                    st.balloons()
                    time.sleep(2); st.rerun()
        else:
            st.error("😭 很抱歉，所有社團皆已額滿。")

# ----------------------------------------------------------------
# 【功能三：查詢報名】
# ----------------------------------------------------------------
else:
    st.header("🔍 查詢報名狀態")
    q_name = st.text_input("請輸入您的完整姓名：")
    if q_name:
        res = reg_df[reg_df["姓名"] == q_name]
        if not res.empty: 
            st.success(f"找到囉！以下是您的報名資料：")
            st.table(res)
        else:
            st.warning("查無紀錄，請確認姓名輸入是否完全正確。")