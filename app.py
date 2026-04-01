import streamlit as st
import cv2
import numpy as np
from PIL import Image
from datetime import datetime

def process_meat_ratio_adjustable(image, fat_threshold, sat_threshold):
    img = np.array(image)
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    
    # Resize เพื่อความรวดเร็ว
    height, width = img.shape[:2]
    if width > 800:
        new_w = 800
        new_h = int(height * (800 / width))
        img = cv2.resize(img, (new_w, new_h))

    filtered = cv2.bilateralFilter(img, 9, 75, 75)
    hsv = cv2.cvtColor(filtered, cv2.COLOR_BGR2HSV)
    gray = cv2.cvtColor(filtered, cv2.COLOR_BGR2GRAY)
    s_channel = hsv[:, :, 1]

    _, mask_pork = cv2.threshold(gray, 20, 255, cv2.THRESH_BINARY)
    mask_light = cv2.inRange(gray, fat_threshold, 255)
    mask_pale = cv2.inRange(s_channel, 0, sat_threshold)
    
    mask_fat_raw = cv2.bitwise_and(mask_light, mask_pale)
    mask_fat = cv2.bitwise_and(mask_fat_raw, mask_pork)

    kernel = np.ones((3, 3), np.uint8)
    mask_fat = cv2.morphologyEx(mask_fat, cv2.MORPH_OPEN, kernel)
    mask_red = cv2.bitwise_and(mask_pork, cv2.bitwise_not(mask_fat))

    total_pixels = cv2.countNonZero(mask_pork)
    fat_pixels = cv2.countNonZero(mask_fat)
    
    red_p = (np.float64(cv2.countNonZero(mask_red)) / total_pixels * 100) if total_pixels > 0 else 0
    fat_p = 100 - red_p if total_pixels > 0 else 0
    
    output_img = img.copy()
    overlay = img.copy()
    overlay[mask_red > 0] = [0, 0, 255]    
    overlay[mask_fat > 0] = [255, 255, 255] 
    cv2.addWeighted(overlay, 0.5, output_img, 0.5, 0, output_img)
    
    return red_p, fat_p, cv2.cvtColor(output_img, cv2.COLOR_BGR2RGB), mask_light, mask_pale

# --- UI Setup ---
st.set_page_config(page_title="Pork Ratio Pro", layout="wide")

# เพิ่ม Google Font และตั้งค่า CSS
st.markdown("""
    <style>
    /* 1. ดึงฟอนต์จาก Google Fonts (เลือก Sarabun หรือ Kanit ก็ได้) */
    @import url('https://fonts.googleapis.com/css2?family=Sarabun:wght@300;400;700&display=swap');

    /* 2. บังคับใช้ฟอนต์กับทุกส่วนของแอป */
    html, body, [class*="css"], .stMarkdown, p, div, h1, h2, h3, h4, h5, h6, span, label {
        font-family: 'Sarabun', sans-serif !important;
    }

    /* 3. ปรับจูนช่องว่าง (Compact Mode เดิม) */
    .block-container { 
        padding-top: 1.5rem !important; 
        padding-bottom: 0rem !important; 
        max-width: 96% !important; 
    }
    
    .main-title { 
        font-size: 1.8rem !important; 
        font-weight: 700;
        margin-bottom: 0.5rem !important; 
    }

    .stImage > img { 
        max-height: 240px !important; 
        object-fit: contain; 
        border-radius: 8px;
    }

    .product-info { 
        font-size: 0.9rem !important; 
        padding: 10px !important; 
        background-color: #f8f9fa;
        border-left: 5px solid #ff4b4b;
    }

    div.stVerticalBlock { gap: 0.4rem !important; }
    </style>
    """, unsafe_allow_html=True)

# Sidebar
st.sidebar.title("📱 มุมมอง")
view_mode = st.sidebar.radio("โหมดปัจจุบัน:", ("Desktop", "Mobile"))

st.sidebar.divider()
st.sidebar.header("⚙️ ตั้งค่าความแม่นยำ")
fat_th = st.sidebar.slider("ความสว่าง", 50, 255, 125)
sat_th = st.sidebar.slider("ความจืด", 0, 255, 110)

# Main Title
st.markdown('<p class="main-title">🥩 เครื่องคำนวณสัดส่วนหมูบด</p>', unsafe_allow_html=True)

# --- ส่วนกรอกข้อมูลสินค้า (เพิ่มใหม่) ---
with st.expander("📝 บันทึกข้อมูลสินค้า / LOT (คลิกเพื่อระบุรายละเอียด)", expanded=True):
    col_in1, col_in2, col_in3 = st.columns([1, 1, 1])
    product_lot = col_in1.text_input("หมายเลข LOT / รหัสสินค้า", placeholder="เช่น LOT-670327-01")
    product_name = col_in2.text_input("ชื่อสินค้า / ประเภท", placeholder="เช่น หมูบดเกรด A")
    remark = st.text_area("หมายเหตุเพิ่มเติม", placeholder="ระบุรายละเอียดอื่นๆ เช่น อุณหภูมิหน้างาน หรือแหล่งที่มา", height=70)

uploaded_file = st.file_uploader("📸 ถ่ายรูปหรือเลือกรูปหมู...", type=["jpg", "jpeg", "png"], accept_multiple_files=False)

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    
    with st.spinner('🔍 กำลังวิเคราะห์...'):
        red_p, fat_p, result_img, m_light, m_pale = process_meat_ratio_adjustable(image, fat_th, sat_th)

  # ---  st.divider()

    # --- ส่วนแสดงข้อมูลสินค้าในหน้าสรุปผล (เพื่อให้ติดไปตอนแคปจอ) ---
    st.markdown(f"""
    <div class="product-info">
        <b>ข้อมูลการตรวจสอบ</b><br>
        วันที่-เวลา: {datetime.now().strftime('%d/%m/%Y %H:%M')}<br>
        <b>LOT:</b> {product_lot if product_lot else '-'} | 
        <b>สินค้า:</b> {product_name if product_name else '-'} | 
        <b>หมายเหตุ:</b> {remark if remark else '-'}
    </div>
    """, unsafe_allow_html=True)

    # Metrics
    m_col1, m_col2 = st.columns(2)
    m_col1.metric("🔴 เนื้อแดง", f"{red_p:.2f} %")
    m_col2.metric("⚪ มันหมู", f"{fat_p:.2f} %")
    
   # ---  st.divider()

    if view_mode == "Desktop":
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("🖼️ 1. รูปต้นฉบับ")
            st.image(image, use_container_width=True)
        with col2:
            st.subheader("✅ 2. ผลวิเคราะห์")
            st.image(result_img, use_container_width=True)
        with col3:
            st.subheader("🎭 3. แยกสี (Mask)")
            sub_c1, sub_c2 = st.columns(2)
            sub_c1.image(m_light, caption="สว่าง", use_container_width=True)
            sub_c2.image(m_pale, caption="จืด", use_container_width=True)
    else:
        st.subheader("✅ ผลวิเคราะห์")
        st.image(result_img, use_container_width=True)
        st.subheader("🖼️ รูปต้นฉบับ")
        st.image(image, use_container_width=True)
        with st.expander("🎭 ดูรายละเอียด Mask"):
            st.image(m_light, caption="ความสว่าง", use_container_width=True)
            st.image(m_pale, caption="ความจืด", use_container_width=True)

else:
    st.info("💡 กรุณากรอกข้อมูลสินค้าและอัปโหลดรูปภาพเพื่อเริ่มต้น")
