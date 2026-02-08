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

# --- 4. 初始化頁面狀態 ---
if "current_page" not in st.session_state:
    st.session_state.current_page = "📝 學生報名"

# ----------------------------------------------------------------
# 【主畫面標題與導覽按鈕】
# ----------------------------------------------------------------
st.set_page_config(page_title="社團管理系統", page_icon="🏫", layout="centered")

st.title("🏫 社團線上報名系統")

# 在標題下方建立三個導覽按鈕
nav_col1, nav_col2, nav_col3 = st.columns(3)

if nav_col1.button("📝 學生報名", use_container_width=True):
    st.session_state.current_page = "📝 學生報名"
if nav_col2.button("🔍 查詢報名", use_container_width=True):
    st.session_state.current_page = "🔍 查詢報名"
if nav_col3.button("🛠️ 管理員後台", use_container_width=True):
    st.session_state.current_page = "🛠️ 管理員後台"

st.divider() # 分隔線，下方顯示功能內容

# ----------------------------------------------------------------
# 【分頁邏輯顯示】
# ----------------------------------------------------------------

mode = st.session_state.current_page

# --- 功能一：管理員後台 ---
if mode == "🛠️ 管理員後台":
    st.subheader("🛠️ 管理員安全後台")
    if "is_admin" not in st.session_state: st.session_state.is_admin = False

    if not st.session_state.is_admin:
        pwd = st.text_input("請輸入管理密碼", type="password")
        if st.button("登入後台"):
            if pwd == config_data["admin_password"]:
                st.session_state.is_admin = True
                st.rerun()
            else: st.error("❌ 密碼錯誤")
    else:
        # 登入成功後的後台內容
        if st.button("🚪 登出管理員模式"): 
            st.session_state.is_admin = False
            st.rerun()

        tab1, tab2, tab3 = st.tabs(["⚙️ 名額與時間", "📁 名冊與資料", "🔑 修改密碼"])
        
        with tab1:
            st.write("### 📅 時間與名額設定")
            c_start = datetime.strptime(config_data["start_time"], "%Y-%m-%d %H:%M:%S")
            c_end = datetime.strptime(config_data["end_time"], "%Y-%m-%d %H:%M:%S")
            
            col_s1, col_s2 = st.columns(2)
            n_start_d = col_s1.date_input("開始日期", c_start.date())
            n_start_t = col_s1.time_input("開始時間", c_start.time())
            n_end_d = col_s2.date_input("結束日期", c_end.date())
            n_end_t = col_s2.time_input("結束時間", c_end.time())
            
            if st.button("儲存時間"):
                config_data["start_time"] = f"{n_start_d} {n_start_t.strftime('%H:%M:%S')}"
                config_data["end_time"] = f"{n_end_d} {n_end_t.strftime('%H:%M:%S')}"
                save_config(config_data)
                st.success("✅ 更新成功")

            st.write("---")
            st.write("### 🏆 社團名單")
            with st.expander("➕ 新增社團"):
                new_c = st.text_input("名稱")
                l_col, w_col = st.columns(2)
                new_l = l_col.number_input("正式", min_value=1, value=10)
                new_w = w_col.number_input("備取", min_value=0, value=5)
                if st.button("新增項目"):
                    config_data["clubs"][new_c] = {"limit": int(new_l), "wait_limit": int(new_w)}
                    save_config(config_data); st.rerun()
            
            for c, cfg in list(config_data["clubs"].items()):
                c_c1, c_c2 = st.columns([4, 1])
                c_c1.write(f"{c} (正{cfg['limit']} / 備{cfg['wait_limit']})")
                if c_c2.button("刪除", key=f"del_{c}"):
                    del config_data["clubs"][c]
                    save_config(config_data); st.rerun()

        with tab2:
            st.write("### 📥 資料操作")
            if not reg_df.empty:
                csv = reg_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
                st.download_button("📥 下載報名清單", csv, "result.csv", "text/csv")
            
            st.write("---")
            uploaded_excel = st.file_uploader("上傳學生名冊 (.xlsx)", type=["xlsx"])
            if uploaded_excel:
                try:
                    df_std = pd.read_excel(uploaded_excel, dtype={"班級": str, "座號": str})
                    df_std.to_excel(STUDENT_LIST_FILE, index=False)
                    st.success("✅ 名冊已上傳")
                except: st.error("上傳失敗")
            
            st.write("---")
            if st.checkbox("確定要重設所有報名？"):
                if st.button("🔥 一鍵清空資料", type="primary"):
                    if os.path.exists(REG_FILE): os.remove(REG_FILE)
                    st.rerun()

        with tab3:
            st.write("### 🔐 修改密碼")
            new_p = st.text_input("新密碼", type="password")
            if st.button("儲存新密碼"):
                config_data["admin_password"] = new_p
                save_config(config_data); st.success("已更新")

# --- 功能二：學生報名 (核心邏輯) ---
elif mode == "📝 學生報名":
    now = get_taiwan_now()
    start_dt = datetime.strptime(config_data["start_time"], "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.strptime(config_data["end_time"], "%Y-%m-%d %H:%M:%S")
    
    # 倒數邏輯
    if now < start_dt:
        diff = start_dt - now
        st.warning("⏳ 報名尚未開始")
        if diff.total_seconds() < 60:
            st.error(f"🚀 即將開始：{int(diff.total_seconds())} 秒")
            time.sleep(1); st.rerun()
        else:
            st.metric("距離開放還有", f"{diff.days}天 {diff.seconds//3600}時 {(diff.seconds//60)%60}分")
            st.stop()
    elif now > end_dt:
        st.error("❌ 報名已結束")
        st.stop()
    else:
        # 進行中倒數
        diff_end = end_dt - now
        total_sec = int(diff_end.total_seconds())
        if total_sec < 60:
            st.error(f"🚨 系統關閉倒數：{total_sec} 秒")
            time.sleep(1); st.rerun()
        else:
            st.info(f"🔓 報名開放中！距離結束還有：{diff_end.days}天 {diff_end.seconds//3600}時 {(diff_end.seconds//60)%60}分")

    # 表單區
    if not os.path.exists(STUDENT_LIST_FILE):
        st.info("👋 歡迎！請管理員先進入後台確認名冊。")
    else:
        std_df = pd.read_excel(STUDENT_LIST_FILE, dtype={"班級": str, "座號": str})
        all_cls = sorted(std_df["班級"].unique())
        f_c1, f_c2, f_c3 = st.columns(3)
        sel_cls = f_c1.selectbox("班級", all_cls)
        df_cls = std_df[std_df["班級"] == sel_cls]
        sel_seat = f_c2.selectbox("座號", sorted(df_cls["座號"].unique()))
        sel_name = df_cls[df_cls["座號"] == sel_seat].iloc[0]["姓名"]
        f_c3.text_input("姓名", value=sel_name, disabled=True)
        
        st.write("### 🎯 選擇社團")
        avail = []
        for c, cfg in config_data["clubs"].items():
            count = len(reg_df[reg_df["社團"] == c])
            if count < (cfg["limit"] + cfg["wait_limit"]):
                tag = "(正式)" if count < cfg["limit"] else "(備取)"
                avail.append(f"{c} {tag}")
        
        if avail:
            choice = st.selectbox("請選擇：", avail)
            real_c = choice.split(" (")[0]
            if st.button("確認報名", use_container_width=True):
                if not reg_df[(reg_df["班級"] == sel_cls) & (reg_df["座號"] == sel_seat)].empty:
                    st.warning("你已報名過！")
                else:
                    c_count = len(reg_df[reg_df["社團"] == real_c])
                    status = "正式" if c_count < config_data["clubs"][real_c]["limit"] else "備取"
                    new_r = pd.DataFrame({"班級":[sel_cls], "座號":[sel_seat], "姓名":[sel_name], "社團":[real_c], "報名時間":[get_taiwan_now().strftime('%Y-%m-%d %H:%M:%S')], "狀態":[status]})
                    new_r.to_csv(REG_FILE, mode='a', index=False, header=not os.path.exists(REG_FILE), encoding="utf-8-sig")
                    st.success(f"🎊 報名成功：{status}"); st.balloons(); time.sleep(2); st.rerun()
        else: st.error("社團已全數額滿")

# --- 功能三：查詢報名 ---
else:
    st.subheader("🔍 查詢報名狀態")
    q_name = st.text_input("輸入完整姓名：")
    if q_name:
        res = reg_df[reg_df["姓名"] == q_name]
        if not res.empty: st.table(res)
        else: st.warning("查無資料")