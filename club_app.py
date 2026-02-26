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
if __name__ == '__main__':
    try:
        from streamlit.runtime import exists
        if not exists():
            file_path = os.path.abspath(__file__)
            try:
                import subprocess
                subprocess.run([sys.executable, "-m", "streamlit", "run", file_path, "--server.runOnSave", "true"])
                sys.exit()
            except: pass
    except ImportError:
        pass

# 嘗試匯入必要套件
try:
    from docx import Document
    from PIL import Image, ImageDraw, ImageFont
    import openpyxl 
    
    # PDF 相關
    from reportlab.pdfgen import canvas
    from reportlab.lib.pagesizes import A4
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.lib import colors
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, PageBreak
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle

except ImportError as e:
    st.error(f"⚠️ 系統缺少必要套件：{e}")
    st.info("請確認 requirements.txt 包含：python-docx, Pillow, openpyxl, reportlab")
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

# --- [修改重點 1] 超級字型雷達 (解決黑方塊問題) ---
def get_chinese_font_path():
    """尋找電腦或專案中可用的中文字型"""
    # 建立一個清單，優先順序：專案資料夾內 > Windows 標楷體 > Windows 微軟正黑體
    paths_to_try = [
        os.path.join(BASE_DIR, "custom_font.ttf"), # 雲端備用：自帶標楷體 (已上傳)
        os.path.join(BASE_DIR, "kaiu.ttf"),      # 雲端備用：自帶標楷體
        os.path.join(BASE_DIR, "msjh.ttc"),      # 雲端備用：自帶正黑體
        "C:\\Windows\\Fonts\\kaiu.ttf",          # 本機 Windows 標楷體 (純TTF，ReportLab 最愛)
        "C:\\Windows\\Fonts\\msjh.ttc",          # 本機 Windows 微軟正黑體
        "C:\\Windows\\Fonts\\simhei.ttf"         # 本機 Windows 黑體
    ]
    for p in paths_to_try:
        if os.path.exists(p):
            return p
    return None

# 全域字型路徑
FONT_PATH = get_chinese_font_path()

# ------------------------------------------
# [核心 1] 社團名稱轉圖片
# ------------------------------------------
def generate_text_image(text):
    width, height = 400, 45 
    background_color = (255, 255, 255) 
    text_color = (30, 58, 138) 
    img = Image.new('RGB', (width, height), color=background_color)
    draw = ImageDraw.Draw(img)
    try:
        if FONT_PATH:
            font = ImageFont.truetype(FONT_PATH, 24)
        else:
            font = ImageFont.load_default()
    except: font = ImageFont.load_default()
    
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
    try:
        if FONT_PATH:
            font_num = ImageFont.truetype(FONT_PATH, 22) 
            font_text = ImageFont.truetype(FONT_PATH, 24) 
        else:
            font_num = ImageFont.load_default()
            font_text = ImageFont.load_default()
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
            # 確保欄位存在
            for c in data.get("clubs", {}):
                if "category" not in data["clubs"][c]: data["clubs"][c]["category"] = "綜合"
            if "start_time" not in data: data["start_time"] = "2026-02-09 08:00:00"
            if "end_time" not in data: data["end_time"] = "2026-02-09 17:00:00"
            if "admin_password" not in data: data["admin_password"] = "0000"
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

def load_students_with_identity():
    if not os.path.exists(STUDENT_LIST_FILE):
        return pd.DataFrame(columns=["班級", "座號", "姓名", "學號", "身分"])
    df = pd.read_excel(STUDENT_LIST_FILE, dtype={"班級": str, "座號": str, "學號": str})
    df["座號"] = df["座號"].apply(lambda x: str(x).zfill(2))
    if "身分" not in df.columns:
        df["身分"] = "一般生"
        df.to_excel(STUDENT_LIST_FILE, index=False)
    df["身分"] = df["身分"].fillna("一般生")
    return df

# --- [修改重點 2] PDF 生成 (套用超級字型雷達) ---
def generate_merged_pdf(data_dict):
    buffer = io.BytesIO()
    
    font_name = 'Helvetica' # 預設為不支援中文的安全牌
    
    # 嘗試註冊中文字型
    if FONT_PATH:
        try:
            # 將找到的路徑註冊為 'MyChineseFont'
            pdfmetrics.registerFont(TTFont('MyChineseFont', FONT_PATH))
            font_name = 'MyChineseFont'
        except Exception as e:
            st.error(f"字型載入失敗，PDF 可能無法顯示中文: {e}")
    else:
        st.warning("⚠️ 系統找不到中文字型檔，PDF 可能會出現黑方塊。")

    doc = SimpleDocTemplate(buffer, pagesize=A4)
    elements = []
    styles = getSampleStyleSheet()
    
    # 將字型套用到樣式中
    title_style = ParagraphStyle(
        'Title', parent=styles['Heading1'], fontName=font_name, fontSize=18, alignment=1, spaceAfter=20
    )
    normal_style = ParagraphStyle(
        'Normal', parent=styles['Normal'], fontName=font_name, fontSize=10
    )

    keys = list(data_dict.keys())
    for i, title in enumerate(keys):
        df = data_dict[title]
        elements.append(Paragraph(title, title_style))
        elements.append(Paragraph(f"列印時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
        elements.append(Spacer(1, 10))
        
        table_data = [df.columns.tolist()] + df.values.tolist()
        table = Table(table_data)
        table.setStyle(TableStyle([
            ('FONTNAME', (0, 0), (-1, -1), font_name), # 這裡也必須套用中文字型
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ]))
        elements.append(table)
        if i < len(keys) - 1: elements.append(PageBreak())
    doc.build(elements)
    return buffer.getvalue()

def create_batch_zip(data_dict, file_type="Excel"):
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
# 2. 介面設定
# ==========================================
try:
    st.set_page_config(page_title="頂級社團報名系統 V18.34", page_icon="💎", layout="wide")
except:
    pass

if "id_verified" not in st.session_state: st.session_state.id_verified = False
if "last_student" not in st.session_state: st.session_state.last_student = ""

with st.sidebar:
    st.title("🏫 功能選單")
    page = st.radio("前往頁面", ["📝 學生報名", "🔍 查詢報名", "🛠️ 管理員後台"])
    st.divider()
    st.caption("Designed with ❤️ via Streamlit")

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

@st.dialog("🧨 清空報名資料確認")
def confirm_clear_data():
    st.error("⚠️ 確定要清除所有「報名紀錄」嗎？")
    if st.button("🧨 確定清除", type="primary"):
        if os.path.exists(REG_FILE):
            os.remove(REG_FILE)
            pd.DataFrame(columns=["班級", "座號", "姓名", "社團", "報名時間", "狀態"]).to_csv(REG_FILE, index=False, encoding="utf-8-sig")
            st.success("✅ 資料已清空！"); time.sleep(1); st.rerun()

@st.dialog("🧨 清空社團清單確認")
def confirm_clear_clubs():
    st.warning("⚠️ 這將刪除所有社團設定！")
    if st.button("🧨 確定清空", type="primary"):
        config_data["clubs"] = {}; save_config(config_data); st.success("✅ 社團已歸零！"); time.sleep(1); st.rerun()

@st.dialog("☢️ 恢復原廠設定確認")
def confirm_factory_reset():
    st.markdown("<h3 style='color: red;'>⚠️ 警告：破壞性操作</h3><p>將刪除所有名冊、報名與設定。</p>", unsafe_allow_html=True)
    check = st.checkbox("我已備份資料")
    if st.button("💀 確定重置", type="primary", disabled=not check):
        if os.path.exists(REG_FILE): os.remove(REG_FILE)
        if os.path.exists(STUDENT_LIST_FILE): os.remove(STUDENT_LIST_FILE)
        if os.path.exists(CONFIG_FILE): os.remove(CONFIG_FILE)
        default_config = {"clubs": {"極地探險社": {"limit": 30, "category": "體育"}}, "start_time": "2026-02-09 08:00:00", "end_time": "2026-02-09 17:00:00", "admin_password": "0000"}
        with open(CONFIG_FILE, "w", encoding="utf-8") as f: json.dump(default_config, f, ensure_ascii=False, indent=4)
        st.success("✅ 系統已重置！"); time.sleep(2); st.rerun()

# --- 血條渲染函數 (固定方格 + 自動換行) ---
def render_health_bar(limit, current):
    remain = limit - current
    blocks_html = ""
    for i in range(limit):
        color = "#22C55E" if i < remain else "#E5E7EB"
        blocks_html += f'<div style="width:8px; height:12px; background-color:{color}; border-radius:2px; margin:1px;"></div>'
    
    container_html = f"""
    <div style="display:flex; flex-wrap:wrap; margin-bottom:5px;">
        {blocks_html}
    </div>
    <div style="font-size:12px; font-weight:bold; color:gray;">
        剩餘: {remain} / {limit}
    </div>
    """
    return container_html

# --- 管理員邏輯 ---
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

def admin_batch_remove_students(selected_rows):
    all_std = load_students_with_identity()
    targets = set((r['班級'], r['座號']) for r in selected_rows)
    new_std = all_std[~all_std.apply(lambda x: (x['班級'], x['座號']) in targets, axis=1)]
    new_std.to_excel(STUDENT_LIST_FILE, index=False)
    st.toast("✅ 已移除名冊", icon="🗑️"); time.sleep(1); st.rerun()

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
# 5. 管理員後台
# ==========================================
if page == "🛠️ 管理員後台":
    st.subheader("🛠️ 管理員後台")
    if not st.session_state.get("is_admin", False):
        col_login, _ = st.columns([1, 2])
        with col_login:
            with st.form("admin_login"):
                st.image(generate_step_image("🔐", "登入"), use_container_width=True)
                pwd = st.text_input("請輸入密碼", type="password")
                if st.form_submit_button("登入", type="primary"):
                    if pwd == config_data["admin_password"]: st.session_state.is_admin = True; st.rerun()
                    else: st.error("❌ 密碼錯誤")
    else:
        if st.sidebar.button("🚪 管理員登出"): st.session_state.is_admin = False; st.rerun()
        
        tab_monitor, tab_student, tab_config, tab_export = st.tabs([
            "📊 實時看板", "👥 學生管理", "⚙️ 系統設定", "🖨️ 報表輸出"
        ])
        
        with tab_monitor:
            df = load_registrations()
            all_students_df = load_students_with_identity()
            
            if not df.empty:
                m1, m2, m3 = st.columns(3)
                m1.metric("已報名人數", f"{len(df)} 人")
                m2.metric("正取", f"{len(df[df['狀態']=='正取'])} 人")
                m3.metric("報名率", f"{int(len(df)/len(all_students_df)*100) if not all_students_df.empty else 0} %")
                
                with st.expander("📊 查看社團報名長條圖", expanded=False):
                    st.bar_chart(df['社團'].value_counts())

                view_tabs = st.tabs(["🏆 依社團", "🏫 依班級", "⚠️ 未選社"])
                
                with view_tabs[0]:
                    clubs_list = sorted(df["社團"].unique())
                    if clubs_list:
                        sel_club_view = st.selectbox("選擇社團", ["全部"] + clubs_list, key="v_club")
                        if sel_club_view != "全部":
                            sub_df = df[df["社團"]==sel_club_view].sort_values(by=["班級", "座號"])
                            sub_df.insert(0, "選取", False)
                            edited = st.data_editor(sub_df, column_config={"選取": st.column_config.CheckboxColumn(default=False)}, hide_index=True, key="ed_c")
                            sel_rows = edited[edited["選取"]].to_dict('records')
                            if sel_rows:
                                c_act1, c_act2 = st.columns([1, 1])
                                with c_act1:
                                    if st.button("踢除", type="primary"): admin_batch_action("delete", sel_rows)
                                with c_act2:
                                    target = st.selectbox("轉移至", [c for c in config_data["clubs"] if c != sel_club_view], label_visibility="collapsed")
                                    if st.button("確認轉社"): admin_batch_action("move", sel_rows, target)
                    else: st.info("尚無資料")

                with view_tabs[1]:
                    classes = sorted(df["班級"].unique()) if not df.empty else []
                    if classes:
                        sel_cls = st.selectbox("選擇班級", classes, key="v_cls")
                        c_reg = df[df["班級"]==sel_cls].sort_values(by="座號")
                        c_reg.insert(0, "選取", False)
                        edited_c = st.data_editor(c_reg, hide_index=True, key="ed_cls")
                        sel_rows_c = edited_c[edited_c["選取"]].to_dict('records')
                        if sel_rows_c:
                            c_act_cls1, c_act_cls2 = st.columns([1, 1])
                            with c_act_cls1:
                                if st.button("批量踢除", key="del_cls_btn", type="primary"):
                                    admin_batch_action("delete", sel_rows_c)
                            with c_act_cls2:
                                target_cls_view = st.selectbox("批量轉移至", list(config_data["clubs"].keys()), key="tg_cls_view", label_visibility="collapsed")
                                if st.button("確認轉社", key="mv_cls_btn"):
                                    admin_batch_action("move", sel_rows_c, target_cls_view)
                    else: st.info("尚無資料")

                with view_tabs[2]:
                    if not all_students_df.empty:
                        reg_set = set(zip(df["班級"], df["座號"]))
                        unreg = all_students_df[~all_students_df.apply(lambda x: (x["班級"], x["座號"]) in reg_set, axis=1)]
                        if not unreg.empty:
                            st.write(f"共 {len(unreg)} 人未報名")
                            u_cls = sorted(unreg["班級"].unique())
                            sel_u_c = st.selectbox("篩選班級", ["全部"] + u_cls)
                            target_u = unreg if sel_u_c == "全部" else unreg[unreg["班級"] == sel_u_c]
                            target_u.insert(0, "選取", False)
                            ed_u = st.data_editor(target_u, hide_index=True, key="ed_u")
                            s_u = ed_u[ed_u["選取"]].to_dict('records')
                            if s_u:
                                t_add = st.selectbox("強制報名至", list(config_data["clubs"].keys()))
                                if st.button("執行"): admin_batch_add(s_u, t_add)
                        else: st.success("全員已報名！")
                    else: st.warning("請先匯入名冊")
            else: st.info("目前尚無報名資料")

        with tab_student:
            all_std = load_students_with_identity()
            if not all_std.empty:
                st.write("##### 🏅 學生身分設定 (校隊/一般)")
                c_s1, c_s2 = st.columns([1, 2])
                with c_s1:
                    sel_admin_cls = st.selectbox("選擇班級", sorted(all_std["班級"].unique()), key="id_cls_sel")
                
                sub_std = all_std[all_std["班級"] == sel_admin_cls].sort_values(by="座號")
                col_btn1, col_btn2 = st.columns(2)
                if col_btn1.button(f"⚡ {sel_admin_cls}班 全設為校隊", use_container_width=True):
                    admin_batch_update_identity(sub_std.to_dict('records'), "校隊學生")
                if col_btn2.button(f"🔙 {sel_admin_cls}班 全設為一般", use_container_width=True):
                    admin_batch_update_identity(sub_std.to_dict('records'), "一般生")
                
                sub_std.insert(0, "選取", False)
                ed_id = st.data_editor(sub_std, hide_index=True, disabled=["班級","姓名","學號"], key="ed_id_table")
                sel_id = ed_id[ed_id["選取"]].to_dict('records')
                if sel_id:
                    c_b1, c_b2 = st.columns(2)
                    if c_b1.button("設為校隊", key="btn_team"): admin_batch_update_identity(sel_id, "校隊學生")
                    if c_b2.button("設為一般", key="btn_normal"): admin_batch_update_identity(sel_id, "一般生")
            
            st.divider()
            col_add, col_trans = st.columns(2)
            with col_add:
                with st.container(border=True):
                    st.write("➕ **手動新增學生**")
                    with st.form("add_std"):
                        ac1, ac2 = st.columns(2)
                        n_c = ac1.text_input("班級")
                        n_s = ac2.text_input("座號")
                        n_n = ac1.text_input("姓名")
                        n_id = ac2.text_input("學號")
                        if st.form_submit_button("新增", use_container_width=True):
                            if n_c and n_s and n_n and n_id: admin_add_student_manual(n_c, n_s.zfill(2), n_n, n_id)
                            else: st.error("欄位不全")
            with col_trans:
                with st.container(border=True):
                    st.write("🔄 **學生轉班/調號**")
                    with st.form("trans_std"):
                        tc1, tc2 = st.columns(2)
                        o_c = tc1.text_input("舊班級")
                        o_s = tc2.text_input("舊座號")
                        n_c_t = tc1.text_input("新班級")
                        n_s_t = tc2.text_input("新座號")
                        if st.form_submit_button("執行異動", use_container_width=True):
                            if o_c and o_s and n_c_t and n_s_t: admin_transfer_student(o_c, o_s.zfill(2), n_c_t, n_s_t.zfill(2))
                            else: st.error("欄位不全")

        with tab_config:
            with st.container(border=True):
                st.write("⏰ **時間與密碼設定**")
                c_conf1, c_conf2, c_conf3 = st.columns(3)
                new_start = c_conf1.text_input("開始時間", config_data["start_time"])
                new_end = c_conf2.text_input("結束時間", config_data["end_time"])
                new_pwd = c_conf3.text_input("管理員密碼", config_data["admin_password"], type="password")
                if st.button("💾 儲存設定"):
                    config_data.update({"start_time": new_start, "end_time": new_end, "admin_password": new_pwd})
                    save_config(config_data); st.success("已更新"); time.sleep(1); st.rerun()

            c_imp1, c_imp2 = st.columns(2)
            with c_imp1:
                with st.container(border=True):
                    st.write("📋 **匯入社團簡章**")
                    if st.button("🧨 清空社團"): confirm_clear_clubs()
                    f_club = st.file_uploader("上傳 Excel/Word", type=["xlsx", "docx"], key="up_c")
                    
                    if f_club and st.button("📥 開始匯入"):
                        try:
                            count = 0
                            cats_found = set()
                            keywords = ["類別", "類型", "性質", "分類", "Category", "Type"]

                            if f_club.name.endswith(".xlsx"):
                                d = pd.read_excel(f_club)
                                d = d.dropna(axis=1, how='all')
                                d = d.loc[:, ~d.columns.str.contains('^Unnamed')]
                                target_col = None
                                for col in d.columns:
                                    if any(k in str(col) for k in keywords):
                                        target_col = col; break
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

                            elif f_club.name.endswith(".docx"):
                                doc = Document(f_club)
                                if doc.tables:
                                    t = doc.tables[0]
                                    header_cells = t.rows[0].cells
                                    target_index = -1
                                    for i, cell in enumerate(header_cells):
                                        txt = cell.text.strip().replace("\n","").replace("\r","")
                                        if any(k in txt for k in keywords):
                                            target_index = i; break
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
                            save_config(config_data); st.success(f"成功匯入 {count} 筆！"); time.sleep(1); st.rerun()
                        except Exception as e: st.error(f"匯入錯誤: {e}")
            
            with c_imp2:
                with st.container(border=True):
                    st.write("👥 **匯入學生名冊**")
                    st.caption("請上傳 students.xlsx")
                    f_std = st.file_uploader("上傳 Excel", type=["xlsx"], key="up_s")
                    if f_std:
                        pd.read_excel(f_std, dtype=str).to_excel(STUDENT_LIST_FILE, index=False)
                        st.success("名冊已更新")

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

            with st.expander("🧨 危險操作區 (慎用)", expanded=False):
                st.markdown("### ⚠️ 這裡的操作不可逆")
                d1, d2 = st.columns(2)
                if d1.button("🗑️ 清空報名資料", use_container_width=True): confirm_clear_data()
                if d2.button("☢️ 恢復原廠設定", type="primary", use_container_width=True): confirm_factory_reset()

        with tab_export:
            st.subheader("🖨️ 批次列印與下載中心")
            
            c_type, c_content = st.columns([1, 3])
            with c_type:
                st.info("選擇格式")
                fmt = st.radio("格式", ["PDF (合併列印)", "Excel (ZIP壓縮)"], label_visibility="collapsed")
            
            with c_content:
                tab_dl_cls, tab_dl_club = st.tabs(["🏫 按班級列印", "🏆 按社團列印"])
                
                with tab_dl_cls:
                    if not df.empty:
                        all_cls = sorted(df["班級"].unique())
                        sel_cls = st.multiselect("選擇班級", all_cls)
                        if st.button("全選班級"): sel_cls = all_cls
                        
                        if sel_cls:
                            if st.button(f"執行輸出 ({len(sel_cls)} 班)"):
                                data_map = {f"{c}班_名單": df[df["班級"]==c].sort_values("座號")[["班級","座號","姓名","社團"]] for c in sel_cls}
                                if "PDF" in fmt:
                                    out = generate_merged_pdf(data_map)
                                    st.download_button("⬇️ 下載 PDF", out, "班級名單.pdf", "application/pdf", type="primary")
                                else:
                                    out = create_batch_zip(data_map)
                                    st.download_button("⬇️ 下載 ZIP", out, "班級名單.zip", "application/zip", type="primary")
                    else: st.info("無資料")

                with tab_dl_club:
                    if not df.empty:
                        all_club = sorted(df["社團"].unique())
                        sel_club = st.multiselect("選擇社團", all_club)
                        if st.button("全選社團"): sel_club = all_club
                        
                        if sel_club:
                            if st.button(f"執行輸出 ({len(sel_club)} 社)"):
                                data_map = {f"{c}_名單": df[df["社團"]==c].sort_values(["班級","座號"])[["班級","座號","姓名","狀態"]] for c in sel_club}
                                if "PDF" in fmt:
                                    out = generate_merged_pdf(data_map)
                                    st.download_button("⬇️ 下載 PDF", out, "社團名單.pdf", "application/pdf", type="primary")
                                else:
                                    out = create_batch_zip(data_map)
                                    st.download_button("⬇️ 下載 ZIP", out, "社團名單.zip", "application/zip", type="primary")
                    else: st.info("無資料")
            
            st.divider()
            st.caption("👇 原始資料備份")
            dl1, dl2 = st.columns(2)
            if not df.empty:
                dl1.download_button("📥 總表 CSV", df.to_csv(index=False).encode("utf-8-sig"), "registrations.csv", "text/csv")
            if os.path.exists(STUDENT_LIST_FILE):
                with open(STUDENT_LIST_FILE, "rb") as f:
                    dl2.download_button("📥 學生名冊 Excel", f, "students.xlsx")

# ==========================================
# 6. 學生報名
# ==========================================
elif page == "📝 學生報名":
    if os.path.exists(STUDENT_LIST_FILE):
        std_df = load_students_with_identity()
        all_classes = sorted(std_df["班級"].unique())
        
        st.markdown("<h2 style='text-align: center; color: #1E3A8A;'>📝 學生社團報名</h2>", unsafe_allow_html=True)
        
        with st.container(border=True):
            c_grade, c_class, c_seat = st.columns(3)
            sel_grade = c_grade.selectbox("年級", ["七年級", "八年級", "九年級"])
            prefix = "7" if sel_grade == "七年級" else "8" if sel_grade == "八年級" else "9"
            target_classes = [c for c in all_classes if str(c).startswith(prefix)]
            sel_class = c_class.selectbox("班級", target_classes) if target_classes else None
            
            sel_seat = None
            if sel_class:
                seats = sorted(std_df[std_df["班級"] == sel_class]["座號"].unique())
                sel_seat = c_seat.selectbox("座號", seats)

        if sel_class and sel_seat:
            current_key = f"{sel_class}_{sel_seat}"
            if st.session_state.last_student != current_key:
                st.session_state.id_verified = False
                st.session_state.last_student = current_key
            
            row = std_df[(std_df["班級"] == sel_class) & (std_df["座號"] == sel_seat)].iloc[0]
            
            if not st.session_state.id_verified:
                with st.form("verify"):
                    c_v1, c_v2 = st.columns([3, 1])
                    sid = c_v1.text_input("輸入學號驗證", type="password", placeholder="請輸入學號")
                    if c_v2.form_submit_button("驗證", use_container_width=True):
                        if sid == str(row["學號"]):
                            st.session_state.id_verified = True
                            st.rerun()
                        else: st.error("學號錯誤")
            else:
                c1, c2 = st.columns([3, 1])
                with c1: st.success(f"👋 歡迎：{row['姓名']}")
                with c2:
                    if st.button("🚪 登出", use_container_width=True):
                        st.session_state.id_verified = False
                        st.session_state.last_student = ""
                        st.rerun()

                admin_set_identity = row.get("身分", "一般生")
                is_locked = (admin_set_identity == "校隊學生")
                
                c_id_info, c_id_sel = st.columns([2, 1])
                c_id_info.info(f"系統身分：{admin_set_identity}")
                student_identity = c_id_sel.radio("身分", ["一般生", "校隊學生"], index=1 if is_locked else 0, disabled=is_locked, horizontal=True)

                school_team_clubs = [c for c, data in config_data["clubs"].items() if "校隊" in str(data.get("category", ""))]
                if student_identity == "校隊學生": st.warning(f"🏅 僅顯示校隊社團：{', '.join(school_team_clubs)}")

                live = load_registrations()
                my_reg = live[(live["班級"]==sel_class) & (live["座號"]==sel_seat)]
                if not my_reg.empty: st.info(f"✅ 已報名：{my_reg.iloc[0]['社團']}")

                clubs_to_show = []
                for c, cfg in config_data["clubs"].items():
                    is_team = "校隊" in str(cfg.get("category", ""))
                    if student_identity == "校隊學生" and not is_team: continue
                    clubs_to_show.append(c)
                
                for i in range(0, len(clubs_to_show), 2):
                    cols = st.columns(2)
                    for j in range(2):
                        if i + j < len(clubs_to_show):
                            c_name = clubs_to_show[i+j]
                            cfg = config_data["clubs"][c_name]
                            with cols[j].container(border=True):
                                current = len(live[live["社團"]==c_name])
                                limit = cfg["limit"]
                                st.write(f"**{c_name}** ({cfg.get('category','')})")
                                st.markdown(render_health_bar(limit, current), unsafe_allow_html=True)
                                if current >= limit: st.button("已滿", key=f"btn_{c_name}", disabled=True, use_container_width=True)
                                else:
                                    if my_reg.empty:
                                        if st.button("報名", key=f"btn_{c_name}", type="primary", use_container_width=True):
                                            confirm_submission(sel_class, sel_seat, row['姓名'], c_name)
                                    elif my_reg.iloc[0]['社團'] == c_name:
                                        st.button("✅ 已選", key=f"btn_{c_name}", disabled=True, use_container_width=True)
                                    else:
                                        st.button("鎖定", key=f"btn_{c_name}", disabled=True, use_container_width=True)
    else: st.error("請先匯入學生名冊")

elif page == "🔍 查詢報名":
    st.markdown("<h2 style='text-align: center;'>🔍 查詢報名結果</h2>", unsafe_allow_html=True)
    q = st.text_input("輸入姓名搜尋", placeholder="按 Enter 查詢")
    if q:
        res = reg_df[reg_df["姓名"] == q]
        if not res.empty: st.table(res[["班級", "座號", "社團", "狀態"]])
        else: st.warning("查無資料")
