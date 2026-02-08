import streamlit as st
import pandas as pd
import os
import json
import time
from datetime import datetime
import pytz 

# --- 1. 基本設定與時區 ---
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
        "clubs": {"極地探險社": {"limit": 10, "wait_limit": 5}}, # 移除預設簡介
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
st.set_page_config(page_title="頂級社團報名系統 V14.4", page_icon="💎", layout="centered")

# 初始化狀態
if "current_page" not in st.session_state: st.session_state.current_page = "📝 學生報名"
if "id_verified" not in st.session_state: st.session_state.id_verified = False
if "last_student" not in st.session_state: st.session_state.last_student = ""

# --- 3. [優化：確認彈窗] ---
@st.dialog("📋 報名資訊最後確認")
def confirm_submission(sel_class, sel_seat, name, club, status):
    st.write(f"親愛的 **{name}** 同學：")
    st.markdown(f"""
    > **您的報名內容如下：**
    > - **所屬班級：** {sel_class} 班
    > - **學生座號：** {sel_seat} 號
    > - **欲報社團：** {club}
    > - **預計狀態：** {status}
    """)
    st.warning("請確認以上資訊無誤。點擊下方按鈕後將正式寫入資料庫，無法自行修改。")
    
    if st.button("✅ 我確認無誤，送出報名", use_container_width=True, type="primary"):
        new_row = pd.DataFrame({
            "班級": [sel_class], "座號": [sel_seat], "姓名": [name],
            "社團": [club], "報名時間": [get_taiwan_now().strftime('%Y-%m-%d %H:%M:%S')],
            "狀態": [status]
        })
        new_row.to_csv(REG_FILE, mode='a', index=False, header=not os.path.exists(REG_FILE), encoding="utf-8-sig")
        st.success("🎊 恭喜！報名已成功傳送。")
        st.balloons()
        time.sleep(2)
        st.session_state.id_verified = False
        st.rerun()

# --- [新增功能] 確認清除資料彈窗 ---
@st.dialog("🧨 危險操作確認")
def confirm_clear_data():
    st.error("⚠️ 您確定要清除所有報名資料嗎？此操作無法復原！")
    st.write("這將會刪除 `club_registrations.csv` 檔案中的所有紀錄，讓系統回到初始狀態。")
    
    if st.button("🧨 是的，我確定要刪除所有資料", type="primary"):
        if os.path.exists(REG_FILE):
            os.remove(REG_FILE)
            # 重新建立空檔案
            pd.DataFrame(columns=["班級", "座號", "姓名", "社團", "報名時間", "狀態"]).to_csv(REG_FILE, index=False, encoding="utf-8-sig")
            st.success("✅ 所有資料已清空！")
            time.sleep(1)
            st.rerun()
        else:
            st.info("目前本來就沒有資料喔。")

# --- 4. 頂部標題與導覽 ---
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>🏫 社團線上報名系統</h1>", unsafe_allow_html=True)
st.markdown("<p style='text-align: center; color: #6B7280;'>請依序完成身分驗證後，選擇您的心儀社團</p>", unsafe_allow_html=True)

nav_col1, nav_col2, nav_col3 = st.columns(3)
if nav_col1.button("📝 學生報名", use_container_width=True): st.session_state.current_page = "📝 學生報名"; st.rerun()
if nav_col2.button("🔍 查詢報名", use_container_width=True): st.session_state.current_page = "🔍 查詢報名"; st.rerun()
if nav_col3.button("🛠️ 管理員後台", use_container_width=True): st.session_state.current_page = "🛠️ 管理員後台"; st.rerun()

st.divider()

# ----------------------------------------------------------------
# 【一、管理員後台】 - [已移除簡介功能]
# ----------------------------------------------------------------
if st.session_state.current_page == "🛠️ 管理員後台":
    if not st.session_state.get("is_admin", False):
        pwd = st.text_input("後台認證密碼", type="password")
        if st.button("驗證並進入"):
            if pwd == config_data["admin_password"]: st.session_state.is_admin = True; st.rerun()
            else: st.error("密碼不正確")
    else:
        if st.button("🚪 安全登出"): st.session_state.is_admin = False; st.rerun()
        t1, t2, t3, t4 = st.tabs(["📊 實時看板", "⚙️ 參數設定", "📁 數據與備份", "🔑 權限管理"])
        
        with t1:
            st.write("### 📈 報名狀況即時統計")
            if not reg_df.empty:
                m1, m2, m3 = st.columns(3)
                m1.metric("總收件數", f"{len(reg_df)} 份")
                m2.metric("正取人數", f"{len(reg_df[reg_df['狀態'] == '正取'])} 人")
                m3.metric("候補人數", f"{len(reg_df[reg_df['狀態'] == '備取'])} 人")
                
                st.write("#### 📊 社團受歡迎程度排序")
                club_stats = reg_df['社團'].value_counts()
                st.bar_chart(club_stats)
            else:
                st.info("目前尚未有任何報名數據。")

        with t2:
            st.write("### 🕒 報名時程管理")
            c_start = datetime.strptime(config_data["start_time"], "%Y-%m-%d %H:%M:%S")
            c_end = datetime.strptime(config_data["end_time"], "%Y-%m-%d %H:%M:%S")
            cs1, cs2 = st.columns(2)
            n_sd = cs1.date_input("開始日期", c_start.date())
            n_st = cs1.time_input("開始時間", c_start.time())
            n_ed = cs2.date_input("結束日期", c_end.date())
            n_et = cs2.time_input("結束時間", c_end.time())
            if st.button("💾 更新時程並套用"):
                config_data["start_time"] = f"{n_sd} {n_st.strftime('%H:%M:%S')}"
                config_data["end_time"] = f"{n_ed} {n_et.strftime('%H:%M:%S')}"
                save_config(config_data); st.success("報名時段已更新！")
            
            st.divider()
            st.write("### 🏆 社團額度管理")
            for c_name, cfg in list(config_data["clubs"].items()):
                with st.container(border=True):
                    c1, c2, c3, c4 = st.columns([2, 1, 1, 1])
                    n_n = c1.text_input("名稱", value=c_name, key=f"n_{c_name}")
                    n_l = c2.number_input("正取", value=cfg['limit'], key=f"l_{c_name}")
                    n_w = c3.number_input("備取", value=cfg['wait_limit'], key=f"w_{c_name}")
                    if c4.button("🗑️", key=f"d_{c_name}"):
                        del config_data["clubs"][c_name]; save_config(config_data); st.rerun()
                    
                    # 邏輯修改：移除了 n_d (簡介) 的檢查與儲存
                    if n_l != cfg['limit'] or n_w != cfg['wait_limit'] or n_n != c_name:
                        config_data["clubs"][n_n] = {"limit": int(n_l), "wait_limit": int(n_w)}
                        if n_n != c_name: del config_data["clubs"][c_name]
                        save_config(config_data)
            if st.button("➕ 新增社團選項"):
                config_data["clubs"]["新社團"] = {"limit": 10, "wait_limit": 5}; save_config(config_data); st.rerun()

        with t3:
            st.write("### 📥 資料下載與備份")
            if not reg_df.empty:
                csv = reg_df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
                st.download_button("📥 匯出當前名單 (CSV)", csv, "registrations.csv", "text/csv")
            else:
                st.info("目前沒有資料可供下載。")

            st.divider()
            st.write("### 🔄 名冊更新")
            uploaded = st.file_uploader("同步學生名冊 (.xlsx)", type=["xlsx"])
            if uploaded:
                pd.read_excel(uploaded, dtype={"班級": str, "座號": str, "學號": str}).to_excel(STUDENT_LIST_FILE, index=False)
                st.success("名冊資料庫已完成同步！")
            
            # --- [保留功能] 一鍵清除資料按鈕 ---
            st.divider()
            st.write("### 🧨 危險區域")
            if st.button("🗑️ 清空所有報名資料 (慎點)", type="primary"):
                confirm_clear_data() # 呼叫彈窗

# ----------------------------------------------------------------
# 【二、學生報名】 - [保留：segmented_control]
# ----------------------------------------------------------------
elif st.session_state.current_page == "📝 學生報名":
    now = get_taiwan_now()
    start_dt = datetime.strptime(config_data["start_time"], "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.strptime(config_data["end_time"], "%Y-%m-%d %H:%M:%S")

    if now < start_dt:
        diff = start_dt - now
        st.warning(f"⏳ 系統尚未開放。距離開始報名還有：{diff.days}天 {diff.seconds//3600}時 {(diff.seconds//60)%60}分")
        st.stop()
    elif now > end_dt:
        st.error("❌ 報名時間已截止，系統已關閉。")
        st.stop()
    
    if not os.path.exists(STUDENT_LIST_FILE):
        st.info("👋 歡迎！請聯繫管理員上傳名冊。")
    else:
        std_df = pd.read_excel(STUDENT_LIST_FILE, dtype={"班級": str, "座號": str, "學號": str})
        std_df["座號"] = std_df["座號"].apply(lambda x: str(x).zfill(2))
        
        st.write("### 1️⃣ 選擇班級")
        classes = sorted(std_df["班級"].unique())
        # 保留原本的 segmented_control
        sel_class = st.segmented_control("班級選擇", options=classes, label_visibility="collapsed")
        
        if sel_class:
            st.write("### 2️⃣ 選擇座號")
            seats = sorted(std_df[std_df["班級"] == sel_class]["座號"].unique())
            # 保留原本的 segmented_control
            sel_seat = st.segmented_control("座號選擇", options=seats, label_visibility="collapsed")
            
            if sel_seat:
                # 偵測是否更換學生身分
                current_id_key = f"{sel_class}_{sel_seat}"
                if st.session_state.last_student != current_id_key:
                    st.session_state.id_verified = False
                    st.session_state.last_student = current_id_key

                student_row = std_df[(std_df["班級"] == sel_class) & (std_df["座號"] == sel_seat)].iloc[0]
                
                st.divider()
                st.write("### 🛡️ 3️⃣ 身分認證")
                input_sid = st.text_input("🔑 請輸入您的學號以解鎖報名：", type="password")
                
                if st.button("確定驗證身分", use_container_width=True):
                    if input_sid == str(student_row["學號"]):
                        st.session_state.id_verified = True
                        st.success(f"### ✅ 驗證成功：**{student_row['姓名']}** 同學")
                    else:
                        st.session_state.id_verified = False
                        st.error("❌ 學號驗證失敗，請重新輸入")

                # 通過驗證才顯示
                if st.session_state.id_verified:
                    st.divider()
                    st.write("### 🎯 4️⃣ 選擇社團")
                    
                    # 顯示每個社團的進度
                    for club_n, cfg in config_data["clubs"].items():
                        c_reg = len(reg_df[reg_df["社團"] == club_n])
                        c_lim = cfg["limit"]
                        
                        # 計算進度與顏色
                        prog = min(c_reg / c_lim, 1.0) if c_lim > 0 else 1.0
                        label = f"{club_n} (正取已收 {c_reg}/{c_lim})"
                        # 移除了簡介顯示 st.caption
                        st.progress(prog, text=label)
                    
                    # 製作可選清單
                    avail_options = []
                    for club_n, cfg in config_data["clubs"].items():
                        c_reg = len(reg_df[reg_df["社團"] == club_n])
                        if c_reg < cfg["limit"]: avail_options.append(f"{club_n} (正取)")
                        elif c_reg < (cfg["limit"] + cfg["wait_limit"]): avail_options.append(f"{club_n} (備取)")
                    
                    if avail_options:
                        choice = st.radio("可選社團：", avail_options, horizontal=True, label_visibility="collapsed")
                        if st.button("🚀 提交報名表", use_container_width=True, type="primary"):
                            if not reg_df[(reg_df["班級"] == sel_class) & (reg_df["座號"] == sel_seat)].empty:
                                st.warning("⚠️ 您已經有報名紀錄，請勿重複提交。")
                            else:
                                real_c = choice.split(" (")[0]
                                status = "正取" if len(reg_df[reg_df["社團"] == real_c]) < config_data["clubs"][real_c]["limit"] else "備取"
                                # [保留：確認彈窗]
                                confirm_submission(sel_class, sel_seat, student_row['姓名'], real_c, status)
                    else:
                        st.error("😭 很抱歉，所有名額已搶購一空。")

# ----------------------------------------------------------------
# 【三、查詢報名】 - [保留：動態流水號]
# ----------------------------------------------------------------
else:
    st.subheader("🔍 查詢個人報名結果")
    q_name = st.text_input("請輸入您的姓名：")
    if st.button("啟動查詢", use_container_width=True):
        if q_name and not reg_df.empty:
            df = reg_df.copy().sort_values(by="報名時間")
            # [優化：計算正取 01, 正取 02...]
            df['順位'] = df.groupby(['社團', '狀態']).cumcount() + 1
            df['最終狀態'] = df.apply(lambda x: f"{x['狀態']}{str(x['順位']).zfill(2)}", axis=1)
            
            res = df[df["姓名"] == q_name]
            if not res.empty:
                st.success(f"找到 {len(res)} 筆紀錄：")
                final_view = res[["班級", "座號", "姓名", "社團", "報名時間", "最終狀態"]]
                st.table(final_view.rename(columns={"最終狀態": "錄取狀態"}))
            else: st.warning("資料庫中查無此姓名。")