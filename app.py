import streamlit as st
import streamlit.components.v1 as components
import numpy as np
import skfuzzy as fuzz
from skfuzzy import control as ctrl
from geopy.geocoders import ArcGIS
import requests
import polyline
import json

# ==========================================
# 1. CẤU HÌNH GIAO DIỆN (Sửa triệt để lỗi Dark Mode & Khoảng trắng)
# ==========================================
st.set_page_config(page_title="AIBike Vietnam", layout="centered")

st.markdown("""
    <style>
    /* Reset lại margin/padding mặc định của Streamlit để xóa khoảng trắng */
    .block-container { padding-top: 0rem !important; padding-bottom: 0rem !important; max-width: 500px !important; }
    header, #MainMenu, footer {visibility: hidden; display: none;}
    
    /* ÉP MÀU CHỮ & NỀN CHO MỌI WIDGET (Chống lỗi tàng hình trên Dark Mode) */
    .stApp { background-color: #F4F6F8 !important; }
    .stTextInput label, .stRadio label, .stSelectbox label, .stCheckbox label, p, div[data-testid="stMarkdownContainer"] {
        color: #222222 !important; font-weight: 500 !important;
    }
    .stTextInput input, div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important; color: #000000 !important; border: 1px solid #CCCCCC !important; border-radius: 8px !important;
    }
    
    /* Header & Layout HTML Custom */
    .app-header { background: #00B14F; padding: 15px; color: white !important; text-align: center; font-size: 20px; font-weight: bold; margin: 0 -20px 0 -20px; z-index: 100; position: relative; box-shadow: 0 4px 6px rgba(0,0,0,0.1);}
    
    .info-card { background: #ffffff; border-radius: 12px; padding: 15px; margin: 15px 0; border: 1px solid #e0e0e0; box-shadow: 0 2px 8px rgba(0,0,0,0.05); color: #222 !important;}
    .driver-card { background: #E8F5E9; border-radius: 12px; padding: 15px; margin: 15px 0; border: 1px solid #A5D6A7; color: #222 !important; display: flex; align-items: center; gap: 15px;}
    
    .vehicle-card { background: #ffffff; border-radius: 12px; padding: 15px; border: 1.5px solid #e0e0e0; margin-bottom: 15px; display: flex; justify-content: space-between; align-items: center; color: #222 !important; box-shadow: 0 2px 5px rgba(0,0,0,0.04);}
    .v-price { font-size: 18px; font-weight: bold; color: #00B14F; margin: 0;}
    
    /* Nút bấm chuẩn xanh lá */
    div.stButton > button:first-child { background-color: #00B14F !important; color: white !important; border-radius: 8px !important; border: none !important; padding: 10px !important; font-weight: bold !important; font-size: 16px !important; width: 100% !important; transition: 0.2s;}
    div.stButton > button:first-child:hover { background-color: #008f3f !important; }
    
    /* List chỉ đường */
    .step-list { list-style: none; padding: 0; margin: 0; color: #222 !important;}
    .step-item { display: flex; margin-bottom: 12px; align-items: flex-start; border-bottom: 1px solid #f0f0f0; padding-bottom: 10px;}
    .step-icon { font-size: 18px; margin-right: 12px; width: 25px; text-align: center;}
    .step-dist { font-size: 12px; color: #777; display: block;}
    </style>
""", unsafe_allow_html=True)

# Khởi tạo Session State
if 'searched' not in st.session_state: st.session_state.searched = False
if 'route_data' not in st.session_state: st.session_state.route_data = None
if 'chuyen_xe_da_chon' not in st.session_state: st.session_state.chuyen_xe_da_chon = None
if 'da_xac_nhan' not in st.session_state: st.session_state.da_xac_nhan = False

arc_geolocator = ArcGIS()

# ==========================================
# 2. LOGIC TÍNH TOÁN (AI, Giá cả, Địa lý)
# ==========================================
def get_detailed_location(query):
    loc = arc_geolocator.geocode(query + ", Việt Nam")
    if loc:
        try:
            rev = arc_geolocator.reverse(f"{loc.latitude}, {loc.longitude}")
            if rev and rev.address: return loc.latitude, loc.longitude, rev.address
        except: pass
        return loc.latitude, loc.longitude, loc.address
    return None, None, None

def run_fuzzy_logic(thoi_tiet_val, giao_thong_val, is_rush_hour):
    thoi_tiet = ctrl.Antecedent(np.arange(0, 11, 1), 'Thời tiết')
    giao_thong = ctrl.Antecedent(np.arange(0, 101, 1), 'Giao thông')
    he_so = ctrl.Consequent(np.arange(1.0, 3.1, 0.1), 'Hệ số')

    thoi_tiet['Xấu'], thoi_tiet['Đẹp'] = fuzz.trimf(thoi_tiet.universe, [0, 0, 5]), fuzz.trimf(thoi_tiet.universe, [4, 10, 10])
    giao_thong['Thoáng'], giao_thong['Kẹt'] = fuzz.trimf(giao_thong.universe, [0, 0, 40]), fuzz.trimf(giao_thong.universe, [30, 100, 100])
    he_so['Bình thường'], he_so['Tăng'], he_so['Rất cao'] = fuzz.trimf(he_so.universe, [1.0, 1.0, 1.5]), fuzz.trimf(he_so.universe, [1.2, 1.8, 2.5]), fuzz.trimf(he_so.universe, [2.0, 3.0, 3.0])

    rule1 = ctrl.Rule(giao_thong['Thoáng'] & thoi_tiet['Đẹp'], he_so['Bình thường'])
    rule2 = ctrl.Rule(giao_thong['Kẹt'] | thoi_tiet['Xấu'], he_so['Tăng'])
    rule3 = ctrl.Rule(giao_thong['Kẹt'] & thoi_tiet['Xấu'], he_so['Rất cao'])

    sim = ctrl.ControlSystemSimulation(ctrl.ControlSystem([rule1, rule2, rule3]))
    sim.input['Thời tiết'], sim.input['Giao thông'] = thoi_tiet_val, giao_thong_val
    sim.compute()
    return sim.output['Hệ số'] + (0.2 if is_rush_hour else 0)

def get_base_price(dist_km, vehicle_type):
    if dist_km <= 2: return {"bike": 15000, "car4": 29000, "car7": 35000}[vehicle_type]
    if vehicle_type == "bike": return 15000 + ((dist_km - 2) * 5000 if dist_km <= 15 else (13 * 5000) + (dist_km - 15) * 4000)
    if vehicle_type == "car4": return 29000 + ((dist_km - 2) * 10000 if dist_km <= 15 else (13 * 10000) + (dist_km - 15) * 8000)
    if vehicle_type == "car7": return 35000 + ((dist_km - 2) * 12000 if dist_km <= 15 else (13 * 12000) + (dist_km - 15) * 10000)

def translate_maneuver(step):
    m = step['maneuver']
    t, mod, name = m['type'], m.get('modifier', 'straight'), step.get('name', '').strip()
    name_str = f"vào {name}" if name else "tiếp tục đi"
    if t == 'depart': return "🟢", f"Xuất phát {name_str}"
    if t == 'arrive': return "🔴", "Đến điểm đích"
    if t == 'roundabout': return "🔂", f"Đi vào vòng xuyến {name_str}"
    icon, action = "⬆️", "Đi thẳng"
    if 'left' in mod: icon, action = "⬅️", "Rẽ trái"
    elif 'right' in mod: icon, action = "➡️", "Rẽ phải"
    elif 'uturn' in mod: icon, action = "🔄", "Quay đầu"
    return icon, f"{action} {name_str}"

# ==========================================
# 3. RENDER BẢN ĐỒ (Ép chiều cao chính xác để xóa khoảng trắng)
# ==========================================
def render_map(coords=None, p_don=None, is_tracking=False, vehicle_id="bike"):
    # Đặt cố định chiều cao là 360px cho cả HTML div và Streamlit Iframe
    map_height = 360 
    
    if not coords:
        html = f"""
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <body style="margin:0; padding:0; overflow:hidden;">
            <div id="map" style="height:{map_height}px; width:100vw;"></div>
            <script>
                var map = L.map('map', {{zoomControl: false}}).setView([10.7769, 106.7009], 13);
                L.tileLayer('https://mt1.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}').addTo(map);
            </script>
        </body>
        """
    else:
        emoji = "🚗" if "car" in vehicle_id else "🛵"
        coords_json = json.dumps(coords)
        html = f"""
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <body style="margin:0; padding:0; overflow:hidden;">
            <div id="map" style="height:{map_height}px; width:100vw;"></div>
            <script>
                var map = L.map('map', {{zoomControl: false}}).setView([{p_don[0]}, {p_don[1]}], 14);
                L.tileLayer('https://mt1.google.com/vt/lyrs=m&x={{x}}&y={{y}}&z={{z}}', {{maxZoom: 19}}).addTo(map);
                var coords = {coords_json};
                var polyline = L.polyline(coords, {{color: '#00B14F', weight: 6, opacity: 0.9}}).addTo(map);
                map.fitBounds(polyline.getBounds(), {{padding: [30, 30]}});
                L.circleMarker(coords[0], {{radius: 7, color: 'white', weight: 2, fillColor: '#00B14F', fillOpacity: 1}}).addTo(map);
                L.circleMarker(coords[coords.length - 1], {{radius: 7, color: 'white', weight: 2, fillColor: '#FF3B30', fillOpacity: 1}}).addTo(map);
                if ('{is_tracking}' === 'True') {{
                    var vIcon = L.divIcon({{html: '<div style="font-size: 32px; filter: drop-shadow(0px 3px 3px rgba(0,0,0,0.4)); transform: translate(-12px, -16px);">{emoji}</div>', className: 'clear-class', iconSize: [0, 0]}});
                    var vMarker = L.marker(coords[0], {{icon: vIcon}}).addTo(map);
                    var i = 0, interval = 50, step = Math.max(1, Math.floor(coords.length / (10000 / interval)));
                    function animate() {{
                        if (i < coords.length - 1) {{
                            i += step;
                            if (i >= coords.length) i = coords.length - 1;
                            vMarker.setLatLng(coords[i]);
                            setTimeout(animate, interval);
                        }}
                    }}
                    setTimeout(animate, 500);
                }}
            </script>
        </body>
        """
    # Chiều cao iframe khớp đúng 360px, cuộn tắt
    components.html(html, height=map_height, scrolling=False) 

# ==========================================
# 4. LUỒNG GIAO DIỆN CHÍNH (Đầy đủ chức năng)
# ==========================================
st.markdown("<div class='app-header'>🟢 AIBike Vietnam</div>", unsafe_allow_html=True)

# Hiển thị Bản đồ
if not st.session_state.searched:
    render_map()
else:
  vid = st.session_state.chuyen_xe_da_chon['id'] if st.session_state.chuyen_xe_da_chon else "bike"
  render_map(st.session_state.route_data['coords'], st.session_state.route_data['p_don'], str(st.session_state.da_xac_nhan), vid)

# Container nhập liệu
with st.container():
    c_don, c_den = st.columns(2)
    with c_don: diem_don = st.text_input("📍 Đón tại", "Chợ Bến Thành" if not st.session_state.searched else st.session_state.route_data['diem_don_hien_thi'])
    with c_den: diem_den = st.text_input("🚩 Đến nơi", "Landmark 81" if not st.session_state.searched else st.session_state.route_data['diem_den_hien_thi'])

    opt_choice = st.radio("⭐ Lựa chọn tối ưu chuyến đi:", ["Tiết kiệm", "Nhanh", "An toàn", "Premium"], horizontal=True)

    c1, c2, c3 = st.columns(3)
    with c1: weather_ui = st.selectbox("Thời tiết", ["☀️ Nắng", "🌧️ Mưa"])
    with c2: traffic_ui = st.slider("Kẹt xe(%)", 0, 100, 20)
    with c3: 
        st.write("") 
        is_rush = st.checkbox("Giờ cao điểm")

# Nút Tìm kiếm
if not st.session_state.da_xac_nhan:
    st.write("") # Tạo khoảng cách nhỏ trước nút
    if st.button("🔍 TÌM CHUYẾN XE", use_container_width=True):
        with st.spinner("Đang định vị và tính toán AI..."):
            lat_don, lon_don, ad_don = get_detailed_location(diem_don)
            lat_den, lon_den, ad_den = get_detailed_location(diem_den)
            
            if lat_don and lat_den:
                url = f"http://router.project-osrm.org/route/v1/driving/{lon_don},{lat_don};{lon_den},{lat_den}?steps=true&geometries=polyline&overview=full"
                res = requests.get(url).json()
                if res.get('code') == 'Ok':
                    st.session_state.route_data = {
                        "dist": res['routes'][0]['distance'] / 1000,
                        "he_so_ai": run_fuzzy_logic(10 if "Nắng" in weather_ui else 4, traffic_ui, is_rush),
                        "coords": polyline.decode(res['routes'][0]['geometry']),
                        "p_don": [lat_don, lon_don], "p_den": [lat_den, lon_den],
                        "ad_don": ad_don, "ad_den": ad_den,
                        "diem_don_hien_thi": diem_don, "diem_den_hien_thi": diem_den,
                        "steps": res['routes'][0]['legs'][0]['steps']
                    }
                    st.session_state.searched = True
                    st.session_state.chuyen_xe_da_chon = None
                    st.rerun()

# Hiển thị Kết quả
if st.session_state.searched and st.session_state.route_data:
    data = st.session_state.route_data
    
    # 1. Thẻ hiển thị Địa chỉ & Tọa độ đầy đủ
    st.markdown(f"""
    <div class='info-card'>
        <div style='margin-bottom: 10px;'>
            <b>📍 Điểm đón:</b> <span style='font-size:14px; color:#555;'>{data['ad_don']}</span><br>
            <span style='font-size:12px; color:#888;'>Tọa độ: {data['p_don'][0]:.5f}, {data['p_don'][1]:.5f}</span>
        </div>
        <div>
            <b>🚩 Điểm đến:</b> <span style='font-size:14px; color:#555;'>{data['ad_den']}</span><br>
            <span style='font-size:12px; color:#888;'>Tọa độ: {data['p_den'][0]:.5f}, {data['p_den'][1]:.5f}</span>
        </div>
        <hr style='border-top:1px solid #eee; margin:10px 0;'>
        <div style='text-align:center;'>Quãng đường: <b>{data['dist']:.1f} km</b> • Hệ số giá AI: <b>x{data['he_so_ai']:.1f}</b></div>
    </div>
    """, unsafe_allow_html=True)
    
    opt_mods = {"Tiết kiệm": 0.85, "Nhanh": 1.0, "An toàn": 1.05, "Premium": 1.25}
    hs_tong = data['he_so_ai'] * opt_mods[opt_choice]
    
    vehicles = [
        {"id": "bike", "name": "🛵 AIBike", "cap": "1 khách", "price": round((get_base_price(data['dist'], "bike") * hs_tong) / 1000), "dur": max(3, int(((data['dist'] / 35) * 60) * hs_tong * 0.85))},
        {"id": "car4", "name": "🚗 AICar 4 Chỗ", "cap": "4 khách", "price": round((get_base_price(data['dist'], "car4") * hs_tong) / 1000), "dur": max(3, int(((data['dist'] / 45) * 60) * hs_tong))},
        {"id": "car7", "name": "🚙 AICar 7 Chỗ", "cap": "7 khách", "price": round((get_base_price(data['dist'], "car7") * hs_tong) / 1000), "dur": max(3, int(((data['dist'] / 40) * 60) * hs_tong))}
    ]
    
    # 2. Luồng chọn phương tiện
    if not st.session_state.chuyen_xe_da_chon:
        st.markdown("<h3 style='color:#333; margin-top:20px;'>Chọn Phương Tiện</h3>", unsafe_allow_html=True)
        for v in vehicles:
            col_info, col_btn = st.columns([3, 1])
            with col_info:
                st.markdown(f"""
                <div class='vehicle-card'>
                    <div>
                        <p style='font-size: 16px; font-weight: bold; margin: 0;'>{v['name']}</p>
                        <p style='font-size: 13px; color: #666; margin: 0;'>{v['cap']} • Ước tính: {v['dur']} phút</p>
                    </div>
                    <p class='v-price'>{v['price']}K</p>
                </div>
                """, unsafe_allow_html=True)
            with col_btn:
                st.write("") 
                if st.button("CHỌN", key=f"btn_{v['id']}", use_container_width=True):
                    st.session_state.chuyen_xe_da_chon = v
                    st.rerun()
                    
    # 3. Luồng Đặt xe & Đang theo dõi
    else:
        xe = st.session_state.chuyen_xe_da_chon
        if not st.session_state.da_xac_nhan:
            st.markdown(f"<div class='info-card' style='border: 2px solid #00B14F; text-align:center;'><h3 style='margin:0; color:#00B14F;'>Thanh toán: {xe['price']}.000 đ</h3><p style='margin:5px 0 0 0;'>Dịch vụ: {xe['name']} ({opt_choice})</p></div>", unsafe_allow_html=True)
            if st.button("✅ XÁC NHẬN ĐẶT XE", use_container_width=True):
              st.session_state.da_xac_nhan = True
              st.rerun()
        else:
            # Thẻ thông tin tài xế
            st.markdown(f"""
            <div class='driver-card'>
                <div style='font-size:55px; line-height:1;'>👨🏻‍✈️</div>
                <div>
                    <h3 style='margin: 0; color: #00B14F;'>Tài xế đang đến...</h3>
                    <b style='font-size: 18px;'>Trần Văn Đạt</b>
                    <p style='margin: 0; color: #444;'>{xe['name']} • Biển số: 59-H1 123.45<br>⭐️ 5.0 (1,250 chuyến)</p>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            # Thẻ Mũi tên chỉ đường chi tiết
            with st.expander("🗺️ LỘ TRÌNH CHỈ ĐƯỜNG CHI TIẾT (Bấm để xem)", expanded=False):
                html_steps = "<div class='info-card' style='box-shadow:none;'><ul class='step-list'>"
                for step in data['steps']:
                    dist_step = step['distance'] / 1000
                    icon, action = translate_maneuver(step)
                    html_steps += f"<li class='step-item'><div class='step-icon'>{icon}</div><div><span style='font-weight:600;'>{action}</span><span class='step-dist'>{dist_step:.2f} km</span></div></li>"
                html_steps += "</ul></div>"
                st.markdown(html_steps, unsafe_allow_html=True)
                
            st.write("---")
            if st.button("❌ Hủy chuyến / Đặt chuyến mới", use_container_width=True):
                st.session_state.searched = False
                st.session_state.da_xac_nhan = False
                st.session_state.chuyen_xe_da_chon = None
                st.rerun()
