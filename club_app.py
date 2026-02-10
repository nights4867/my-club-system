import streamlit as st
import sys
import os
import subprocess
import time
import io
import json
import re
import pandas as pd
from datetime import datetime
import pytz 

# ==========================================
# 0. 智慧啟動器
# ==========================================
if __name__ == '__main__':
    try:
        from streamlit.runtime import exists
        if not exists():
            file_path = os.path.abspath(__file__)
            subprocess.run([sys.executable, "-m", "streamlit", "run", file_path, "--server.runOnSave", "true"])
            sys.exit()
    except ImportError:
        pass

# ==========================================
# 檢查必要套件
# ==========================================
try:
    from docx import Document
    from PIL import Image, ImageDraw, ImageFont
except ImportError:
    st.error("⚠️ 缺少必要套件！請在終端機輸入： pip install python-docx Pillow")
    st.stop()

# ==========================================
# 1. 系統路徑與設定
# ==========================================
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "club_config.json")
REG_FILE = os.path.join(BASE_DIR, "club_registrations.csv")
STUDENT_LIST_FILE = os.path.join(BASE_DIR, "students.xlsx")
IMAGES_DIR = os.path.join(BASE_DIR, "club_images")

if not os.path.exists(IMAGES_DIR):
    os.makedirs(IMAGES_DIR)

# ------------------------------------------
# [核心 1] 社團名稱轉圖片
# ------------------------------------------
def generate_text_image(text):
    width, height = 400, 45 
    background_color = (255, 255, 255) 
    text_color = (30, 58, 138) 
    
    img = Image.new('RGB', (width, height), color=background_color)
    draw = ImageDraw.Draw(img)
    
    font_path = "C:\\Windows\\Fonts\\msjh.ttc" 
    try:
        if os.path.exists(font_path):
            font = ImageFont.truetype(font_path, 24) 
        else:
            font = ImageFont.load_default()
    except:
        font = ImageFont.load_default()
    
    bbox = draw.textbbox((0, 0), text, font=font)
    text_h = bbox[3] - bbox[1]
    draw.text((5, (height - text_h) / 2 - 3), text, fill=text_color, font=font)
    
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

# ------------------------------------------
# [核心 2] 步驟標題轉圖片
# ------------------------------------------
def generate_step_image(num, text):
    width, height = 350, 40
    bg_color = (255, 255, 255)
    box_color = (0, 120, 212) 
    text_color = (50, 50, 50)
    
    img = Image.new('RGB', (width, height), color=bg_color)
    draw = ImageDraw.Draw(img)
    
    font_path = "C:\\Windows\\Fonts\\msjhbd.ttc"
    if not os.path.exists(font_path):
        font_path = "C:\\Windows\\Fonts\\msjh.ttc"
        
    try:
        font_num = ImageFont.truetype(font_path, 22) 
        font_text = ImageFont.truetype(font_path, 24) 
    except:
        font_num = ImageFont.load_default()
        font_text = ImageFont.load_default()

    box_size = 32
    box_x, box_y = 0, (height - box_size) // 2
    draw.rectangle([box_x, box_y, box_x + box_size, box_y + box_size], fill=box_color)
    
    bbox_num = draw.textbbox((0, 0), num, font=font_num)
    nw = bbox_num[2] - bbox_num[0]
    nh = bbox_num[3] - bbox_num[1]
    draw.text((box_x + (box_size - nw) / 2, box_y + (box_size - nh) / 2 - 4), num, fill=(255, 255, 255), font=font_num)
    
    text_x = box_x + box_size + 12
    bbox_text = draw.textbbox((0, 0), text, font=font_text)
    th = bbox_text[3] - bbox_text[1]
    draw.text((text_x, (height - th) / 2 - 5), text, fill=text_color, font=font_text)

    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

# ------------------------------------------

def get_taiwan_now():
    tw_tz = pytz.timezone('Asia/Taipei')
    return datetime.now(tw_tz).replace(tzinfo=None)

def load_config():
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for c in data.get("clubs", {}):
                if "category" not in data["clubs"][c]:
                    data["clubs"][c]["category"] = "綜合"
            return data
    return {
        "clubs": {"極地探險社": {"limit": 30, "category": "體育"}}, 
        "start_time": "2026-02-09 08:00:00",
        "end_time": "2026-02-09 17:00:00",
        "admin_password": "0000"
    }

def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

config_data = load_config()

def load_registrations():
    if os.path.exists(REG_FILE):
        return pd.read_csv(REG_FILE, dtype={"班級": str, "座號": str})
    else:
        return pd.DataFrame(columns=["班級", "座號", "姓名", "社團", "報名時間", "狀態"])

reg_df = load_registrations()

# ==========================================
# 2. 介面設定
# ==========================================
try:
    st.set_page_config(page_title="頂級社團報名系統 V18.14", page_icon="💎", layout="centered")
except:
    pass

if "current_page" not in st.session_state: st.session_state.current_page = "📝 學生報名"
if "id_verified" not in st.session_state: st.session_state.id_verified = False
if "last_student" not in st.session_state: st.session_state.last_student = ""

# ==========================================
# 3. 彈窗與邏輯
# ==========================================

@st.dialog("📋 報名資訊最後確認")
def confirm_submission(sel_class, sel_seat, name, club):
    st.write(f"親愛的 **{name}** 同學：")
    img_data = generate_text_image(club)
    st.image(img_data, use_container_width=True)
    st.info("系統將在您按下按鈕的瞬間，再次確認剩餘名額。")
    
    if st.button("✅ 我確認無誤，送出報名", use_container_width=True, type="primary"):
        current_df = load_registrations()
        if not current_df[(current_df["班級"] == sel_class) & (current_df["座號"] == sel_seat)].empty:
            st.error("⚠️ 寫入失敗：系統發現您剛剛已經完成報名了！")
            time.sleep(2); st.rerun(); return

        if club not in config_data["clubs"]:
            st.error("❌ 該社團設定已被移除。"); return
        
        limit = config_data["clubs"][club]["limit"]
        current_count = len(current_df[current_df["社團"] == club])
        
        if current_count >= limit:
            st.error(f"😭 來晚了一步！該社團剛剛瞬間額滿了。"); return 
        
        new_row = pd.DataFrame({
            "班級": [sel_class], "座號": [sel_seat], "姓名": [name],
            "社團": [club], "報名時間": [get_taiwan_now().strftime('%Y-%m-%d %H:%M:%S')],
            "狀態": ["正取"]
        })
        new_row.to_csv(REG_FILE, mode='a', index=False, header=not os.path.exists(REG_FILE), encoding="utf-8-sig")
        st.success(f"🎊 恭喜！您已成功報名！")
        st.balloons(); time.sleep(2); st.session_state.id_verified = False; st.rerun()

@st.dialog("🧨 危險操作確認")
def confirm_clear_data():
    st.error("⚠️ 您確定要清除所有報名資料嗎？")
    if st.button("🧨 確定刪除", type="primary"):
        if os.path.exists(REG_FILE):
            os.remove(REG_FILE)
            pd.DataFrame(columns=["班級", "座號", "姓名", "社團", "報名時間", "狀態"]).to_csv(REG_FILE, index=False, encoding="utf-8-sig")
            st.success("✅ 資料已清空！"); time.sleep(1); st.rerun()

@st.dialog("🧨 清空社團清單確認")
def confirm_clear_clubs():
    st.warning("⚠️ 這將會刪除「所有」目前的社團設定！")
    if st.button("🧨 確定清空", type="primary"):
        config_data["clubs"] = {}; save_config(config_data); st.success("✅ 社團清單已歸零！"); time.sleep(1); st.rerun()

def render_health_bar(limit, current):
    remain = limit - current
    blocks = ""
    for i in range(limit):
        color = "#22C55E" if i < remain else "#E5E7EB"
        blocks += f'<div style="width:12px; height:16px; background-color:{color}; border-radius:2px; border:1px solid white; flex:none;"></div>'
    return f'<div style="display:flex; gap:2px; margin:5px 0;">{blocks}</div><div style="font-size:13px; font-weight:bold; color:gray;">剩餘名額: {remain} / {limit}</div>'

# 批量處理
def admin_batch_action(action, selected_rows, target_club=None):
    current_df = load_registrations()
    targets = set((r['班級'], r['座號']) for r in selected_rows)
    
    if action == "delete":
        new_df = current_df[~current_df.apply(lambda x: (x['班級'], x['座號']) in targets, axis=1)]
        new_df.to_csv(REG_FILE, index=False, encoding="utf-8-sig")
        st.toast(f"✅ 已批量踢除 {len(selected_rows)} 人", icon="🗑️")
        time.sleep(1); st.rerun()
        
    elif action == "move":
        c_limit = config_data["clubs"][target_club]["limit"]
        c_current = len(current_df[current_df["社團"] == target_club])
        if c_current + len(selected_rows) > c_limit:
            st.error(f"❌ 目標社團 {target_club} 空間不足！餘額 {c_limit - c_current}，欲轉入 {len(selected_rows)}")
            return

        new_df = current_df[~current_df.apply(lambda x: (x['班級'], x['座號']) in targets, axis=1)]
        new_records = []
        for r in selected_rows:
            new_records.append({
                "班級": r['班級'], "座號": r['座號'], "姓名": r['姓名'],
                "社團": target_club, "報名時間": get_taiwan_now().strftime('%Y-%m-%d %H:%M:%S'),
                "狀態": "正取"
            })
        
        final_df = pd.concat([new_df, pd.DataFrame(new_records)], ignore_index=True)
        final_df.to_csv(REG_FILE, index=False, encoding="utf-8-sig")
        st.toast(f"✅ 已批量轉移 {len(selected_rows)} 人至 {target_club}", icon="🔄")
        time.sleep(1); st.rerun()

# 批量補報名
def admin_batch_add(selected_rows, target_club):
    current_df = load_registrations()
    c_limit = config_data["clubs"][target_club]["limit"]
    c_current = len(current_df[current_df["社團"] == target_club])
    
    if c_current + len(selected_rows) > c_limit:
        st.error(f"❌ 目標社團 {target_club} 空間不足！餘額 {c_limit - c_current}，欲報名 {len(selected_rows)}")
        return

    new_records = []
    for r in selected_rows:
        new_records.append({
            "班級": r['班級'], "座號": r['座號'], "姓名": r['姓名'],
            "社團": target_club, "報名時間": get_taiwan_now().strftime('%Y-%m-%d %H:%M:%S'),
            "狀態": "正取"
        })
    
    final_df = pd.concat([current_df, pd.DataFrame(new_records)], ignore_index=True)
    final_df.to_csv(REG_FILE, index=False, encoding="utf-8-sig")
    st.toast(f"✅ 已成功強制報名 {len(selected_rows)} 人至 {target_club}", icon="➕")
    time.sleep(1); st.rerun()

# 批量刪名冊
def admin_batch_remove_students(selected_rows):
    if not os.path.exists(STUDENT_LIST_FILE): st.error("找不到名冊檔案"); return
    
    all_std = pd.read_excel(STUDENT_LIST_FILE, dtype={"班級": str, "座號": str, "學號": str})
    all_std["座號"] = all_std["座號"].apply(lambda x: str(x).zfill(2))
    
    targets = set((r['班級'], r['座號']) for r in selected_rows)
    new_std = all_std[~all_std.apply(lambda x: (x['班級'], x['座號']) in targets, axis=1)]
    
    new_std.to_excel(STUDENT_LIST_FILE, index=False)
    st.toast(f"✅ 已從全校名冊中永久移除 {len(selected_rows)} 人", icon="🗑️")
    time.sleep(1); st.rerun()

# 手動新增學生
def admin_add_student_manual(cls, seat, name, sid):
    if not os.path.exists(STUDENT_LIST_FILE): st.error("❌ 找不到名冊檔案"); return
    
    all_std = pd.read_excel(STUDENT_LIST_FILE, dtype={"班級": str, "座號": str, "學號": str})
    all_std["座號"] = all_std["座號"].apply(lambda x: str(x).zfill(2))
    
    if not all_std[(all_std["班級"] == cls) & (all_std["座號"] == seat)].empty:
        st.error(f"❌ 新增失敗：{cls} 班 {seat} 號 已經存在！")
        return

    new_row = pd.DataFrame({"班級": [cls], "座號": [seat], "姓名": [name], "學號": [sid]})
    final_std = pd.concat([all_std, new_row], ignore_index=True)
    
    try: final_std = final_std.sort_values(by=["班級", "座號"])
    except: pass
        
    final_std.to_excel(STUDENT_LIST_FILE, index=False)
    st.success(f"✅ 成功新增轉入生：{cls} 班 {seat} 號 {name}")
    time.sleep(1); st.rerun()

# 學生轉班/調號
def admin_transfer_student(old_c, old_s, new_c, new_s):
    if not os.path.exists(STUDENT_LIST_FILE): st.error("❌ 找不到名冊"); return
    
    all_std = pd.read_excel(STUDENT_LIST_FILE, dtype={"班級": str, "座號": str, "學號": str})
    all_std["座號"] = all_std["座號"].apply(lambda x: str(x).zfill(2))
    
    if not all_std[(all_std["班級"] == new_c) & (all_std["座號"] == new_s)].empty:
        st.error(f"❌ 移動失敗：目標 {new_c}班 {new_s}號 已經有人了！"); return

    mask = (all_std["班級"] == old_c) & (all_std["座號"] == old_s)
    if all_std[mask].empty:
        st.error("❌ 找不到原學生資料"); return
        
    all_std.loc[mask, "班級"] = new_c
    all_std.loc[mask, "座號"] = new_s
    try: all_std = all_std.sort_values(by=["班級", "座號"])
    except: pass
    all_std.to_excel(STUDENT_LIST_FILE, index=False)
    
    reg_df = load_registrations()
    reg_mask = (reg_df["班級"] == old_c) & (reg_df["座號"] == old_s)
    if not reg_df[reg_mask].empty:
        reg_df.loc[reg_mask, "班級"] = new_c
        reg_df.loc[reg_mask, "座號"] = new_s
        reg_df.to_csv(REG_FILE, index=False, encoding="utf-8-sig")
        st.success(f"✅ 成功轉班！該學生的社團資格已一併轉移至 {new_c} 班。")
    else:
        st.success(f"✅ 成功轉班！(該生尚未報名社團)")
        
    time.sleep(1.5); st.rerun()

# ==========================================
# 4. 主介面
# ==========================================
st.markdown("<h1 style='text-align: center; color: #1E3A8A;'>🏫 社團線上報名系統</h1>", unsafe_allow_html=True)

nav_col1, nav_col2, nav_col3 = st.columns(3)
if nav_col1.button("📝 學生報名", use_container_width=True): st.session_state.current_page = "📝 學生報名"; st.rerun()
if nav_col2.button("🔍 查詢報名", use_container_width=True): st.session_state.current_page = "🔍 查詢報名"; st.rerun()
if nav_col3.button("🛠️ 管理員後台", use_container_width=True): st.session_state.current_page = "🛠️ 管理員後台"; st.rerun()
st.divider()

# ==========================================
# 5. 管理員後台 (V18.14 混合式導航)
# ==========================================
if st.session_state.current_page == "🛠️ 管理員後台":
    if not st.session_state.get("is_admin", False):
        with st.form("admin_login"):
            st.image(generate_step_image("🔐", "管理員登入"), use_container_width=False)
            pwd = st.text_input("請輸入密碼", type="password")
            if st.form_submit_button("登入", type="primary"):
                if pwd == config_data["admin_password"]: st.session_state.is_admin = True; st.rerun()
                else: st.error("❌ 密碼錯誤")
    else:
        if st.button("🚪 安全登出"): st.session_state.is_admin = False; st.rerun()
        t1, t2, t3 = st.tabs(["📊 實時看板 (含管理)", "⚙️ 參數設定", "📁 名冊與備份"])
        
        with t1:
            df = load_registrations()
            if os.path.exists(STUDENT_LIST_FILE):
                all_students_df = pd.read_excel(STUDENT_LIST_FILE, dtype={"班級": str, "座號": str, "學號": str})
                all_students_df["座號"] = all_students_df["座號"].apply(lambda x: str(x).zfill(2))
            else:
                all_students_df = pd.DataFrame(columns=["班級", "座號", "姓名", "學號"])

            if not df.empty:
                c1, c2 = st.columns(2)
                c1.metric("總人數", f"{len(df)} 人"); c2.metric("正取", f"{len(df[df['狀態']=='正取'])} 人")
                st.bar_chart(df['社團'].value_counts())
                
                st.divider()
                
                view_tabs = st.tabs(["🏆 依社團檢視 (批量管理)", "🏫 依班級檢視 (批量管理)", "⚠️ 未選社名單 (批量處理)"])
                
                # 模式 1: 依社團 (V18.14 混合導航)
                with view_tabs[0]:
                    clubs_list = sorted(df["社團"].unique())
                    if clubs_list:
                        # 整理所有類別
                        all_categories = sorted(list(set([config_data["clubs"][c].get("category", "綜合") for c in clubs_list if c in config_data["clubs"]])))
                        if "全部" in all_categories: all_categories.remove("全部")
                        all_categories.insert(0, "全部")
                        
                        selected_cat = st.segmented_control("依類別篩選", all_categories, default="全部", key="cat_filter")
                        
                        target_club_to_show = None

                        if selected_cat == "全部":
                            # 情境 A: 顯示所有社團，使用 Dropdown
                            filtered_clubs = clubs_list
                            if filtered_clubs:
                                target_club_to_show = st.selectbox("👇 請選擇社團", filtered_clubs, key="sel_all_clubs")
                        else:
                            # 情境 B: 顯示特定類別，使用 Segmented Control (攤開顯示)
                            filtered_clubs = [c for c in clubs_list if config_data["clubs"].get(c, {}).get("category", "綜合") == selected_cat]
                            if filtered_clubs:
                                st.caption(f"👇 請直接點選 {selected_cat} 類別下的社團：")
                                target_club_to_show = st.segmented_control("社團列表", filtered_clubs, key=f"seg_clubs_{selected_cat}", label_visibility="collapsed")
                            else:
                                st.warning(f"沒有 {selected_cat} 的社團資料")

                        # 顯示選定社團的詳細資料
                        if target_club_to_show:
                            selected_club = target_club_to_show # 統一變數名稱
                            sub_df = df[df["社團"]==selected_club].sort_values(by=["班級", "座號"])
                            sub_df.insert(0, "選取", False)
                            st.write(f"### 📌 {selected_club} (目前 {len(sub_df)} 人)")
                            st.caption("💡 提示：勾選後可批量轉社或踢除")
                            
                            edited_club_df = st.data_editor(
                                sub_df,
                                column_config={"選取": st.column_config.CheckboxColumn("選取", default=False)},
                                disabled=["班級", "座號", "姓名", "社團", "報名時間", "狀態"],
                                hide_index=True, key=f"ed_club_{selected_club}"
                            )
                            sel_rows_club = edited_club_df[edited_club_df["選取"]].to_dict('records')
                            if sel_rows_club:
                                st.error(f"⚡ 已選取 {len(sel_rows_club)} 人")
                                cc1, cc2 = st.columns(2)
                                with cc1:
                                    target_c = st.selectbox("批量轉至", [c for c in config_data["clubs"] if c != selected_club], key=f"tg_club_mv_{selected_club}")
                                    if st.button("🔄 批量轉社", key=f"btn_club_mv_{selected_club}"): admin_batch_action("move", sel_rows_club, target_c)
                                with cc2:
                                    st.write(""); st.write("")
                                    if st.button("🗑️ 批量踢除", type="primary", key=f"btn_club_del_{selected_club}"): admin_batch_action("delete", sel_rows_club)
                    else: st.info("無資料")

                # 模式 2: 依班級
                with view_tabs[1]:
                    if not all_students_df.empty:
                        all_classes = sorted(all_students_df["班級"].unique())
                    else:
                        all_classes = sorted(df["班級"].unique())

                    if len(all_classes) > 0:
                        grade_select = st.segmented_control("選擇年級 (班級)", ["七年級", "八年級", "九年級", "其他"], default="七年級", key="g_reg")
                        target_prefix = "7" if grade_select == "七年級" else "8" if grade_select == "八年級" else "9" if grade_select == "九年級" else ""
                        if target_prefix: filtered_classes = [c for c in all_classes if str(c).startswith(target_prefix)]
                        else: filtered_classes = [c for c in all_classes if not str(c)[0] in ["7","8","9"]]

                        if filtered_classes:
                            cls_tabs = st.tabs([f"{c} 班" for c in filtered_classes])
                            for i, cls in enumerate(filtered_classes):
                                with cls_tabs[i]:
                                    class_reg_df = df[df["班級"]==cls].sort_values(by="座號")
                                    class_reg_df.insert(0, "選取", False)
                                    st.write(f"✅ **{cls} 班已報名學生 ({len(class_reg_df)} 人)**")
                                    st.caption("💡 提示：勾選後可批量操作")
                                    edited_df = st.data_editor(
                                        class_reg_df,
                                        column_config={"選取": st.column_config.CheckboxColumn("選取", default=False)},
                                        disabled=["班級", "座號", "姓名", "社團", "報名時間", "狀態"],
                                        hide_index=True, key=f"ed_reg_{cls}"
                                    )
                                    sel_rows = edited_df[edited_df["選取"]].to_dict('records')
                                    if sel_rows:
                                        st.error(f"⚡ 已選取 {len(sel_rows)} 人")
                                        ac1, ac2 = st.columns(2)
                                        with ac1:
                                            target_c = st.selectbox("批量轉至", list(config_data["clubs"].keys()), key=f"tg_mv_{cls}")
                                            if st.button("🔄 批量轉社", key=f"btn_mv_{cls}"): admin_batch_action("move", sel_rows, target_c)
                                        with ac2:
                                            st.write(""); st.write("")
                                            if st.button("🗑️ 批量踢除", type="primary", key=f"btn_del_{cls}"): admin_batch_action("delete", sel_rows)
                        else: st.warning(f"無 {grade_select} 資料")
                    else: st.info("無班級資料")

                # 模式 3: 未選社名單
                with view_tabs[2]:
                    if not all_students_df.empty:
                        reg_set = set(zip(df["班級"], df["座號"]))
                        unreg_list = [row for _, row in all_students_df.iterrows() if (row["班級"], row["座號"]) not in reg_set]
                        unreg_df = pd.DataFrame(unreg_list)

                        if not unreg_df.empty:
                            st.error(f"⚠️ 全校尚未報名總人數：{len(unreg_df)} 人")
                            unreg_classes = sorted(unreg_df["班級"].unique())
                            g_sel_un = st.segmented_control("選擇年級 (未報名)", ["七年級", "八年級", "九年級", "其他"], default="七年級", key="g_unreg")
                            pfx = "7" if g_sel_un == "七年級" else "8" if g_sel_un == "八年級" else "9" if g_sel_un == "九年級" else ""
                            if pfx: f_cls = [c for c in unreg_classes if str(c).startswith(pfx)]
                            else: f_cls = [c for c in unreg_classes if not str(c)[0] in ["7","8","9"]]

                            if f_cls:
                                tab_titles = [f"{c} 班 ({len(unreg_df[unreg_df['班級'] == c])})" for c in f_cls]
                                u_tabs = st.tabs(tab_titles)
                                for i, c in enumerate(f_cls):
                                    with u_tabs[i]:
                                        target_unreg = unreg_df[unreg_df["班級"] == c].sort_values(by="座號")
                                        target_unreg.insert(0, "選取", False)
                                        st.caption("💡 提示：勾選後可進行強制分發或刪除名單")
                                        edited_unreg = st.data_editor(
                                            target_unreg[["選取", "班級", "座號", "姓名", "學號"]],
                                            column_config={"選取": st.column_config.CheckboxColumn("選取", default=False)},
                                            disabled=["班級", "座號", "姓名", "學號"],
                                            hide_index=True, key=f"ed_unreg_{c}"
                                        )
                                        sel_unreg = edited_unreg[edited_unreg["選取"]].to_dict('records')
                                        if sel_unreg:
                                            st.warning(f"⚡ 已選取 {len(sel_unreg)} 位未報名學生")
                                            uc1, uc2 = st.columns(2)
                                            with uc1:
                                                target_add = st.selectbox("強制分發至...", list(config_data["clubs"].keys()), key=f"tg_add_{c}")
                                                if st.button("🔄 批量強制報名", key=f"btn_add_{c}"): admin_batch_add(sel_unreg, target_add)
                                            with uc2:
                                                st.write(""); st.write("")
                                                if st.button("🗑️ 從名冊移除 (慎用)", type="primary", key=f"btn_rm_{c}"): admin_batch_remove_students(sel_unreg)
                            else:
                                st.success(f"太棒了！{g_sel_un} 所有學生都已完成報名！")
                        else:
                            st.success("🎉 全校所有人都已完成報名！")
                    else:
                        st.warning("尚未匯入學生名冊 (students.xlsx)，無法比對未報名名單。")
            else: st.info("尚無資料")

        with t2:
            st.write("### 🏆 社團匯入設定")
            c_clear, _ = st.columns([1,2])
            if c_clear.button("🧨 清空所有社團"): confirm_clear_clubs()
            f = st.file_uploader("匯入 (Word/Excel)", type=["xlsx", "docx"])
            if f and st.button("📥 開始匯入"):
                try:
                    count = 0
                    cats_found = set()
                    keywords = ["類別", "類型", "性質", "分類", "Category", "Type"]

                    if f.name.endswith(".xlsx"):
                        d = pd.read_excel(f)
                        d = d.dropna(axis=1, how='all')
                        d = d.loc[:, ~d.columns.str.contains('^Unnamed')]
                        
                        target_col = None
                        for col in d.columns:
                            if any(k in str(col) for k in keywords):
                                target_col = col
                                break
                        
                        for _, r in d.iterrows():
                            limit = 30
                            if '名額' in r:
                                try: limit = int(r['名額'])
                                except: pass
                            
                            category = "綜合"
                            if target_col:
                                val = str(r[target_col]).strip()
                                if val and val.lower() != 'nan': category = val
                            elif not d.empty:
                                val = str(r.iloc[-1]).strip()
                                if val and val.lower() != 'nan': category = val
                            
                            cats_found.add(category)
                            name = str(r['社團名稱']).strip()
                            if name: 
                                config_data["clubs"][name] = {"limit": limit, "category": category}
                                count += 1

                    elif f.name.endswith(".docx"):
                        doc = Document(f)
                        if doc.tables:
                            t = doc.tables[0]
                            header_cells = t.rows[0].cells
                            target_index = -1
                            for i, cell in enumerate(header_cells):
                                txt = cell.text.strip().replace("\n","").replace("\r","")
                                if any(k in txt for k in keywords):
                                    target_index = i
                                    break
                            
                            for i, r in enumerate(t.rows):
                                if i == 0: continue
                                cells = r.cells
                                if len(cells) >= 2:
                                    name = cells[1].text.strip()
                                    limit = 30
                                    if len(cells) >= 5:
                                        digs = re.findall(r'\d+', cells[4].text.strip())
                                        if digs: limit = int(digs[0])
                                    
                                    category = "綜合"
                                    if target_index != -1 and target_index < len(cells):
                                        val = cells[target_index].text.strip().replace("\n","")
                                        if val: category = val
                                    elif len(cells) >= 1:
                                        val = cells[-1].text.strip().replace("\n","")
                                        if val: category = val
                                    
                                    cats_found.add(category)
                                    if name:
                                        config_data["clubs"][name] = {"limit": limit, "category": category}
                                        count += 1
                                        
                    if cats_found: st.toast(f"已偵測類別：{', '.join(cats_found)}")
                    save_config(config_data); st.success(f"匯入 {count} 筆資料成功！(已自動分類)"); time.sleep(1); st.rerun()
                except Exception as e: st.error(f"匯入錯誤: {e}")

            st.divider()
            for c, cfg in list(config_data["clubs"].items()):
                with st.container(border=True):
                    cc1, cc2, cc3, cc4 = st.columns([1.5, 1, 1, 0.5])
                    nn = cc1.text_input("名稱", c, key=f"n_{c}")
                    cat = cc2.text_input("類別", value=cfg.get("category", "綜合"), key=f"cat_{c}")
                    nl = cc3.number_input("名額", value=cfg['limit'], key=f"l_{c}")
                    if cc4.button("🗑️", key=f"d_{c}"): del config_data["clubs"][c]; save_config(config_data); st.rerun()
                    
                    if nn != c or nl != cfg['limit'] or cat != cfg.get("category", "綜合"):
                        config_data["clubs"][nn] = {"limit": int(nl), "category": cat}
                        if nn != c: del config_data["clubs"][c]
                        save_config(config_data)
            if st.button("➕ 新增社團"): config_data["clubs"]["新社團"] = {"limit": 30, "category": "綜合"}; save_config(config_data); st.rerun()

        with t3:
            st.write("### 👥 學生資料異動管理")
            with st.expander("➕ 手動新增學生 (轉入生)", expanded=False):
                with st.form("add_student_form", clear_on_submit=True):
                    c1, c2, c3, c4 = st.columns(4)
                    new_class = c1.text_input("班級 (如 701)")
                    new_seat = c2.text_input("座號 (如 35)")
                    new_name = c3.text_input("姓名")
                    new_sid = c4.text_input("學號")
                    if st.form_submit_button("確認新增"):
                        if new_class and new_seat and new_name and new_sid:
                            admin_add_student_manual(new_class, new_seat.zfill(2), new_name, new_sid)
                        else: st.error("❌ 所有欄位都必須填寫！")

            with st.expander("🔄 學生轉班 / 修改座號 (保留社團)", expanded=False):
                with st.form("transfer_student_form", clear_on_submit=True):
                    tc1, tc2, tc3, tc4 = st.columns([1,1,0.2,2])
                    old_c = tc1.text_input("舊班級")
                    old_s = tc2.text_input("舊座號")
                    tc3.markdown("## ➡️")
                    with tc4:
                        nc1, nc2 = st.columns(2)
                        new_c = nc1.text_input("新班級")
                        new_s = nc2.text_input("新座號")
                    if st.form_submit_button("確認異動"):
                        if old_c and old_s and new_c and new_s:
                            admin_transfer_student(old_c, old_s.zfill(2), new_c, new_s.zfill(2))
                        else: st.error("❌ 欄位不完整")

            st.divider()
            st.write("### 📥 資料下載與更新")
            if not df.empty:
                csv = df.to_csv(index=False, encoding="utf-8-sig").encode("utf-8-sig")
                st.download_button("📥 下載名單 CSV", csv, "registrations.csv", "text/csv")
            
            up_std = st.file_uploader("更新學生名冊 (students.xlsx)", type=["xlsx"])
            if up_std: pd.read_excel(up_std, dtype=str).to_excel(STUDENT_LIST_FILE, index=False); st.success("名冊更新成功")
            st.divider()
            if st.button("🧨 清空報名資料"): confirm_clear_data()

# ==========================================
# 6. 學生報名
# ==========================================
elif st.session_state.current_page == "📝 學生報名":
    now = get_taiwan_now()
    s_dt = datetime.strptime(config_data["start_time"], "%Y-%m-%d %H:%M:%S")
    e_dt = datetime.strptime(config_data["end_time"], "%Y-%m-%d %H:%M:%S")

    if now < s_dt: st.warning("⏳ 系統未開放"); st.stop()
    if now > e_dt: st.error("❌ 報名已截止"); st.stop()

    if not os.path.exists(STUDENT_LIST_FILE): st.error("❌ 找不到 students.xlsx"); st.stop()
    std_df = pd.read_excel(STUDENT_LIST_FILE, dtype={"班級": str, "座號": str, "學號": str})
    std_df["座號"] = std_df["座號"].apply(lambda x: str(x).zfill(2))
    
    all_classes = sorted(std_df["班級"].unique())
    
    st.image(generate_step_image("1", "選擇年級"), use_container_width=False)
    grade_opts = ["七年級", "八年級", "九年級"]
    sel_grade = st.segmented_control("年級", grade_opts, key="std_grade_sel", label_visibility="collapsed")

    if sel_grade:
        prefix = "7" if sel_grade == "七年級" else "8" if sel_grade == "八年級" else "9"
        target_classes = [c for c in all_classes if str(c).startswith(prefix)]
        
        st.image(generate_step_image("2", "選擇班級"), use_container_width=False)
        sel_class = st.segmented_control("班級", target_classes, key="std_class_sel", label_visibility="collapsed")
        
        if sel_class:
            st.image(generate_step_image("3", "選擇座號"), use_container_width=False)
            seats = sorted(std_df[std_df["班級"] == sel_class]["座號"].unique())
            sel_seat = st.segmented_control("座號", seats, label_visibility="collapsed")
            if sel_seat:
                row = std_df[(std_df["班級"] == sel_class) & (std_df["座號"] == sel_seat)].iloc[0]
                current_key = f"{sel_class}_{sel_seat}"
                if st.session_state.last_student != current_key:
                    st.session_state.id_verified = False
                    st.session_state.last_student = current_key

                st.divider()
                with st.form("verify_form"):
                    st.image(generate_step_image("4", "身分驗證"), use_container_width=False)
                    sid = st.text_input("🔑 輸入學號", type="password")
                    if st.form_submit_button("驗證", use_container_width=True):
                        if sid == str(row["學號"]):
                            st.session_state.id_verified = True
                            st.markdown(f"""
                            <div style="background-color:#E0F2FE; padding:20px; border-radius:10px; border-left: 10px solid #1E3A8A; text-align: left; margin-bottom: 20px;">
                                <h2 style="color:#1E3A8A; margin:0; font-weight:900;">👋 歡迎登入：{row['姓名']} 同學</h2>
                                <p style="color:#64748B; margin:0; font-size: 18px;">請選擇下方社團進行報名</p>
                            </div>
                            """, unsafe_allow_html=True)
                        else: st.session_state.id_verified = False; st.error("學號錯誤")

                if st.session_state.id_verified:
                    st.divider()
                    st.image(generate_step_image("5", "選擇社團"), use_container_width=False)
                    @st.fragment(run_every=3)
                    def show_clubs():
                        live = load_registrations()
                        mine = live[(live["班級"] == sel_class) & (live["座號"] == sel_seat)]
                        is_reg = not mine.empty
                        my_club = mine.iloc[0]["社團"] if is_reg else ""
                        if is_reg: st.info(f"您已報名：{my_club}")

                        for c, cfg in config_data["clubs"].items():
                            c_reg = len(live[live["社團"] == c])
                            c_lim = cfg["limit"]
                            full = c_reg >= c_lim
                            with st.container(border=True):
                                c1, c2 = st.columns([0.75, 0.25], vertical_alignment="center")
                                with c1:
                                    user_img_png = os.path.join(IMAGES_DIR, f"{c}.png")
                                    user_img_jpg = os.path.join(IMAGES_DIR, f"{c}.jpg")
                                    if os.path.exists(user_img_png): st.image(user_img_png, use_container_width=True)
                                    elif os.path.exists(user_img_jpg): st.image(user_img_jpg, use_container_width=True)
                                    else: st.image(generate_text_image(c), use_container_width=True)
                                    
                                    st.markdown(render_health_bar(c_lim, c_reg), unsafe_allow_html=True)
                                
                                with c2:
                                    if full: st.button("已滿", disabled=True, key=f"f_{c}", use_container_width=True)
                                    else:
                                        if not is_reg:
                                            if st.button("報名", type="primary", key=f"r_{c}", use_container_width=True): confirm_submission(sel_class, sel_seat, row['姓名'], c)
                                        else:
                                            if my_club == c: st.button("✅", disabled=True, key=f"ok_{c}", use_container_width=True)
                                            else: st.button("鎖定", disabled=True, key=f"lk_{c}", use_container_width=True)
                    show_clubs()

# ==========================================
# 7. 查詢
# ==========================================
elif st.session_state.current_page == "🔍 查詢報名":
    st.subheader("🔍 查詢結果")
    q = st.text_input("輸入姓名")
    if st.button("查詢", use_container_width=True) and q:
        res = reg_df[reg_df["姓名"] == q]
        if not res.empty:
            st.success(f"找到 {len(res)} 筆")
            st.table(res[["班級", "座號", "社團", "狀態"]])
        else: st.warning("查無資料")