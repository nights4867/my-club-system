import streamlit as st
import pandas as pd
import os
import json
import time
from datetime import datetime
import pytz 

# --- 1. 基本設定 ---
CONFIG_FILE = r"club_config.json"
REG_FILE = r"club_registrations.csv"
STUDENT_LIST_FILE = r"students.xlsx"

def get_taiwan_now():
    tw_tz = pytz.timezone('Asia/Taipei')
    return datetime.now(tw_tz).replace(tzinfo=None)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "clubs": {"桌球社": {"limit": 10, "wait_limit": 5}},
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

# --- 2. 介面與狀態初始化 ---
st.set_page_config(page_title="社團報名系統 V12.1", page_icon="🏫", layout="centered")

# 初始化 Session State
if "current_page" not in st.session_state: st.session_state.current_page = "📝 學生報名"
if "id_verified" not in st.session_state: st.session_state.id_verified = False
if "last_student" not in st.session_state: st.session_state.last_student = ""

st.title("🏫 社團線上報名系統")

# 導覽按鈕
nav_col1, nav_col2, nav_col3 = st.columns(3)
if nav_col1.button("📝 學生報名", use_container_width=True): 
    st.session_state.current_page = "📝 學生報名"; st.rerun()
if nav_col2.button("🔍 查詢報名", use_container_width=True): 
    st.session_state.current_page = "🔍 查詢報名"; st.rerun()
if nav_col3.button("🛠️ 管理員後台", use_container_width=True): 
    st.session_state.current_page = "🛠️ 管理員後台"; st.rerun()

st.divider()

# ----------------------------------------------------------------
# 【一、管理員後台】
# ----------------------------------------------------------------
if st.session_state.current_page == "🛠️ 管理員後台":
    st.subheader("🛠️ 管理員後台")
    if "is_admin" not in st.session_state: st.session_state.is_admin = False

    if not st.session_state.is_admin:
        pwd = st.text_input("後台管理密碼", type="password")
        if st.button("驗證登入"):
            if pwd == config_data["admin_password"]:
                st.session_state.is_admin = True; st.rerun()
            else: st.error("密碼錯誤")
    else:
        if st.button("🚪 登出管理員模式"): st.session_state.is_admin = False; st.rerun()
        t1, t2, t3 = st.tabs(["⚙️ 參數修改", "📁 資料與名冊", "🔑 密碼更換"])
        
        with t1:
            st.write("### 🕒 報名時程 (台灣時間)")
            c_start = datetime.strptime(config_data["start_time"], "%Y-%m-%d %H:%M:%S")
            c_end = datetime.strptime(config_data["end_time"], "%Y-%m-%d %H:%M:%S")
            col1, col2 = st.columns(2)
            n_start_date = col1.date_input("開始日期", c_start.date())
            n_start_time = col1.time_input("開始時間", c_start.time())
            n_end_date = col2.date_input("結束日期", c_end.date())
            n_end_time = col2.time_input("結束時間", c_end.time())
            if st.button("💾 儲存時間"):
                config_data["start_time"] = f"{n_start_date} {n_start_time.strftime('%H:%M:%S')}"
                config_data["end_time"] = f"{n_end_date} {n_end_time.strftime('%H:%M:%S')}"
                save_config(config_data); st.success("時程已更新！")

            st.divider()
            st.write("### 🏆 社團名額管理")
            for club_name, cfg in list(config_data["clubs"].items()):
                with st.container(border=True):
                    ec1, ec2, ec3, ec4 = st.columns([2, 1, 1, 1])
                    new_n = ec1.text_input("社團名", value=club_name, key=f"n_{club_name}")
                    new_l = ec2.number_input("正取", value=cfg['limit'], key=f"l_{club_name}")
                    new_w = ec2.number_input("備取", value=cfg['wait_limit'], key=f"w_{club_name}")
                    if ec4.button("🗑️", key=f"d_{club_name}"):
                        del config_data["clubs"][club_name]; save_config(config_data); st.rerun()
                    if new_l != cfg['limit'] or new_w != cfg['wait_limit'] or new_n != club_name:
                        config_data["clubs"][new_n] = {"limit": int(new_l), "wait_limit": int(new_w)}
                        if new_n != club_name: del config_data["clubs"][club_name]
                        save_config(config_data)
            if st.button("➕ 新增社團"):
                config_data["clubs"]["新社團"] = {"limit": 10, "wait_limit": 5}; save_config(config_data); st.rerun()

        with t2:
            if not reg_df.empty:
                csv = reg_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
                st.download_button("💾 下載 CSV 報名清單", csv, "registrations.csv", "text/csv")
            st.divider()
            st.info("💡 提醒：Excel 必須包含「班級」、「座號」、「姓名」、「學號」欄位。")
            uploaded = st.file_uploader("上傳 Excel 名冊 (.xlsx)", type=["xlsx"])
            if uploaded:
                pd.read_excel(uploaded, dtype={"班級": str, "座號": str, "學號": str}).to_excel(STUDENT_LIST_FILE, index=False)
                st.success("名冊上傳成功！")

# ----------------------------------------------------------------
# 【二、學生報名】 - 整合學號驗證按鈕 + 名字放大
# ----------------------------------------------------------------
elif st.session_state.current_page == "📝 學生報名":
    now = get_taiwan_now()
    start_dt = datetime.strptime(config_data["start_time"], "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.strptime(config_data["end_time"], "%Y-%m-%d %H:%M:%S")

    if now < start_dt:
        diff = start_dt - now
        st.warning(f"⏳ 報名尚未開始。距離開放還有：{diff.days}天 {diff.seconds//3600}時 {(diff.seconds//60)%60}分")
        st.stop()
    elif now > end_dt:
        st.error("❌ 報名已截止")
        st.stop()
    
    if not os.path.exists(STUDENT_LIST_FILE):
        st.info("👋 請管理員先上傳名冊。")
    else:
        std_df = pd.read_excel(STUDENT_LIST_FILE, dtype={"班級": str, "座號": str, "學號": str})
        std_df["座號"] = std_df["座號"].apply(lambda x: str(x).zfill(2))
        
        st.write("### 1️⃣ 班級")
        classes = sorted(std_df["班級"].unique())
        sel_class = st.segmented_control("班級選擇", options=classes, label_visibility="collapsed")
        
        if sel_class:
            st.write("### 2️⃣ 座號")
            seats = sorted(std_df[std_df["班級"] == sel_class]["座號"].unique())
            sel_seat = st.segmented_control("座號選擇", options=seats, label_visibility="collapsed")
            
            if sel_seat:
                # 偵測是否更換了學生
                current_id_key = f"{sel_class}_{sel_seat}"
                if st.session_state.last_student != current_id_key:
                    st.session_state.id_verified = False
                    st.session_state.last_student = current_id_key

                student_row = std_df[(std_df["班級"] == sel_class) & (std_df["座號"] == sel_seat)].iloc[0]
                
                # 身分驗證區
                st.divider()
                st.write("### 🛡️ 3️⃣ 身分驗證")
                input_sid = st.text_input("🔑 請輸入學號確認身分：", type="password")
                
                # 驗證按鈕
                if st.button("確定驗證身分", use_container_width=True):
                    if input_sid == str(student_row["學號"]):
                        st.session_state.id_verified = True
                        # --- 修改處：使用 Markdown 放大並加粗名字 ---
                        st.success(f"### ✅ 驗證成功：**{student_row['姓名']}** 同學\n\n請在下方選擇社團")
                    else:
                        st.session_state.id_verified = False
                        st.error("❌ 學號不正確，請重新確認")

                # 驗證通過才顯示社團選擇
                if st.session_state.id_verified:
                    st.divider()
                    st.write(f"### 🎯 4️⃣ 選擇社團")
                    avail_options = []
                    for c, cfg in config_data["clubs"].items():
                        reg_count = len(reg_df[reg_df["社團"] == c])
                        limit = cfg["limit"]
                        wait_limit = cfg["wait_limit"]
                        if reg_count < limit:
                            avail_options.append(f"{c} (正取, 剩{limit - reg_count}人)")
                        elif reg_count < (limit + wait_limit):
                            avail_options.append(f"{c} (備取, 剩{(limit + wait_limit) - reg_count}人)")
                    
                    if avail_options:
                        choice = st.radio("社團選項", avail_options, horizontal=True, label_visibility="collapsed")
                        if st.button("🚀 確認提交報名", use_container_width=True, type="primary"):
                            if not reg_df[(reg_df["班級"] == sel_class) & (reg_df["座號"] == sel_seat)].empty:
                                st.warning("⚠️ 此座號已報名過。")
                            else:
                                real_club = choice.split(" (")[0]
                                status = "正取" if len(reg_df[reg_df["社團"] == real_club]) < config_data["clubs"][real_club]["limit"] else "備取"
                                new_row = pd.DataFrame({"班級": [sel_class], "座號": [sel_seat], "姓名": [student_row['姓名']], "社團": [real_club], "報名時間": [get_taiwan_now().strftime('%Y-%m-%d %H:%M:%S')], "狀態": [status]})
                                new_row.to_csv(REG_FILE, mode='a', index=False, header=not os.path.exists(REG_FILE), encoding="utf-8-sig")
                                st.success("🎊 報名成功！")
                                st.balloons(); time.sleep(2); st.session_state.id_verified = False; st.rerun()
                    else: st.error("😭 社團名額已全數額滿")

# ----------------------------------------------------------------
# 【三、查詢報名】
# ----------------------------------------------------------------
else:
    st.subheader("🔍 查詢報名結果")
    name_input = st.text_input("輸入完整姓名搜尋")
    if st.button("開始查詢", use_container_width=True):
        if name_input and not reg_df.empty:
            df = reg_df.copy().sort_values(by="報名時間")
            df['序號'] = df.groupby(['社團', '狀態']).cumcount() + 1
            df['狀態'] = df.apply(lambda x: f"{x['狀態']}{str(x['序號']).zfill(2)}", axis=1)
            result = df[df["姓名"] == name_input]
            if not result.empty:
                st.success(f"找到 {len(result)} 筆紀錄：")
                st.table(result[["班級", "座號", "姓名", "社團", "報名時間", "狀態"]])
            else: st.warning("查無資料")