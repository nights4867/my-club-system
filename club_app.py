import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
import os
import json
import time
from datetime import datetime
import pytz 

# --- 1. 基本設定與 Google Sheets 連接 ---
CONFIG_FILE = r"club_config.json"
STUDENT_LIST_FILE = r"students.xlsx"

# 建立 Google Sheets 連線
conn = st.connection("gsheets", type=GSheetsConnection)

def get_taiwan_now():
    tw_tz = pytz.timezone('Asia/Taipei')
    return datetime.now(tw_tz).replace(tzinfo=None)

# 讀取雲端報名紀錄
def get_reg_data():
    try:
        # worksheet 名稱必須與 Google Sheets 下方的分頁名稱一致
        return conn.read(worksheet="registrations", ttl="0s")
    except Exception:
        # 如果讀取失敗，建立一個空表格
        return pd.DataFrame(columns=["班級", "座號", "姓名", "社團", "報名時間", "狀態"])

reg_df = get_reg_data()

# 載入本地設定檔 (時程與社團定義)
def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {
        "clubs": {"桌球社": {"limit": 10, "wait_limit": 5, "desc": "校園人氣社團"}},
        "start_time": "2026-02-09 08:00:00",
        "end_time": "2026-02-09 17:00:00",
        "admin_password": "admin"
    }

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

config_data = load_config()

# --- 2. 頁面配置與 CSS 美化 ---
st.set_page_config(page_title="雲端同步報名系統 V15", page_icon="☁️", layout="centered")

st.markdown("""
    <style>
    .stProgress > div > div > div > div { background-color: #4A7856; }
    h1 { color: #1E3A8A; text-align: center; }
    .verified-name { color: #166534; font-size: 1.8rem; font-weight: bold; margin: 10px 0; }
    </style>
    """, unsafe_allow_html=True)

# 初始化 Session State
if "current_page" not in st.session_state: st.session_state.current_page = "📝 學生報名"
if "id_verified" not in st.session_state: st.session_state.id_verified = False
if "last_student" not in st.session_state: st.session_state.last_student = ""

# --- 3. [優化：確認彈窗與寫入 Google Sheets] ---
@st.dialog("📝 最後確認報名資訊")
def confirm_submission(sel_class, sel_seat, name, club, status):
    st.write(f"### **{name}** 同學您好：")
    st.info(f"📍 班級座號：{sel_class} 班 {sel_seat} 號\n\n🎯 報名社團：{club}\n\n📝 錄取狀態：{status}")
    st.warning("⚠️ 按下確認後資料將永久儲存至雲端，且無法自行修改。")
    
    if st.button("✅ 確定報名，送出資料", use_container_width=True, type="primary"):
        with st.spinner('同步資料至雲端試算表中...'):
            # 準備新資料
            new_row = pd.DataFrame({
                "班級": [sel_class], "座號": [sel_seat], "姓名": [name],
                "社團": [club], "報名時間": [get_taiwan_now().strftime('%Y-%m-%d %H:%M:%S')],
                "狀態": [status]
            })
            
            # 重新抓取一次最新資料，避免多人同時報名衝突
            latest_reg = get_reg_data()
            updated_df = pd.concat([latest_reg, new_row], ignore_index=True)
            
            # 更新回 Google Sheets
            conn.update(worksheet="registrations", data=updated_df)
            
            st.success("🎉 報名成功！資料已安全存儲至雲端。")
            st.balloons()
            time.sleep(2)
            st.session_state.id_verified = False
            st.rerun()

# --- 4. 導覽列 ---
st.title("🏫 社團線上報名系統")
nav_col1, nav_col2, nav_col3 = st.columns(3)
if nav_col1.button("📝 學生報名", use_container_width=True): st.session_state.current_page = "📝 學生報名"; st.rerun()
if nav_col2.button("🔍 查詢報名", use_container_width=True): st.session_state.current_page = "🔍 查詢報名"; st.rerun()
if nav_col3.button("🛠️ 管理員後台", use_container_width=True): st.session_state.current_page = "🛠️ 管理員後台"; st.rerun()

st.divider()

# ----------------------------------------------------------------
# 【一、管理員後台】 - 雲端數據看板
# ----------------------------------------------------------------
if st.session_state.current_page == "🛠️ 管理員後台":
    if not st.session_state.get("is_admin", False):
        pwd = st.text_input("後台認證密碼", type="password")
        if st.button("驗證進入"):
            if pwd == config_data["admin_password"]: st.session_state.is_admin = True; st.rerun()
            else: st.error("密碼錯誤")
    else:
        if st.sidebar.button("🚪 登出"): st.session_state.is_admin = False; st.rerun()
        t1, t2, t3 = st.tabs(["📊 數據看版", "⚙️ 設定修改", "📁 名冊同步"])
        
        with t1:
            st.write("### 📈 雲端實時統計 (Google Sheets)")
            if not reg_df.empty:
                col_m1, col_m2 = st.columns(2)
                col_m1.metric("總報名人數", f"{len(reg_df)} 人")
                col_m2.metric("剩餘社團名額", f"{sum(c['limit'] for c in config_data['clubs'].values()) - len(reg_df[reg_df['狀態'] == '正取'])} 位")
                st.bar_chart(reg_df['社團'].value_counts())
                st.write("#### 📝 詳細名單")
                st.dataframe(reg_df, use_container_width=True)
            else:
                st.info("目前雲端試算表尚無資料。")

        with t2:
            st.write("### 🕒 時程管理")
            c_start = datetime.strptime(config_data["start_time"], "%Y-%m-%d %H:%M:%S")
            c_end = datetime.strptime(config_data["end_time"], "%Y-%m-%d %H:%M:%S")
            col_d1, col_d2 = st.columns(2)
            n_sd = col_d1.date_input("開始日期", c_start.date())
            n_st = col_d1.time_input("開始時間", c_start.time())
            n_ed = col_d2.date_input("結束日期", c_end.date())
            n_et = col_d2.time_input("結束時間", c_end.time())
            if st.button("💾 儲存報名時程"):
                config_data["start_time"] = f"{n_sd} {n_st.strftime('%H:%M:%S')}"
                config_data["end_time"] = f"{n_ed} {n_et.strftime('%H:%M:%S')}"
                save_config(config_data); st.success("時程已更新")
            
            st.divider()
            st.write("### 🏆 社團管理")
            for club_n, cfg in list(config_data["clubs"].items()):
                with st.container(border=True):
                    ec1, ec2, ec3, ec4 = st.columns([2, 1, 1, 1])
                    new_n = ec1.text_input("名稱", value=club_n, key=f"n_{club_n}")
                    new_l = ec2.number_input("正取", value=cfg['limit'], key=f"l_{club_n}")
                    new_w = ec3.number_input("備取", value=cfg['wait_limit'], key=f"w_{club_n}")
                    if ec4.button("🗑️", key=f"d_{club_n}"):
                        del config_data["clubs"][club_n]; save_config(config_data); st.rerun()
                    if new_l != cfg['limit'] or new_w != cfg['wait_limit'] or new_n != club_n:
                        config_data["clubs"][new_n] = {"limit": int(new_l), "wait_limit": int(new_w)}
                        if new_n != club_n: del config_data["clubs"][club_n]
                        save_config(config_data)

        with t3:
            uploaded = st.file_uploader("同步 Excel 名冊 (.xlsx)", type=["xlsx"])
            if uploaded:
                pd.read_excel(uploaded, dtype={"班級": str, "座號": str, "學號": str}).to_excel(STUDENT_LIST_FILE, index=False)
                st.success("本地名冊資料庫已更新")

# ----------------------------------------------------------------
# 【二、學生報名】 - 整合所有優化與身分驗證
# ----------------------------------------------------------------
elif st.session_state.current_page == "📝 學生報名":
    now = get_taiwan_now()
    start_dt = datetime.strptime(config_data["start_time"], "%Y-%m-%d %H:%M:%S")
    end_dt = datetime.strptime(config_data["end_time"], "%Y-%m-%d %H:%M:%S")

    if now < start_dt:
        diff = start_dt - now
        st.warning(f"⏳ 尚未開放報名。距離開始還有：{diff.days}天 {diff.seconds//3600}時")
        st.stop()
    elif now > end_dt:
        st.error("❌ 報名已截止")
        st.stop()
    
    if not os.path.exists(STUDENT_LIST_FILE):
        st.info("👋 管理員正在建置系統中。")
    else:
        std_df = pd.read_excel(STUDENT_LIST_FILE, dtype={"班級": str, "座號": str, "學號": str})
        std_df["座號"] = std_df["座號"].apply(lambda x: str(x).zfill(2))
        
        st.write("### 1️⃣ 選擇班級")
        classes = sorted(std_df["班級"].unique())
        sel_class = st.segmented_control("班級", options=classes, label_visibility="collapsed")
        
        if sel_class:
            st.write("### 2️⃣ 選擇座號")
            seats = sorted(std_df[std_df["班級"] == sel_class]["座號"].unique())
            sel_seat = st.segmented_control("座號", options=seats, label_visibility="collapsed")
            
            if sel_seat:
                # 偵測座號切換
                current_id_key = f"{sel_class}_{sel_seat}"
                if st.session_state.last_student != current_id_key:
                    st.session_state.id_verified = False
                    st.session_state.last_student = current_id_key

                student_row = std_df[(std_df["班級"] == sel_class) & (std_df["座號"] == sel_seat)].iloc[0]
                
                st.divider()
                st.write("### 🔒 3️⃣ 身分驗證")
                input_sid = st.text_input("🔑 請輸入學號確認身分：", type="password")
                
                if st.button("確定驗證身分", use_container_width=True):
                    if input_sid == str(student_row["學號"]):
                        st.session_state.id_verified = True
                        st.markdown(f'<p class="verified-name">✅ 驗證成功：{student_row["姓名"]} 同學</p>', unsafe_allow_html=True)
                    else:
                        st.session_state.id_verified = False
                        st.error("❌ 學號驗證錯誤，請重新輸入")

                if st.session_state.id_verified:
                    st.divider()
                    st.write("### 🎯 4️⃣ 選擇社團")
                    
                    # 顯示名額進度條
                    for club_n, cfg in config_data["clubs"].items():
                        c_reg = len(reg_df[reg_df["社團"] == club_n])
                        prog = min(c_reg / cfg["limit"], 1.0) if cfg["limit"] > 0 else 0
                        st.progress(prog, text=f"{club_n} (已收 {c_reg}/{cfg['limit']} 人)")
                    
                    # 選擇與彈窗確認
                    avail_options = []
                    for club_n, cfg in config_data["clubs"].items():
                        c_reg = len(reg_df[reg_df["社團"] == club_n])
                        if c_reg < cfg["limit"]: avail_options.append(f"{club_n} (正取)")
                        elif c_reg < (cfg["limit"] + cfg["wait_limit"]): avail_options.append(f"{club_n} (備取)")
                    
                    if avail_options:
                        choice = st.radio("可選清單", avail_options, horizontal=True)
                        if st.button("🚀 確認提交報名表", use_container_width=True, type="primary"):
                            # 檢查雲端有無重複報名
                            if not reg_df[(reg_df["班級"] == sel_class) & (reg_df["座號"] == sel_seat)].empty:
                                st.warning("⚠️ 您已在雲端資料庫中完成過報名。")
                            else:
                                real_c = choice.split(" (")[0]
                                status = "正取" if len(reg_df[reg_df["社團"] == real_c]) < config_data["clubs"][real_c]["limit"] else "備取"
                                confirm_submission(sel_class, sel_seat, student_row['姓名'], real_c, status)
                    else:
                        st.error("😭 所有社團名額已滿。")

# ----------------------------------------------------------------
# 【三、查詢報名】 - 從雲端讀取並排序
# ----------------------------------------------------------------
else:
    st.subheader("🔍 個人報名狀態查詢")
    name_input = st.text_input("輸入完整姓名：")
    if st.button("開始查詢", use_container_width=True):
        if name_input and not reg_df.empty:
            df = reg_df.copy().sort_values(by="報名時間")
            df['序號'] = df.groupby(['社團', '狀態']).cumcount() + 1
            df['狀態順位'] = df.apply(lambda x: f"{x['狀態']}{str(x['序號']).zfill(2)}", axis=1)
            result = df[df["姓名"] == name_input]
            if not result.empty:
                st.success(f"找到 {len(result)} 筆紀錄：")
                st.table(result[["班級", "座號", "姓名", "社團", "報名時間", "狀態順位"]])
            else: st.warning("查無資料，請確認姓名輸入正確。")