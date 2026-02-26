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
import tempfile
import shutil

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
    # PDF 相關 (改回 reportlab，但用更穩健的方式載入字型)
    from reportlab.lib.pagesizes import A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
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

# --- [修正] 字型路徑搜尋 (更穩健的版本) ---
@st.cache_resource(show_spinner=False)
def find_and_register_font():
    """穩健地找到並註冊中文字型，並快取結果"""
    # 嘗試多個可能的路徑
    paths_to_try = [
        os.path.join(BASE_DIR, "custom_font.ttf"),
        os.path.join(os.getcwd(), "custom_font.ttf"),
        "custom_font.ttf",
    ]
    
    font_path = None
    for p in paths_to_try:
        if os.path.exists(p) and os.path.getsize(p) > 0:
            font_path = p
            break
    
    if font_path is None:
        st.sidebar.warning("⚠️ 找不到 custom_font.ttf，PDF/圖片中的中文可能無法顯示")
        return None
    
    # 複製到 tempfile 以確保路徑可讀（避免 Streamlit Cloud 的路徑問題）
    tmp_dir = tempfile.mkdtemp()
    tmp_font_path = os.path.join(tmp_dir, 'custom_font.ttf')
    shutil.copy2(font_path, tmp_font_path)
    
    # 註冊字型
    try:
        pdfmetrics.registerFont(TTFont('ChineseFont', tmp_font_path))
        st.sidebar.success("✅ 標楷體字型載入成功")
        return 'ChineseFont'
    except Exception as e:
        st.sidebar.error(f"❌ PDF 字型註冊失敗: {e}")
        return None

# 在 App 啟動時執行一次字型註冊
CHINESE_FONT_NAME = find_and_register_font()

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
        # 直接使用註冊好的字型名稱
        if CHINESE_FONT_NAME:
            # 需要字型檔案的真實路徑給 Pillow
            font_path = os.path.join(BASE_DIR, "custom_font.ttf")
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

# ... (其他函式保持不變) ...

# --- [最終修正] PDF 生成函式 (回到 reportlab，但用穩健的字型載入) ---
def generate_merged_pdf(data_dict):
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4,
                           topMargin=30, bottomMargin=30,
                           leftMargin=30, rightMargin=30)
    
    elements = []
    
    # 檢查字型是否成功載入
    font_name = CHINESE_FONT_NAME if CHINESE_FONT_NAME else 'Helvetica'

    # 定義樣式
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'ChTitle', parent=styles['Title'],
        fontName=font_name, fontSize=18, leading=24, alignment=1 # 1=CENTER
    )
    normal_style = ParagraphStyle(
        'ChNormal', parent=styles['Normal'],
        fontName=font_name, fontSize=10, leading=14
    )
    table_header_style = ParagraphStyle(
        'ChTableHeader', parent=styles['Normal'],
        fontName=font_name, fontSize=10, leading=12, alignment=1
    )
    table_body_style = ParagraphStyle(
        'ChTableBody', parent=styles['Normal'],
        fontName=font_name, fontSize=10, leading=12, alignment=1
    )

    keys = list(data_dict.keys())
    for i, title in enumerate(keys):
        df = data_dict[title]
        
        # 標題
        elements.append(Paragraph(title, title_style))
        elements.append(Spacer(1, 12))
        
        # 列印時間
        elements.append(Paragraph(f"列印時間: {datetime.now().strftime('%Y-%m-%d %H:%M')}", normal_style))
        elements.append(Spacer(1, 12))
        
        # 表格
        header = [Paragraph(col, table_header_style) for col in df.columns]
        data = [header]
        for _, row in df.iterrows():
            data.append([Paragraph(str(item), table_body_style) for item in row])
        
        # 計算欄寬
        page_width = doc.width
        col_widths = [page_width / len(df.columns)] * len(df.columns)
        
        table = Table(data, colWidths=col_widths)
        table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
            ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
            ('TOPPADDING', (0, 0), (-1, -1), 4),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
        ]))
        elements.append(table)
        
        if i < len(keys) - 1:
            elements.append(PageBreak())

    doc.build(elements)
    return buffer.getvalue()

# ... (其餘所有函式和 Streamlit UI 程式碼完全複製貼上) ...
# (此處省略，請將您原始檔案中 generate_merged_pdf 之後的所有程式碼貼到這裡)

# --- (後半部分程式碼) ---

def create_batch_zip(data_dict, file_type="Excel"):
    zip_buffer = io.BytesIO()
    with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        for file_name, df in data_dict.items():
            if file_type == "Excel":
                excel_buffer = io.BytesIO()
                with pd.ExcelWriter(excel_buffer, engine=\'openpyxl\') as writer:
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
            "社團": [club], "報名時間": [get_taiwan_now().strftime(\'%Y-%m-%d %H:%M:%S\')],
            "狀態": ["正取"]
        })
        new_row.to_csv(REG_FILE, mode=\'a\', index=False, header=not os.path.exists(REG_FILE), encoding="utf-8-sig")
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
    st.markdown("<h3 style=\'color: red;\'>⚠️ 警告：破壞性操作</h3><p>將刪除所有名冊、報名與設定。</p>", unsafe_allow_html=True)
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
        blocks_html += f\'<div style="width:8px; height:12px; background-color:{color}; border-radius:2px; margin:1px;"></div>\'

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
    targets = set((r[\'班級\'], r[\'座號\']) for r in selected_rows)
    if action == "delete":
        new_df = current_df[~current_df.apply(lambda x: (x[\'班級\'], x[\'座號\']) in targets, axis=1)]
        new_df.to_csv(REG_FILE, index=False, encoding="utf-8-sig")
        st.toast(f"✅ 踢除 {len(selected_rows)} 人", icon="🗑️"); time.sleep(1); st.rerun()
    elif action == "move":
        c_limit = config_data["clubs"][target_club]["limit"]
        c_current = len(current_df[current_df["社團"] == target_club])
        if c_current + len(selected_rows) > c_limit: st.error("❌ 空間不足"); return
        new_df = current_df[~current_df.apply(lambda x: (x[\'班級\'], x[\'座號\']) in targets, axis=1)]
        new_records = [{"班級": r[\'班級\'], "座號": r[\'座號\'], "姓名": r[\'姓名\'], "社團": target_club, "報名時間": get_taiwan_now().strftime(\'%Y-%m-%d %H:%M:%S\'), "狀態": "正取"} for r in selected_rows]
        final_df = pd.concat([new_df, pd.DataFrame(new_records)], ignore_index=True)
        final_df.to_csv(REG_FILE, index=False, encoding="utf-8-sig")
        st.toast(f"✅ 轉移 {len(selected_rows)} 人", icon="🔄"); time.sleep(1); st.rerun()

def admin_batch_add(selected_rows, target_club):
    current_df = load_registrations()
    c_limit = config_data["clubs"][target_club]["limit"]
    c_current = len(current_df[current_df["社團"] == target_club])
    if c_current + len(selected_rows) > c_limit: st.error("❌ 空間不足"); return
    new_records = [{"班級": r[\'班級\'], "座號": r[\'座號\'], "姓名": r[\'姓名\'], "社團": target_club, "報名時間": get_taiwan_now().strftime(\'%Y-%m-%d %H:%M:%S\'), "狀態": "正取"} for r in selected_rows]
    final_df = pd.concat([current_df, pd.DataFrame(new_records)], ignore_index=True)
    final_df.to_csv(REG_FILE, index=False, encoding="utf-8-sig")
    st.toast("✅ 強制報名成功", icon="➕"); time.sleep(1); st.rerun()

def admin_batch_remove_students(selected_rows):
    all_std = load_students_with_identity()
    targets = set((r[\'班級\'], r[\'座號\']) for r in selected_rows)
    new_std = all_std[~all_std.apply(lambda x: (x[\'班級\'], x[\'座號\']) in targets, axis=1)]
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
    targets = set((r[\'班級\'], r[\'座號\']) for r in selected_rows)
    mask = all_std.apply(lambda x: (x[\'班級\'], x[\'座號\']) in targets, axis=1)
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
                m2.metric("正取", f"{len(df[df[\'狀態\']==\'正取\'])} 人")
                m3.metric("報名率", f"{int(len(df)/len(all_students_df)*100) if not all_students_df.empty else 0} %")

                with st.expander("📊 查看社團報名長條圖", expanded=False):
                    st.bar_chart(df[\'社團\'].value_counts())

                view_tabs = st.tabs(["🏆 依社團", "🏫 依班級", "⚠️ 未選社"])

                with view_tabs[0]:
                    clubs_list = sorted(df["社團"].unique())
                    if clubs_list:
                        selected_club_view = st.selectbox("選擇社團查看名單", clubs_list, key="club_view_selector")
                        if selected_club_view:
                            club_df = df[df["社團"] == selected_club_view].sort_values(by=["班級", "座號"])
                            st.dataframe(club_df, use_container_width=True, hide_index=True)

                with view_tabs[1]:
                    class_list = sorted(df["班級"].unique())
                    if class_list:
                        selected_class_view = st.selectbox("選擇班級查看名單", class_list, key="class_view_selector")
                        if selected_class_view:
                            class_df = df[df["班級"] == selected_class_view].sort_values(by=["座號"])
                            st.dataframe(class_df, use_container_width=True, hide_index=True)

                with view_tabs[2]:
                    registered_students = set(zip(df["班級"], df["座號"]))
                    all_students_set = set(zip(all_students_df["班級"], all_students_df["座號"]))
                    unregistered_students_set = all_students_set - registered_students
                    if unregistered_students_set:
                        unregistered_df = pd.DataFrame(list(unregistered_students_set), columns=["班級", "座號"])
                        unregistered_df = unregistered_df.merge(all_students_df[["班級", "座號", "姓名"]], on=["班級", "座號"], how="left").sort_values(by=["班級", "座號"])
                        st.dataframe(unregistered_df, use_container_width=True, hide_index=True)
                    else:
                        st.success("🎉 全校學生都已完成選社！")

            else:
                st.info("目前尚無任何報名資料")

        with tab_student:
            st.image(generate_step_image("👥", "學生管理"), use_container_width=True)
            all_std_df = load_students_with_identity()
            st.info(f"目前學生總數: {len(all_std_df)} 人")

            sub_tabs_std = st.tabs(["📋 學生名冊", "➕ 新增/轉班", "⬆️ 上傳名冊"])

            with sub_tabs_std[0]:
                st.dataframe(all_std_df, use_container_width=True, hide_index=True, key="student_list_df")
                selected_students_to_remove = st.session_state.get("student_list_df", {}).get("selection", {}).get("rows", [])
                if selected_students_to_remove:
                    selected_data = [all_std_df.iloc[i] for i in selected_students_to_remove]
                    st.warning(f"已選取 {len(selected_data)} 位學生")
                    if st.button("🗑️ 從名冊中移除選取學生", use_container_width=True):
                        admin_batch_remove_students(selected_data)

            with sub_tabs_std[1]:
                with st.form("add_student_form"):
                    st.subheader("➕ 手動新增學生")
                    c1, c2, c3, c4 = st.columns(4)
                    new_cls = c1.text_input("班級", max_chars=3)
                    new_seat = c2.text_input("座號", max_chars=2)
                    new_name = c3.text_input("姓名")
                    new_sid = c4.text_input("學號")
                    if st.form_submit_button("新增學生", use_container_width=True):
                        if new_cls and new_seat and new_name:
                            admin_add_student_manual(new_cls, new_seat.zfill(2), new_name, new_sid)
                        else: st.error("班級、座號、姓名為必填")
                st.divider()
                with st.form("transfer_student_form"):
                    st.subheader("🔄 學生轉班/改座號")
                    t1, t2, t3, t4 = st.columns(4)
                    old_cls = t1.text_input("原班級")
                    old_seat = t2.text_input("原座號")
                    new_cls_t = t3.text_input("新班級")
                    new_seat_t = t4.text_input("新座號")
                    if st.form_submit_button("執行轉班", use_container_width=True):
                        if old_cls and old_seat and new_cls_t and new_seat_t:
                            admin_transfer_student(old_cls, old_seat.zfill(2), new_cls_t, new_seat_t.zfill(2))
                        else: st.error("所有欄位皆為必填")

            with sub_tabs_std[2]:
                st.info("請上傳包含「班級、座號、姓名、學號、身分」欄位的 Excel 檔")
                uploaded_file = st.file_uploader("上傳學生名冊 Excel", type=["xlsx"])
                if uploaded_file:
                    try:
                        df_new = pd.read_excel(uploaded_file, dtype={"班級": str, "座號": str, "學號": str})
                        df_new["座號"] = df_new["座號"].apply(lambda x: str(x).zfill(2))
                        if "身分" not in df_new.columns: df_new["身分"] = "一般生"
                        df_new.to_excel(STUDENT_LIST_FILE, index=False)
                        st.success("✅ 名冊上傳成功！"); time.sleep(1); st.rerun()
                    except Exception as e: st.error(f"❌ 檔案讀取失敗: {e}")

        with tab_config:
            st.image(generate_step_image("⚙️", "系統設定"), use_container_width=True)
            with st.form("config_form"):
                st.subheader("⏰ 報名時間設定")
                c1, c2 = st.columns(2)
                start_time_str = c1.text_input("開始時間", value=config_data["start_time"])
                end_time_str = c2.text_input("結束時間", value=config_data["end_time"])
                st.subheader("🔑 管理員密碼")
                admin_pwd = st.text_input("新密碼 (留空不變)", type="password")
                st.subheader("🎈 社團設定")
                clubs_json = st.text_area("社團 JSON (請謹慎修改)", height=250, value=json.dumps(config_data["clubs"], ensure_ascii=False, indent=4))
                if st.form_submit_button("儲存設定", type="primary", use_container_width=True):
                    try:
                        new_clubs = json.loads(clubs_json)
                        config_data["clubs"] = new_clubs
                        config_data["start_time"] = start_time_str
                        config_data["end_time"] = end_time_str
                        if admin_pwd: config_data["admin_password"] = admin_pwd
                        save_config(config_data)
                        st.success("✅ 設定已儲存！"); time.sleep(1); st.rerun()
                    except json.JSONDecodeError: st.error("❌ 社團 JSON 格式錯誤")
            st.divider()
            st.subheader("💣 危險區域")
            c1, c2, c3 = st.columns(3)
            if c1.button("清空所有報名資料", use_container_width=True): confirm_clear_data()
            if c2.button("清空所有社團", use_container_width=True): confirm_clear_clubs()
            if c3.button("🚨 恢復原廠設定", use_container_width=True): confirm_factory_reset()

        with tab_export:
            st.image(generate_step_image("🖨️", "報表輸出"), use_container_width=True)
            reg_df = load_registrations()
            if reg_df.empty: st.warning("尚無報名資料可匯出"); st.stop()

            st.subheader("📄 依社團分頁")
            club_dfs = {club: df.sort_values(by=["班級", "座號"]) for club, df in reg_df.groupby("社團")}
            c1, c2 = st.columns(2)
            c1.download_button(
                label="📦 下載所有社團名單 (Excel)",
                data=create_batch_zip(club_dfs, "Excel"),
                file_name="社團名單_全部.zip",
                mime="application/zip",
                use_container_width=True
            )
            c2.download_button(
                label="📄 下載所有社團名單 (PDF)",
                data=generate_merged_pdf(club_dfs),
                file_name="社團名單_全部.pdf",
                mime="application/pdf",
                use_container_width=True
            )

            st.subheader("📄 依班級分頁")
            class_dfs = {f"{cls}班_名單": df.sort_values(by=["座號"]) for cls, df in reg_df.groupby("班級")}
            c1, c2 = st.columns(2)
            c1.download_button(
                label="📦 下載所有班級名單 (Excel)",
                data=create_batch_zip(class_dfs, "Excel"),
                file_name="班級名單_全部.zip",
                mime="application/zip",
                use_container_width=True
            )
            c2.download_button(
                label="📄 下載所有班級名單 (PDF)",
                data=generate_merged_pdf(class_dfs),
                file_name="班級名單_全部.pdf",
                mime="application/pdf",
                use_container_width=True
            )

            st.subheader("📄 全校總表")
            total_df = reg_df.sort_values(by=["班級", "座號"])
            c1, c2 = st.columns(2)
            excel_buffer = io.BytesIO()
            with pd.ExcelWriter(excel_buffer, engine=\'openpyxl\') as writer:
                total_df.to_excel(writer, index=False)
            c1.download_button(
                label="📥 下載全校總表 (Excel)",
                data=excel_buffer.getvalue(),
                file_name="全校報名總表.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True
            )
            c2.download_button(
                label="📥 下載全校總表 (PDF)",
                data=generate_merged_pdf({"全校報名總表": total_df}),
                file_name="全校報名總表.pdf",
                mime="application/pdf",
                use_container_width=True
            )

# ==========================================
# 4. 學生報名頁
# ==========================================
if page == "📝 學生報名":
    st.title("📝 頂級社團線上報名")
    now = get_taiwan_now()
    start_time = datetime.fromisoformat(config_data["start_time"]).astimezone(pytz.timezone("Asia/Taipei"))
    end_time = datetime.fromisoformat(config_data["end_time"]).astimezone(pytz.timezone("Asia/Taipei"))

    if now < start_time:
        st.warning(f"報名尚未開始！請於 {start_time.strftime(\'%Y-%m-%d %H:%M\')} 後再來。")
        st.stop()
    if now > end_time:
        st.error("報名已截止！")
        st.stop()

    if not st.session_state.id_verified:
        st.image(generate_step_image("1️⃣", "身分驗證"), use_container_width=True)
        students_df = load_students_with_identity()
        if students_df.empty: st.error("學生名冊尚未上傳，請洽管理員"); st.stop()

        with st.form("verify_form"):
            c1, c2, c3 = st.columns([1, 1, 2])
            sel_class = c1.selectbox("班級", sorted(students_df["班級"].unique()))
            sel_seat = c2.text_input("座號", max_chars=2)
            if st.form_submit_button("驗證身分", type="primary"):
                if sel_class and sel_seat:
                    sel_seat = sel_seat.zfill(2)
                    student = students_df[(students_df["班級"] == sel_class) & (students_df["座號"] == sel_seat)]
                    if not student.empty:
                        reg_df = load_registrations()
                        if not reg_df[(reg_df["班級"] == sel_class) & (reg_df["座號"] == sel_seat)].empty:
                            st.warning("⚠️ 您已經報名過了！如需修改請洽管理員。")
                        else:
                            st.session_state.id_verified = True
                            st.session_state.last_student = student.iloc[0]["姓名"]
                            st.session_state.student_info = student.iloc[0].to_dict()
                            st.rerun()
                    else: st.error("❌ 查無此學生資料")
                else: st.error("班級和座號為必填")
    else:
        st.image(generate_step_image("2️⃣", "選擇社團"), use_container_width=True)
        student_info = st.session_state.student_info
        st.success(f"你好，**{student_info[\'姓名\']}** 同學！")
        if st.button("返回重新驗證", use_container_width=True): st.session_state.id_verified = False; st.rerun()

        reg_df = load_registrations()
        club_counts = reg_df["社團"].value_counts().to_dict()

        categories = sorted(list(set(v.get("category", "未分類") for v in config_data["clubs"].values())))
        cat_tabs = st.tabs(categories)

        for i, category in enumerate(categories):
            with cat_tabs[i]:
                clubs_in_cat = {k: v for k, v in config_data["clubs"].items() if v.get("category", "未分類") == category}
                if not clubs_in_cat: st.info("此分類暫無社團"); continue

                cols = st.columns(3)
                col_idx = 0
                for club, details in sorted(clubs_in_cat.items()):
                    with cols[col_idx]:
                        limit = details["limit"]
                        current = club_counts.get(club, 0)
                        is_full = current >= limit

                        with st.container(border=True):
                            img_data = generate_text_image(club)
                            st.image(img_data, use_container_width=True)
                            st.markdown(render_health_bar(limit, current), unsafe_allow_html=True)
                            if st.button(f"選擇「{club}」", key=f"btn_{club}", use_container_width=True, disabled=is_full, type="primary"):
                                confirm_submission(student_info["班級"], student_info["座號"], student_info["姓名"], club)
                    col_idx = (col_idx + 1) % 3

# ==========================================
# 6. 查詢頁
# ==========================================
if page == "🔍 查詢報名":
    st.title("🔍 查詢我的報名結果")
    reg_df = load_registrations()
    q = st.text_input("輸入姓名搜尋", placeholder="按 Enter 查詢")
    if q:
        res = reg_df[reg_df["姓名"] == q]
        if not res.empty: st.table(res[["班級", "座號", "社團", "狀態"]])
        else: st.warning("查無資料")
