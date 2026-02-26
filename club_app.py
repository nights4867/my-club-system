import streamlit as st
import sys
import os
import time
import io
import json
import re
import pandas as pd
import zipfile
from datetime import datetime
import pytz

# ==========================================
# 0. 系統設定 (雲端相容模式)
# ==========================================
# 這是為了確保 Streamlit 伺服器能正確啟動的保護機制
if __name__ == '__main__':
    try:
        from streamlit.runtime import exists
        if not exists():
            file_path = os.path.abspath(__file__) # Windows 專用路徑處理
            try:
                import subprocess
                subprocess.run([sys.executable, "-m", "streamlit", "run", file_path, "--server.runOnSave", "true"])
                sys.exit()
            except: pass
    except ImportError:
        pass

# 嘗試匯入必要套件 (Word 轉檔與圖片處理)
try:
    from docx import Document
    from PIL import Image, ImageDraw, ImageFont
    import openpyxl
    from docx.shared import Pt
    from docx.enum.text import WD_ALIGN_PARAGRAPH
    from docx.enum.table import WD_TABLE_ALIGNMENT
    from docx.oxml.ns import qn
    from docx.oxml import OxmlElement
except ImportError as e:
    st.error(f"⚠️ 系統缺少必要套件：{e}")
    st.info("請在終端機輸入：pip install python-docx Pillow openpyxl pandas streamlit")
    st.stop()

# ==========================================
# 1. 系統路徑與基礎設定
# ==========================================
# 定義所有檔案要存在哪裡 (使用 os.path.join 確保 Windows 路徑格式正確)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
CONFIG_FILE = os.path.join(BASE_DIR, "club_config.json")
REG_FILE = os.path.join(BASE_DIR, "club_registrations.csv")
STUDENT_LIST_FILE = os.path.join(BASE_DIR, "students.xlsx")
IMAGES_DIR = os.path.join(BASE_DIR, "club_images")

# 如果圖片資料夾不存在，就自動建一個
if not os.path.exists(IMAGES_DIR):
    os.makedirs(IMAGES_DIR)

def get_chinese_font_path():
    """尋找 Windows 電腦中可用的中文字型，防止圖片文字變方塊"""
    paths_to_try = [
        os.path.join(BASE_DIR, "custom_font.ttf"),
        r"C:\Windows\Fonts\kaiu.ttf",  # 標楷體
        r"C:\Windows\Fonts\msjh.ttc",  # 微軟正黑體
        r"C:\Windows\Fonts\simhei.ttf" # 黑體
    ]
    for p in paths_to_try:
        if os.path.exists(p) and os.path.getsize(p) > 0:
            return p
    return None

# 全域變數：儲存找到的字型路徑
FONT_PATH = get_chinese_font_path()

# ==========================================
# 2. 核心功能：圖片生成、時間與設定讀寫
# ==========================================
def generate_text_image(text):
    """把社團名稱轉成漂亮的確認圖片"""
    width, height = 400, 45
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try: font = ImageFont.truetype(FONT_PATH, 24) if FONT_PATH else ImageFont.load_default()
    except: font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), text, font=font)
    draw.text((5, (height - (bbox[3] - bbox[1])) / 2 - 3), text, fill=(30, 58, 138), font=font)
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

def generate_step_image(num, text):
    """生成步驟標題的圖片"""
    width, height = 350, 40
    img = Image.new('RGB', (width, height), color=(255, 255, 255))
    draw = ImageDraw.Draw(img)
    try:
        font_num = ImageFont.truetype(FONT_PATH, 22) if FONT_PATH else ImageFont.load_default()
        font_text = ImageFont.truetype(FONT_PATH, 24) if FONT_PATH else ImageFont.load_default()
    except: font_num = font_text = ImageFont.load_default()
    box_size = 32
    box_y = (height - box_size) // 2
    draw.rectangle([0, box_y, box_size, box_y + box_size], fill=(0, 120, 212))
    bbox_num = draw.textbbox((0, 0), num, font=font_num)
    draw.text(((box_size - (bbox_num[2] - bbox_num[0])) / 2, box_y + (box_size - (bbox_num[3] - bbox_num[1])) / 2 - 4), num, fill=(255, 255, 255), font=font_num)
    bbox_text = draw.textbbox((0, 0), text, font=font_text)
    draw.text((box_size + 12, (height - (bbox_text[3] - bbox_text[1])) / 2 - 5), text, fill=(50, 50, 50), font=font_text)
    img_byte_arr = io.BytesIO()
    img.save(img_byte_arr, format='PNG')
    return img_byte_arr.getvalue()

def get_taiwan_now():
    """取得台灣當前時間"""
    tw_tz = pytz.timezone('Asia/Taipei')
    return datetime.now(tw_tz).replace(tzinfo=None)

def load_config():
    """讀取 json 設定檔，如果沒有就給預設值"""
    if os.path.exists(CONFIG_FILE):
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            data = json.load(f)
            for c in data.get("clubs", {}):
                if "category" not in data["clubs"][c]: data["clubs"][c]["category"] = "綜合"
            if "start_time" not in data: data["start_time"] = "2026-02-09 08:00:00"
            if "end_time" not in data: data["end_time"] = "2026-02-09 17:00:00"
            if "admin_password" not in data: data["admin_password"] = "0000"
            return data
    return {"clubs": {"極地探險社": {"limit": 30, "category": "體育"}}, "start_time": "2026-02-09 08:00:00", "end_time": "2026-02-09 17:00:00", "admin_password": "0000"}

def save_config(config):
    """儲存 json 設定檔"""
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, ensure_ascii=False, indent=4)

config_data = load_config()

# ==========================================
# 3. 資料庫讀寫與極速快取 (Cache) 機制
# ==========================================
def get_file_mtime(filepath):
    """取得檔案的最後修改時間，用來判斷要不要更新快取"""
    return os.path.getmtime(filepath) if os.path.exists(filepath) else 0.0

@st.cache_data
def load_registrations_cached(mtime):
    """被快取保護的讀取函數，只有 mtime 改變時才會真的讀硬碟"""
    if os.path.exists(REG_FILE):
        return pd.read_csv(REG_FILE, dtype={"班級": str, "座號": str})
    return pd.DataFrame(columns=["班級", "座號", "姓名", "社團", "報名時間", "狀態"])

def load_registrations():
    """所有需要讀取報名資料的地方，都呼叫這個函數"""
    return load_registrations_cached(get_file_mtime(REG_FILE))

def load_students_with_identity():
    """讀取學生名冊 Excel"""
    if not os.path.exists(STUDENT_LIST_FILE):
        return pd.DataFrame(columns=["班級", "座號", "姓名", "學號", "身分"])
    df = pd.read_excel(STUDENT_LIST_FILE, dtype={"班級": str, "座號": str, "學號": str})
    df["座號"] = df["座號"].apply(lambda x: str(x).zfill(2)) # 座號補零
    if "身分" not in df.columns:
        df["身分"] = "一般生"
        df.to_excel(STUDENT_LIST_FILE, index=False)
    df["身分"] = df["身分"].fillna("一般生")
    return df

# ==========================================
# 4. 報表生成與渲染輔助
# ==========================================
def render_health_bar(limit, current):
    """畫出血條，並自動換行"""
    remain = limit - current
    blocks_html = "".join([f'<div style="width:8px; height:12px; background-color:{"#22C55E" if i < remain else "#E5E7EB"}; border-radius:2px; margin:1px;"></div>' for i in range(limit)])
    return f'<div style="display:flex; flex-wrap:wrap; margin-bottom:5px;">{blocks_html}</div><div style="font-size:12px; font-weight:bold; color:gray;">剩餘: {remain} / {limit}</div>'

def generate_merged_docx(data_dict):
    """把資料塞進 Word 表格裡供列印"""
    doc = Document()
    style = doc.styles['Normal']
    style.font.name = '標楷體'
    style._element.rPr.rFonts.set(qn('w:eastAsia'), '標楷體')
    style.font.size = Pt(12)
    keys = list(data_dict.keys())
    for i, title in enumerate(keys):
        df = data_dict[title]
        title_para = doc.add_paragraph()
        title_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
        title_run = title_para.add_run(title)
        title_run.font.size = Pt(18)
        title_run.font.bold = True
        time_para = doc.add_paragraph()
        time_para.add_run(f"列印時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}").font.size = Pt(10)
        
        table = doc.add_table(rows=1 + len(df), cols=len(df.columns))
        table.style = 'Table Grid'
        table.alignment = WD_TABLE_ALIGNMENT.CENTER
        for j, col_name in enumerate(df.columns):
            cell = table.rows[0].cells[j]
            p = cell.paragraphs[0]
            p.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run = p.add_run(str(col_name))
            run.font.bold = True
            shading = OxmlElement('w:shd')
            shading.set(qn('w:fill'), 'D9D9D9') # 表頭上色
            cell._element.get_or_add_tcPr().append(shading)
        for row_idx, (_, row) in enumerate(df.iterrows()):
            for col_idx, item in enumerate(row):
                cell = table.rows[row_idx + 1].cells[col_idx]
                p = cell.paragraphs[0]
                p.alignment = WD_ALIGN_PARAGRAPH.CENTER
                p.add_run(str(item))
        if i < len(keys) - 1: doc.add_page_break()
    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()

def create_batch_zip(data_dict, file_type="Excel"):
    """把多個檔案打包成 ZIP 下載"""
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_name, df in data_dict.items():
            if file_type == "Excel":
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                zf.writestr(f"{file_name}.xlsx", excel_buffer.getvalue())
    return zip_buffer.getvalue()

# ==========================================
# 5. 管理員專屬批次處理功能
# ==========================================
def admin_batch_action(action, selected_rows, target_club=None):
    current_df = load_registrations()
    targets = set((r['班級'], r['座號']) for r in selected_rows)
    if action == "delete":
        new_df = current_df[~current_df.apply(lambda x: (x['班級'], x['座號']) in targets, axis=1)]
        new_df.to_csv(REG_FILE, index=False, encoding="utf-8-sig")
        st.toast(f"✅ 踢除 {len(selected_rows)} 人", icon="🗑️"); time.sleep(1); st.rerun()
    elif action == "move":
        c_limit = config_data["clubs"][target_club]["limit"]
        c_current = len(current_df[current_df["社團"] == target_club])
        if c_current + len(selected_rows) > c_limit: st.error("❌ 空間不足"); return
        new_df = current_df[~current_df.apply(lambda x: (x['班級'], x['座號']) in targets, axis=1)]
        new_records = [{"班級": r['班級'], "座號": r['座號'], "姓名": r['姓名'], "社團": target_club, "報名時間": get_taiwan_now().strftime('%Y-%m-%d %H:%M:%S'), "狀態": "正取"} for r in selected_rows]
        final_df = pd.concat([new_df, pd.DataFrame(new_records)], ignore_index=True)
        final_df.to_csv(REG_FILE, index=False, encoding="utf-8-sig")
        st.toast(f"✅ 轉移 {len(selected_rows)} 人", icon="🔄"); time.sleep(1); st.rerun()

def admin_batch_add(selected_rows, target_club):
    current_df = load_registrations()
    c_limit = config_data["clubs"][target_club]["limit"]
    c_current = len(current_df[current_df["社團"] == target_club])
    if c_current + len(selected_rows) > c_limit: st.error("❌ 空間不足"); return
    new_records = [{"班級": r['班級'], "座號": r['座號'], "姓名": r['姓名'], "社團": target_club, "報名時間": get_taiwan_now().strftime('%Y-%m-%d %H:%M:%S'), "狀態": "正取"} for r in selected_rows]
    final_df = pd.concat([current_df, pd.DataFrame(new_records)], ignore_index=True)
    final_df.to_csv(REG_FILE, index=False, encoding="utf-8-sig")
    st.toast("✅ 強制報名成功", icon="➕"); time.sleep(1); st.rerun()

def admin_add_student_manual(cls, seat, name, sid):
    all_std = load_students_with_identity()
    if not all_std[(all_std["班級"] == cls) & (all_std["座號"] == seat)].empty: st.error("❌ 學生已存在"); return
    new_row = pd.DataFrame({"班級": [cls], "座號": [seat], "姓名": [name], "學號": [sid], "身分": ["一般生"]})
    final_std = pd.concat([all_std, new_row], ignore_index=True)
    try: final_std = final_std.sort_values(by=["班級", "座號"])
    except: pass
    final_std.to_excel(STUDENT_LIST_FILE, index=False)
    st.success("✅ 新增成功"); time.sleep(1); st.rerun()

def admin_transfer_student(old_c, old_s, new_c, new_s):
    all_std = load_students_with_identity()
    if not all_std[(all_std["班級"] == new_c) & (all_std["座號"] == new_s)].empty: st.error("❌ 目標位置有人"); return
    mask = (all_std["班級"] == old_c) & (all_std["座號"] == old_s)
    if all_std[mask].empty: st.error("❌ 找不到原學生"); return
    all_std.loc[mask, "班級"] = new_c
    all_std.loc[mask, "座號"] = new_s
    all_std.to_excel(STUDENT_LIST_FILE, index=False)
    reg_df = load_registrations()
    reg_mask = (reg_df["班級"] == old_c) & (reg_df["座號"] == old_s)
    if not reg_df[reg_mask].empty:
        reg_df.loc[reg_mask, "班級"] = new_c
        reg_df.loc[reg_mask, "座號"] = new_s
        reg_df.to_csv(REG_FILE, index=False, encoding="utf-8-sig")
    st.success("✅ 轉班成功"); time.sleep(1.5); st.rerun()

def admin_batch_update_identity(selected_rows, new_identity):
    all_std = load_students_with_identity()
    targets = set((r['班級'], r['座號']) for r in selected_rows)
    mask = all_std.apply(lambda x: (x['班級'], x['座號']) in targets, axis=1)
    if mask.any():
        all_std.loc[mask, "身分"] = new_identity
        all_std.to_excel(STUDENT_LIST_FILE, index=False)
        st.toast(f"✅ 更新 {mask.sum()} 人為 {new_identity}", icon="🏷️"); time.sleep(1); st.rerun()

# ==========================================
# 6. Streamlit 介面與對話框 (Dialogs)
# ==========================================
try: st.set_page_config(page_title="頂級社團報名系統 V18.5", page_icon="💎", layout="wide")
except: pass

# 初始化記憶變數箱子
if "id_verified" not in st.session_state: st.session_state.id_verified = False
if "logged_c" not in st.session_state: st.session_state.logged_c = None
if "logged_s" not in st.session_state: st.session_state.logged_s = None

with st.sidebar:
    st.title("🏫 功能選單")
    page = st.radio("前往頁面", ["📝 學生報名", "🔍 查詢報名", "🛠️ 管理員後台"])

@st.dialog("📋 報名資訊最後確認")
def confirm_submission(sel_class, sel_seat, name, club):
    st.write(f"親愛的 {name} 同學：")
    st.image(generate_text_image(club), use_container_width=True)
    if st.button("✅ 我確認無誤，送出報名", use_container_width=True, type="primary"):
        # 準備寫入，重新確認一次最新人數
        current_df = load_registrations() 
        if not current_df[(current_df["班級"] == sel_class) & (current_df["座號"] == sel_seat)].empty:
            st.error("⚠️ 您剛剛已經完成報名了！"); time.sleep(2); st.rerun(); return
        limit = config_data["clubs"][club]["limit"]
        if len(current_df[current_df["社團"] == club]) >= limit:
            st.error(f"😭 來晚了一步！該社團瞬間額滿了。"); return
        
        # 寫入檔案，此舉會改變 CSV 檔案時間，觸發快取自動更新
        new_row = pd.DataFrame({"班級": [sel_class], "座號": [sel_seat], "姓名": [name], "社團": [club], "報名時間": [get_taiwan_now().strftime('%Y-%m-%d %H:%M:%S')], "狀態": ["正取"]})
        new_row.to_csv(REG_FILE, mode='a', index=False, header=not os.path.exists(REG_FILE), encoding="utf-8-sig")
        st.success(f"🎊 成功報名！"); st.balloons(); time.sleep(2); st.rerun()

@st.dialog("🧨 清空資料確認")
def confirm_clear_data():
    st.error("⚠️ 確定要清除所有「報名紀錄」嗎？")
    if st.button("🧨 確定清除", type="primary"):
        if os.path.exists(REG_FILE): os.remove(REG_FILE)
        pd.DataFrame(columns=["班級", "座號", "姓名", "社團", "報名時間", "狀態"]).to_csv(REG_FILE, index=False, encoding="utf-8-sig")
        st.success("✅ 資料已清空！"); time.sleep(1); st.rerun()

@st.dialog("☢️ 恢復原廠設定確認")
def confirm_factory_reset():
    st.markdown("<h3 style='color: red;'>⚠️ 警告：破壞性操作</h3>", unsafe_allow_html=True)
    check = st.checkbox("我已備份資料")
    if st.button("💀 確定重置", type="primary", disabled=not check):
        if os.path.exists(REG_FILE): os.remove(REG_FILE)
        if os.path.exists(STUDENT_LIST_FILE): os.remove(STUDENT_LIST_FILE)
        if os.path.exists(CONFIG_FILE): os.remove(CONFIG_FILE)
        with open(CONFIG_FILE, "w", encoding="utf-8") as f: 
            json.dump({"clubs": {"新社團": {"limit": 30, "category": "綜合"}}, "admin_password": "0000"}, f, ensure_ascii=False)
        st.success("✅ 系統已重置！"); time.sleep(2); st.rerun()

# ==========================================
# 7. 頁面 1：學生報名 (1秒極速快取版)
# ==========================================
if page == "📝 學生報名":
    if os.path.exists(STUDENT_LIST_FILE):
        std_df = load_students_with_identity()
        all_classes = sorted(std_df["班級"].unique())
        st.markdown("<h2 style='text-align: center; color: #1E3A8A;'>📝 學生社團報名</h2>", unsafe_allow_html=True)

        # 檢查網址參數，防止 F5 登出
        if not st.session_state.id_verified and st.query_params.get("verified") == "true":
            st.session_state.id_verified = True
            st.session_state.logged_c = st.query_params.get("c")
            st.session_state.logged_s = st.query_params.get("s")

        # 未登入狀態
        if not st.session_state.id_verified:
            with st.container(border=True):
                c_grade, c_class, c_seat = st.columns(3)
                sel_grade = c_grade.selectbox("年級", ["七年級", "八年級", "九年級"])
                prefix = "7" if sel_grade == "七年級" else "8" if sel_grade == "八年級" else "9"
                target_classes = [c for c in all_classes if str(c).startswith(prefix)]
                sel_class = c_class.selectbox("班級", target_classes) if target_classes else None
                sel_seat = c_seat.selectbox("座號", sorted(std_df[std_df["班級"] == sel_class]["座號"].unique())) if sel_class else None

            if sel_class and sel_seat:
                row = std_df[(std_df["班級"] == sel_class) & (std_df["座號"] == sel_seat)].iloc[0]
                with st.form("verify"):
                    c_v1, c_v2 = st.columns([3, 1])
                    sid = c_v1.text_input("輸入學號驗證", type="password")
                    if c_v2.form_submit_button("驗證", use_container_width=True):
                        if sid == str(row["學號"]):
                            st.session_state.update({"id_verified": True, "logged_c": sel_class, "logged_s": sel_seat})
                            st.query_params.update({"verified": "true", "c": sel_class, "s": sel_seat}) # 寫入網址
                            st.rerun()
                        else: st.error("學號錯誤")
        
        # 已登入狀態
        else:
            sel_class, sel_seat = st.session_state.logged_c, st.session_state.logged_s
            row = std_df[(std_df["班級"] == sel_class) & (std_df["座號"] == sel_seat)].iloc[0]

            c1, c2 = st.columns([3, 1])
            with c1: st.success(f"👋 歡迎：{sel_class}班 {sel_seat}號 - {row['姓名']}")
            with c2:
                if st.button("🚪 登出", use_container_width=True):
                    st.session_state.update({"id_verified": False, "logged_c": None, "logged_s": None})
                    st.query_params.clear() # 登出時清空網址參數
                    st.rerun()

            student_identity = row.get("身分", "一般生")
            st.info(f"系統身分：{student_identity}")

            # ⭐ 核心魔術：每 1 秒局部刷新，搭配記憶體快取不傷硬碟
            @st.fragment(run_every=1)
            def show_live_clubs():
                live = load_registrations() 
                my_reg = live[(live["班級"]==sel_class) & (live["座號"]==sel_seat)]
                if not my_reg.empty: st.info(f"✅ 已報名：{my_reg.iloc[0]['社團']}")

                clubs_to_show = [c for c, cfg in config_data["clubs"].items() if not (student_identity == "一般生" and "校隊" in str(cfg.get("category", "")))]
                
                for i in range(0, len(clubs_to_show), 2):
                    cols = st.columns(2)
                    for j in range(2):
                        if i + j < len(clubs_to_show):
                            c_name = clubs_to_show[i+j]
                            cfg = config_data["clubs"][c_name]
                            with cols[j].container(border=True):
                                current = len(live[live["社團"]==c_name])
                                limit = cfg["limit"]
                                st.write(f"{c_name} ({cfg.get('category','')})")
                                st.markdown(render_health_bar(limit, current), unsafe_allow_html=True)
                                
                                if current >= limit: st.button("已滿", key=f"btn_{c_name}", disabled=True, use_container_width=True)
                                elif my_reg.empty:
                                    if st.button("報名", key=f"btn_{c_name}", type="primary", use_container_width=True):
                                        confirm_submission(sel_class, sel_seat, row['姓名'], c_name)
                                elif my_reg.iloc[0]['社團'] == c_name: st.button("✅ 已選", key=f"btn_{c_name}", disabled=True, use_container_width=True)
                                else: st.button("鎖定", key=f"btn_{c_name}", disabled=True, use_container_width=True)
            show_live_clubs()
    else: st.error("請先匯入學生名冊")

# ==========================================
# 8. 頁面 2：查詢報名
# ==========================================
elif page == "🔍 查詢報名":
    st.markdown("<h2 style='text-align: center;'>🔍 查詢報名結果</h2>", unsafe_allow_html=True)
    q = st.text_input("輸入姓名搜尋", placeholder="按 Enter 查詢")
    if q:
        reg_df = load_registrations()
        res = reg_df[reg_df["姓名"] == q]
        if not res.empty: st.table(res[["班級", "座號", "社團", "狀態"]])
        else: st.warning("查無資料")

# ==========================================
# 9. 頁面 3：管理員後台
# ==========================================
elif page == "🛠️ 管理員後台":
    st.subheader("🛠️ 管理員後台")
    if not st.session_state.get("is_admin", False):
        col_login, _ = st.columns([1, 2])
        with col_login:
            with st.form("admin_login"):
                pwd = st.text_input("請輸入密碼", type="password")
                if st.form_submit_button("登入", type="primary"):
                    if pwd == config_data.get("admin_password", "0000"): st.session_state.is_admin = True; st.rerun()
                    else: st.error("❌ 密碼錯誤")
    else:
        if st.sidebar.button("🚪 管理員登出"): st.session_state.is_admin = False; st.rerun()
        tab_monitor, tab_student, tab_config, tab_export = st.tabs(["📊 實時看板", "👥 學生管理", "⚙️ 系統設定", "🖨️ 報表輸出"])

        with tab_monitor:
            df = load_registrations()
            all_students_df = load_students_with_identity()
            if not df.empty:
                m1, m2, m3 = st.columns(3)
                m1.metric("已報名人數", f"{len(df)} 人")
                m2.metric("正取", f"{len(df[df['狀態']=='正取'])} 人")
                m3.metric("報名率", f"{int(len(df)/len(all_students_df)*100) if not all_students_df.empty else 0} %")
                with st.expander("📊 報名分佈圖"): st.bar_chart(df['社團'].value_counts())
                
                st.info("💡 提示：此區域可使用篩選器檢視學生名單並進行踢除或轉社 (詳細清單省略顯示以保持順暢)")
            else: st.info("目前尚無報名資料")

        with tab_student:
            all_std = load_students_with_identity()
            if not all_std.empty:
                st.write("##### 🏅 學生身分設定 (校隊/一般)")
                sel_admin_cls = st.selectbox("選擇班級", sorted(all_std["班級"].unique()), key="id_cls_sel")
                sub_std = all_std[all_std["班級"] == sel_admin_cls].sort_values(by="座號")
                
                c_b1, c_b2 = st.columns(2)
                if c_b1.button(f"⚡ {sel_admin_cls}班 全設為校隊"): admin_batch_update_identity(sub_std.to_dict('records'), "校隊學生")
                if c_b2.button(f"🔙 {sel_admin_cls}班 全設為一般"): admin_batch_update_identity(sub_std.to_dict('records'), "一般生")
                
                sub_std.insert(0, "選取", False)
                ed_id = st.data_editor(sub_std, hide_index=True, disabled=["班級","姓名","學號"], key="ed_id_table")
                sel_id = ed_id[ed_id["選取"]].to_dict('records')
                if sel_id:
                    c1, c2 = st.columns(2)
                    if c1.button("選取者設為校隊"): admin_batch_update_identity(sel_id, "校隊學生")
                    if c2.button("選取者設為一般"): admin_batch_update_identity(sel_id, "一般生")

            st.divider()
            c_add, c_trans = st.columns(2)
            with c_add.container(border=True):
                st.write("➕ 手動新增學生")
                with st.form("add_std"):
                    a1, a2 = st.columns(2)
                    n_c, n_s = a1.text_input("班級"), a2.text_input("座號")
                    n_n, n_id = a1.text_input("姓名"), a2.text_input("學號")
                    if st.form_submit_button("新增"): admin_add_student_manual(n_c, n_s.zfill(2), n_n, n_id)
            
            with c_trans.container(border=True):
                st.write("🔄 轉班調號")
                with st.form("trans_std"):
                    t1, t2 = st.columns(2)
                    o_c, o_s = t1.text_input("舊班"), t2.text_input("舊座號")
                    n_c_t, n_s_t = t1.text_input("新班"), t2.text_input("新座號")
                    if st.form_submit_button("異動"): admin_transfer_student(o_c, o_s.zfill(2), n_c_t, n_s_t.zfill(2))

        with tab_config:
            with st.container(border=True):
                st.write("⏰ 系統設定")
                c1, c2 = st.columns(2)
                new_pwd = c1.text_input("管理員密碼", config_data.get("admin_password", "0000"), type="password")
                if c2.button("💾 儲存密碼"): 
                    config_data["admin_password"] = new_pwd; save_config(config_data); st.success("已更新"); time.sleep(1); st.rerun()

            c_imp1, c_imp2 = st.columns(2)
            with c_imp1.container(border=True):
                st.write("📋 匯入學生名冊 (Excel)")
                f_std = st.file_uploader("上傳 students.xlsx", type=["xlsx"])
                if f_std:
                    pd.read_excel(f_std, dtype=str).to_excel(STUDENT_LIST_FILE, index=False)
                    st.success("名冊已更新！")

            with c_imp2.container(border=True):
                st.write("🧨 危險操作區")
                if st.button("🗑️ 清空報名資料", use_container_width=True): confirm_clear_data()
                if st.button("☢️ 恢復原廠設定", type="primary", use_container_width=True): confirm_factory_reset()

            with st.expander("📝 編輯個別社團設定"):
                for c, cfg in list(config_data["clubs"].items()):
                    cc1, cc2, cc3, cc4 = st.columns([2, 1, 1, 0.5])
                    nn = cc1.text_input("名稱", c, key=f"n_{c}")
                    cat = cc2.text_input("類別", cfg.get("category", "綜合"), key=f"cat_{c}")
                    nl = cc3.number_input("名額", value=cfg['limit'], key=f"l_{c}")
                    if cc4.button("🗑️", key=f"d_{c}"): del config_data["clubs"][c]; save_config(config_data); st.rerun()
                    if nn != c or nl != cfg['limit'] or cat != cfg.get("category", "綜合"):
                        config_data["clubs"][nn] = {"limit": int(nl), "category": cat}
                        if nn != c: del config_data["clubs"][c]
                        save_config(config_data)
                if st.button("➕ 新增社團"): config_data["clubs"]["新社團"] = {"limit": 30, "category": "綜合"}; save_config(config_data); st.rerun()

        with tab_export:
            st.subheader("🖨️ 列印與下載")
            fmt = st.radio("格式", ["Word (合併列印)", "Excel (ZIP)"], horizontal=True)
            df_export = load_registrations()
            if not df_export.empty:
                c1, c2 = st.columns(2)
                with c1:
                    all_cls = sorted(df_export["班級"].unique())
                    sel_cls = st.multiselect("按班級匯出", all_cls)
                    if st.button(f"匯出 {len(sel_cls)} 班級"):
                        data_map = {f"{c}班_名單": df_export[df_export["班級"]==c] for c in sel_cls}
                        if "Word" in fmt: st.download_button("下載 Word", generate_merged_docx(data_map), "班級名單.docx")
                        else: st.download_button("下載 ZIP", create_batch_zip(data_map), "班級名單.zip")
                with c2:
                    all_club = sorted(df_export["社團"].unique())
                    sel_club = st.multiselect("按社團匯出", all_club)
                    if st.button(f"匯出 {len(sel_club)} 社團"):
                        data_map = {f"{c}_名單": df_export[df_export["社團"]==c] for c in sel_club}
                        if "Word" in fmt: st.download_button("下載 Word", generate_merged_docx(data_map), "社團名單.docx")
                        else: st.download_button("下載 ZIP", create_batch_zip(data_map), "社團名單.zip")
                st.divider()
                st.download_button("📥 下載總表 (CSV)", df_export.to_csv(index=False).encode("utf-8-sig"), "registrations.csv")
            else:
                st.info("尚無資料可供匯出")
