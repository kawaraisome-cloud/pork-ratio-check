import streamlit as st
import cv2
import numpy as np
from PIL import Image
from datetime import datetime

def process_meat_ratio_adjustable(image, fat_threshold, sat_threshold):
    img = np.array(image)
    img = cv2.cvtColor(img, cv2.COLOR_RGB2BGR)
    
    # ย่อขนาดภาพเริ่มต้นให้เล็กลงอีกนิดเพื่อประหยัดที่
    height, width = img.shape[:2]
    if width > 700:
        new_w = 700
        new_h = int(height * (700 / width))
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

# CSS สำหรับบีบอัดพื้นที่ให้จบในหน้าเดียว
st.markdown("""
    <style>
    /* บีบ Padding หลักของหน้าเว็บ */
    .block-container { 
        padding-top: 1rem !important; 
        padding-bottom: 0rem !important; 
        max-width: 98% !important; 
    }
    /* ย่อหัวข้อหลัก */
    .main-title { 
        font-size: 1.5rem !important; 
        margin-bottom: 0.5rem !important; 
    }
    /* ปรับขนาดรูปภาพให้เล็กลงในโหมด Desktop และ Mobile */
    .stImage > img { 
        max-height: 220px !important; 
        object-fit: contain; 
        margin-bottom: -10px !important;
    }
    /* บีบส่วนข้อมูลสินค้า */
    .product-info { 
        font-size: 0.85rem !important; 
        padding: 8px !important; 
        margin-bottom: 5px !important; 
    }
    /* ลดระยะห่างระหว่างบรรทัด */
    div.stVerticalBlock { gap: 0.3rem !important; }
    /* ปรับแต่ง Metric ให้ตัวเล็กลงและชิดกัน */
    [data-testid="stMetricValue"] { font-size: 1.2rem !important; }
    /* ซ่อน Divider บางส่วนเพื่อประหยัดที่ */
    hr { margin: 0.2rem 0 !important; }
    h3 { font-size: 0.9rem !important; margin-top: 2px !important; }
    </style>
    """, unsafe_allow_html=True)

# Sidebar
st.sidebar.title("📱 มุมมอง")
view_mode = st.sidebar.radio("โหมด:", ("Desktop", "Mobile"))
fat_th = st.sidebar.slider("ความสว่าง", 50, 255, 125)
sat_th = st.sidebar.slider("ความจืด", 0, 255, 110)

# Main Title
st.markdown('<p class="main-title">🥩 เครื่องคำนวณสัดส่วนหมูบด</p>', unsafe_allow_html=True)

# ส่วนกรอกข้อมูลสินค้า (ย่อส่วน)
with st.expander("📝 บันทึกข้อมูลสินค้า", expanded=False):
    col_in1, col_in2 = st.columns(2)
    product_lot = col_in1.text_input("LOT", placeholder="รหัส LOT")
    product_name = col_in2.text_input("สินค้า", placeholder="ชื่อสินค้า")
    inspector = col_in1.text_input("ผู้ตรวจ", placeholder="ชื่อผู้ตรวจ")
    remark = col_in2.text_input("หมายเหตุ", placeholder="ระบุสั้นๆ")

uploaded_file = st.file_uploader("📸 เลือกรูปภาพ", type=["jpg", "jpeg", "png"], label_visibility="collapsed")

if uploaded_file is not None:
    image = Image.open(uploaded_file)
    with st.spinner('🔍 วิเคราะห์...'):
        red_p, fat_p, result_img, m_light, m_pale = process_meat_ratio_adjustable(image, fat_th, sat_th)

    # ข้อมูลการตรวจสอบแบบกระชับ
    st.markdown(f"""
    <div class="product-info" style="background-color: #f0f2f6; border-left: 5px solid red;">
        <b>LOT:</b> {product_lot if product_lot else '-'} | <b>สินค้า:</b> {product_name if product_name else '-'} | <b>ผู้ตรวจ:</b> {inspector if inspector else '-'} | <b>วันที่:</b> {datetime.now().strftime('%d/%m/%y %H:%M')}<br>
        <b>หมายเหตุ:</b> {remark if remark else '-'}
    </div>
    """, unsafe_allow_html=True)

    # Metrics สั้นๆ ในแถวเดียว
    m_col1, m_col2 = st.columns(2)
    m_col1.metric("🔴 เนื้อแดง", f"{red_p:.2f} %")
    m_col2.metric("⚪ มันหมู", f"{fat_p:.2f} %")

    if view_mode == "Desktop":
        col1, col2, col3 = st.columns(3)
        with col1:
            st.subheader("🖼️ 1.ต้นฉบับ")
            st.image(image, use_container_width=True)
        with col2:
            st.subheader("✅ 2.วิเคราะห์")
            st.image(result_img, use_container_width=True)
        with col3:
            st.subheader("🎭 3.Mask")
            sub_c1, sub_c2 = st.columns(2)
            sub_c1.image(m_light, use_container_width=True)
            sub_c2.image(m_pale, use_container_width=True)
    else:
        # โหมดมือถือบีบอัด: เอาภาพผลลัพธ์กับต้นฉบับมาวางคู่กัน (Side-by-Side) เพื่อลดความยาวหน้า
        c1, c2 = st.columns(2)
        with c1:
            st.subheader("✅ ผลวิเคราะห์")
            st.image(result_img, use_container_width=True)
        with c2:
            st.subheader("🖼️ ต้นฉบับ")
            st.image(image, use_container_width=True)
        
        with st.expander("🎭 ดู Mask"):
            st.image(m_light, use_container_width=True)
            st.image(m_pale, use_container_width=True)

else:
    st.info("💡 อัปโหลดรูปภาพ")
