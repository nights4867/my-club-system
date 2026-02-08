import streamlit as st
import pandas as pd
import os
import json
import time
from datetime import datetime

# --- 檔案路徑設定 ---
CONFIG_FILE = r"club_config.json"
REG_FILE = r"club_registrations.csv"
STUDENT_LIST_FILE = r"students.xlsx"

# --- 核心功能：讀取與儲存設定 ---
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "clubs": {"程式設計社": {"limit": 3, "wait_limit": 2}},
        "start_time": "2026-01-01 08:00:00",
        "end_time": "2026-12-31 23:59:59",
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

# --- 側邊欄導覽 ---
st.sidebar.title("🏫 系統導覽")
mode = st.sidebar.selectbox("切換功能", ["📝 學生報名", "🔍 查詢報名", "🛠️ 管理員後台"])

# ----------------------------------------------------------------
# 【功能一：管理員後台】
# ----------------------------------------------------------------
if mode == "🛠️ 管理員後台":
    st.header("🛠️ 管理員後台系統")
    
    if "is_admin" not in st.session_state: st.session_state.is_admin = False

    if not st.session_state.is_admin:
        pwd = st.text_input("請輸入後台管理密碼", type="password")
        if st.button("登入"):
            if pwd == config_data["admin_password"]:
                st.session_state.is_admin = True
                st.rerun()
            else: st.error("密碼錯誤")
    else:
        if st.sidebar.button("登出後台"): 
            st.session_state.is_admin = False
            st.rerun()

        tab1, tab2, tab3 = st.tabs(["⚙️ 名額與時間", "📁 名冊與資料", "🔑 修改密碼"])
        
        with tab1:
            st.subheader("📅 報名時間設定")
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
                st.success("時間設定已更新！")

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
            
            # 列出目前社團並提供刪除按鈕
            for c, cfg in list(config_data["clubs"].items()):
                col_d1, col_d2 = st.columns([4, 1])
                col_d1.write(f"**{c}** (正式: {cfg['limit']} / 備取: {cfg['wait_limit']})")
                if col_d2.button("刪除", key=f"del_{c}"):
                    del config_data["clubs"][c]
                    save_config(config_data)
                    st.rerun()

        with tab2:
            st.subheader("📥 匯出報名清單")
            if not reg_df.empty:
                csv = reg_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
                st.download_button("下載 CSV 報名結果", csv, "result.csv", "text/csv")
            
            st.divider()
            st.subheader("📁 學生名冊上傳")
            uploaded_excel = st.file_uploader("上傳 Excel 名冊 (.xlsx)", type=["xlsx"])
            if uploaded_excel:
                try:
                    df_std = pd.read_excel(uploaded_excel, dtype={"班級": str, "座號": str})
                    df_std.to_excel(STUDENT_LIST_FILE, index=False)
                    st.success("名冊更新成功！")
                except Exception as e: st.error(f"錯誤：{e} (請檢查檔案是否關閉)")
            
            st.divider()
            if st.checkbox("我確定要清空所有報名資料"):
                if st.button("🔥 執行清空", type="primary"):
                    if os.path.exists(REG_FILE): os.remove(REG_FILE)
                    st.rerun()

        with tab3:
            st.subheader("🔐 修改密碼")
            new_p = st.text_input("設定新密碼", type="password")
            if st.button("確認修改"):
                config_data["admin_password"] = new_p
                save_config(config_data)
                st.success("密碼已更新！")

# ----------------------------------------------------------------
# 【功能二：學生報名】
# ----------------------------------------------------------------
elif mode == "📝 學生報名":
    st.header("🏫 社團線上報名")
    
    now = datetime.now()
    start_dt = datetime.strptime(config_data["start_time"], "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.strptime(config_data["end_time"], "%Y-%m-%d %H:%M:%S")
    
    if now < start_dt:
        diff = start_dt - now
        st.warning(f"⏳ 報名尚未開始")
        if diff.total_seconds() < 60:
            st.error(f"🔥 倒數 {int(diff.total_seconds())} 秒開放")
            time.sleep(1)
            st.rerun()
        else:
            st.metric("距離開放還有", f"{diff.days}天 {diff.seconds//3600}時 {(diff.seconds//60)%60}分")
            st.stop()
    elif now > end_dt:
        st.error("❌ 報名已結束")
        st.stop()

    if not os.path.exists(STUDENT_LIST_FILE):
        st.info("請管理員先進入後台確認名單與時間設定。")
    else:
        std_df = pd.read_excel(STUDENT_LIST_FILE, dtype={"班級": str, "座號": str})
        all_cls = sorted(std_df["班級"].unique())
        
        c1, c2, c3 = st.columns(3)
        sel_cls = c1.selectbox("班級", all_cls)
        df_cls = std_df[std_df["班級"] == sel_cls]
        sel_seat = c2.selectbox("座號", sorted(df_cls["座號"].unique()))
        sel_name = df_cls[df_cls["座號"] == sel_seat].iloc[0]["姓名"]
        c3.text_input("姓名", value=sel_name, disabled=True)
        
        # 顯示社團進度
        st.subheader("🎯 選擇社團")
        avail_clubs = []
        for c, cfg in config_data["clubs"].items():
            count = len(reg_df[reg_df["社團"] == c])
            total = cfg["limit"] + cfg["wait_limit"]
            if count < total:
                tag = "(正式)" if count < cfg["limit"] else "(備取)"
                avail_clubs.append(f"{c} {tag}")
        
        if avail_clubs:
            choice = st.selectbox("可選社團：", avail_clubs)
            real_c = choice.split(" (")[0]
            
            if st.button("確認報名", use_container_width=True):
                if not reg_df[(reg_df["班級"] == sel_cls) & (reg_df["座號"] == sel_seat)].empty:
                    st.warning("你已經報名過囉！")
                else:
                    st_count = len(reg_df[reg_df["社團"] == real_c])
                    status = "正式" if st_count < config_data["clubs"][real_c]["limit"] else "備取"
                    new_r = pd.DataFrame({"班級":[sel_cls], "座號":[sel_seat], "姓名":[sel_name], "社團":[real_c], "報名時間":[datetime.now().strftime('%Y-%m-%d %H:%M:%S')], "狀態":[status]})
                    new_r.to_csv(REG_FILE, mode='a', index=False, header=not os.path.exists(REG_FILE), encoding="utf-8-sig")
                    st.success(f"🎊 報名成功！狀態：{status}")
                    st.balloons()
                    st.rerun()
        else: st.error("目前所有社團皆已額滿。")

# ----------------------------------------------------------------
# 【功能三：查詢報名】
# ----------------------------------------------------------------
else:
    st.header("🔍 查詢報名狀態")
    q_name = st.text_input("輸入完整姓名查詢")
    if q_name:
        res = reg_df[reg_df["姓名"] == q_name]
        if not res.empty: st.table(res)
        else: st.warning("查無報名紀錄")