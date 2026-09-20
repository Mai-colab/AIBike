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
# 1. CẤU HÌNH GIAO DIỆN ULTRA-PREMIUM & CSS
# ==========================================
st.set_page_config(page_title="AIBike Luxury", layout="centered", page_icon="A")

st.markdown("""
    <style>
    /* Reset layout */
    .block-container { padding-top: 1rem !important; padding-bottom: 0rem !important; max-width: 480px !important; }
    header, #MainMenu, footer {visibility: hidden; display: none;}

    /* THEME ULTRA-LUXURY: Nền trắng ngà (Off-white), chữ Đen tuyền */
    .stApp { background-color: #FAFAFA !important; }

    /* Typography tối giản, sắc nét */
    .stTextInput label, .stRadio label, .stSelectbox label, .stCheckbox label, p, div[data-testid="stMarkdownContainer"] {
        color: #000000 !important; font-weight: 500 !important; letter-spacing: 0.3px;
    }

    /* Ô nhập liệu & Dropdown: Nền TRẮNG, viền ĐEN mỏng sắc sảo (Khắc phục lỗi màu xám/đen) */
    .stTextInput input, div[data-baseweb="select"] > div {
        background-color: #FFFFFF !important;
        color: #000000 !important;
        border: 1px solid #000000 !important;
        border-radius: 4px !important; /* Bo góc cực nhẹ, nam tính, sang trọng */
        box-shadow: none !important;
    }
    /* Ép cứng màu chữ trong Dropdown thành Đen */
    div[data-baseweb="select"] span, div[data-baseweb="select"] ul li { color: #000000 !important; }

    /* LOGO CÁCH ĐIỆU - ĐỈNH CAO LUXURY */
    .auth-card {
        background: #FFFFFF; border-radius: 8px; padding: 40px 20px;
        box-shadow: 0 10px 40px rgba(0,0,0,0.05); border: 1px solid #EAEAEA;
        text-align: center; margin-top: 2rem; margin-bottom: 2rem;
    }
    .auth-logo {
        background: #000000;
        color: #FFFFFF;
        width: 85px; height: 85px;
        border-radius: 50%; /* Đổi thành hình tròn */
        border: 2px solid #D4AF37; /* Viền màu vàng Gold chuẩn Luxury */
        display: flex; align-items: center; justify-content: center;
        margin: 0 auto 20px auto;
        font-size: 50px;
        font-family: 'Didot', 'Playfair Display', 'Times New Roman', serif; /* Font có chân sang chảnh */
        font-style: italic;
        box-shadow: 0 15px 30px rgba(0,0,0,0.15);
    }
    .auth-title { font-size: 28px; font-weight: 900; color: #000000; margin: 0; letter-spacing: 2px; text-transform: uppercase;}
    .auth-subtitle { font-size: 11px; color: #D4AF37; margin-bottom: 25px; text-transform: uppercase; letter-spacing: 3px; font-weight: bold;}

    /* Card thông tin - Minimalist */
    .info-card { background: #FFFFFF; border-radius: 4px; padding: 20px; margin: 15px 0; border: 1px solid #000000; color: #000000 !important;}
    .driver-card { background: #000000; border-radius: 4px; padding: 20px; margin: 15px 0; color: #FFFFFF !important; display: flex; align-items: center; gap: 20px; box-shadow: 0 10px 20px rgba(0,0,0,0.2);}
    .driver-card h3, .driver-card b, .driver-card p { color: #FFFFFF !important; }

    .vehicle-card { background: #FFFFFF; border-radius: 4px; padding: 18px; border: 1px solid #EAEAEA; margin-bottom: 12px; display: flex; justify-content: space-between; align-items: center; color: #000000 !important; transition: border 0.3s;}
    .vehicle-card:hover { border: 1px solid #000000; }
    .v-price { font-size: 20px; font-weight: 900; color: #000000; margin: 0; font-family: 'Times New Roman', serif;}

    /* NÚT BẤM BLACK & WHITE TỐI THƯỢNG (Khắc phục lỗi mất chữ hoàn toàn) */
    div.stButton > button:first-child {
        background-color: #000000 !important;
        border-radius: 4px !important;
        border: none !important;
        padding: 14px !important;
        width: 100% !important;
        transition: all 0.3s ease;
        box-shadow: 0 5px 15px rgba(0,0,0,0.1);
    }
    /* Ép cứng thẻ p bên trong nút bấm phải là màu TRẮNG */
    div.stButton > button:first-child p {
        color: #FFFFFF !important;
        font-weight: 700 !important;
        font-size: 14px !important;
        text-transform: uppercase !important;
        letter-spacing: 2px !important;
        margin: 0 !important;
    }
    div.stButton > button:first-child:hover { background-color: #333333 !important; transform: translateY(-2px);}

    /* Nút chọn chuyến (nhỏ hơn) */
    div[data-testid="stVerticalBlock"] div.stButton > button:first-child { padding: 8px !important; }

    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. KHỞI TẠO SESSION STATE
# ==========================================
if 'logged_in' not in st.session_state: st.session_state.logged_in = False
if 'user_email' not in st.session_state: st.session_state.user_email = ""
if 'searched' not in st.session_state: st.session_state.searched = False
if 'route_data' not in st.session_state: st.session_state.route_data = None
if 'chuyen_xe_da_chon' not in st.session_state: st.session_state.chuyen_xe_da_chon = None
if 'da_xac_nhan' not in st.session_state: st.session_state.da_xac_nhan = False

arc_geolocator = ArcGIS()

# ==========================================
# 3. GIAO DIỆN ĐĂNG NHẬP
# ==========================================
if not st.session_state.logged_in:
    st.markdown("""
        <div class='auth-card'>
            <div class='auth-logo'>A</div>
            <div class='auth-title'>AIBike</div>
            <div class='auth-subtitle'>Black Edition</div>
        </div>
    """, unsafe_allow_html=True)

    tab_login, tab_register = st.tabs(["ĐĂNG NHẬP", "ĐĂNG KÝ"])
    with tab_login:
        login_email = st.text_input("Email", placeholder="luxury.client@aibike.vn")
        login_pass = st.text_input("Mật khẩu", type="password", placeholder="••••••")
        st.write("")
        if st.button("Đăng nhập bằng Đặc quyền", key="btn_login"):
            st.session_state.logged_in = True
            st.rerun()

    with tab_register:
        st.info("Phiên bản giới hạn - Vui lòng liên hệ hỗ trợ để mở tài khoản.")
    st.stop()

# ==========================================
# 4. LOGIC TÍNH TOÁN
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
    if dist_km <= 2: return {"bike": 25000, "car4": 45000, "car7": 55000}[vehicle_type]
    if vehicle_type == "bike": return 25000 + ((dist_km - 2) * 8000)
    if vehicle_type == "car4": return 45000 + ((dist_km - 2) * 15000)
    if vehicle_type == "car7": return 55000 + ((dist_km - 2) * 18000)

# ==========================================
# 5. RENDER BẢN ĐỒ LUXURY (Line mỏng, tốc độ chậm)
# ==========================================
def render_map(coords=None, p_don=None, is_tracking=False, vehicle_id="bike"):
    map_height = 360
    map_url = "https://mt1.google.com/vt/lyrs=m&x={x}&y={y}&z={z}"

    if not coords:
        html = f"""
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <body style="margin:0; padding:0; overflow:hidden;">
            <div id="map" style="height:{map_height}px; width:100vw;"></div>
            <script>
                var map = L.map('map', {{zoomControl: false}}).setView([10.7769, 106.7009], 14);
                L.tileLayer('{map_url}').addTo(map);
            </script>
        </body>
        """
    else:
        emoji = "🚘" if "car" in vehicle_id else "🏍️"
        coords_json = json.dumps(coords)

        html = f"""
        <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css"/>
        <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
        <body style="margin:0; padding:0; overflow:hidden;">
            <div id="map" style="height:{map_height}px; width:100vw;"></div>
            <script>
                var map = L.map('map', {{zoomControl: false}}).setView([{p_don[0]}, {p_don[1]}], 15);
                L.tileLayer('{map_url}', {{maxZoom: 19}}).addTo(map);
                var coords = {coords_json};

                // LINE BẢN ĐỒ MỎNG, NHỎ, SANG TRỌNG (weight: 2.5, màu đen mờ)
                var polyline = L.polyline(coords, {{color: '#000000', weight: 2.5, opacity: 0.7, dashArray: '5, 5'}}).addTo(map);
                map.fitBounds(polyline.getBounds(), {{padding: [40, 40]}});

                // Chấm điểm đón/đến tinh tế
                L.circleMarker(coords[0], {{radius: 5, color: '#000', weight: 2, fillColor: '#FFF', fillOpacity: 1}}).addTo(map);
                L.circleMarker(coords[coords.length - 1], {{radius: 5, color: '#D4AF37', weight: 2, fillColor: '#000', fillOpacity: 1}}).addTo(map);

                if ('{is_tracking}' === 'True') {{
                    var vIcon = L.divIcon({{html: '<div style="font-size: 28px; filter: grayscale(100%); transform: translate(-10px, -14px);">{emoji}</div>', className: 'clear-class', iconSize: [0, 0]}});
                    var vMarker = L.marker(coords[0], {{icon: vIcon}}).addTo(map);

                    // TỐC ĐỘ DI CHUYỂN RẤT CHẬM (step = 1, interval = 250ms)
                    var i = 0, interval = 250, step = 1;
                    function animate() {{
                        if (i < coords.length - 1) {{
                            i += step;
                            if (i >= coords.length) i = coords.length - 1;
                            vMarker.setLatLng(coords[i]);
                            setTimeout(animate, interval);
                        }}
                    }}
                    setTimeout(animate, 800);
                }}
            </script>
        </body>
        """
    components.html(html, height=map_height, scrolling=False)

# ==========================================
# 6. LUỒNG GIAO DIỆN CHÍNH
# ==========================================
if not st.session_state.searched:
    render_map()
else:
    vid = st.session_state.chuyen_xe_da_chon['id'] if st.session_state.chuyen_xe_da_chon else "bike"
    render_map(st.session_state.route_data['coords'], st.session_state.route_data['p_don'], str(st.session_state.da_xac_nhan), vid)

with st.container():
    c_don, c_den = st.columns(2)
    with c_don: diem_don = st.text_input("ĐÓN TẠI", "Park Hyatt Saigon" if not st.session_state.searched else st.session_state.route_data['diem_don_hien_thi'])
    with c_den: diem_den = st.text_input("ĐẾN NƠI", "Landmark 81" if not st.session_state.searched else st.session_state.route_data['diem_den_hien_thi'])

    opt_choice = st.radio("DỊCH VỤ", ["Tiêu chuẩn", "Thương gia", "Tổng thống"], horizontal=True)

    c1, c2, c3 = st.columns(3)
    with c1: weather_ui = st.selectbox("THỜI TIẾT", ["☀️ Nắng đẹp", "🌧️ Mưa rào"])
    with c2: traffic_ui = st.slider("MẬT ĐỘ(%)", 0, 100, 15)
    with c3:
        st.write("")
        is_rush = st.checkbox("Giờ cao điểm")

if not st.session_state.da_xac_nhan:
    st.write("")
    if st.button("TÌM CHUYẾN XE", use_container_width=True):
        with st.spinner("Đang định vị vệ tinh..."):
            lat_don, lon_don, ad_don = get_detailed_location(diem_don)
            lat_den, lon_den, ad_den = get_detailed_location(diem_den)

            if lat_don and lat_den:
                coords_str = f"{lon_don},{lat_don};{lon_den},{lat_den}"
                url = f"http://router.project-osrm.org/route/v1/driving/{coords_str}?steps=true&geometries=polyline&overview=full"
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

if st.session_state.searched and st.session_state.route_data:
    data = st.session_state.route_data

    st.markdown(f"""
    <div class='info-card'>
        <div style='font-family:"Times New Roman", serif; font-size: 18px; margin-bottom:10px;'>HÀNH TRÌNH CỦA BẠN</div>
        <div style='font-size:13px; margin-bottom: 5px;'><b>Từ:</b> {data['ad_don']}</div>
        <div style='font-size:13px; margin-bottom: 15px;'><b>Đến:</b> {data['ad_den']}</div>
        <div style='font-size:12px; color:#666; text-transform:uppercase; letter-spacing:1px;'>Khoảng cách: {data['dist']:.1f} KM | Biến động giá: x{data['he_so_ai']:.1f}</div>
    </div>
    """, unsafe_allow_html=True)

    opt_mods = {"Tiêu chuẩn": 1.0, "Thương gia": 1.3, "Tổng thống": 2.0}
    hs_tong = data['he_so_ai'] * opt_mods[opt_choice]

    vehicles = [
        {"id": "bike", "name": "AIBike Signature", "desc": "Mô tô phân khối lớn", "price": round((get_base_price(data['dist'], "bike") * hs_tong) / 1000)},
        {"id": "car4", "name": "AICar Executive", "desc": "Sedan hạng sang (Mec, BMW)", "price": round((get_base_price(data['dist'], "car4") * hs_tong) / 1000)},
        {"id": "car7", "name": "AICar President", "desc": "SUV cỡ lớn bọc thép", "price": round((get_base_price(data['dist'], "car7") * hs_tong) / 1000)}
    ]

    if not st.session_state.chuyen_xe_da_chon:
        st.markdown("<p style='font-weight:700; letter-spacing:1px; font-size: 14px;'>HẠNG XE</p>", unsafe_allow_html=True)
        for v in vehicles:
            col_info, col_btn = st.columns([3, 1])
            with col_info:
                st.markdown(f"""
                <div class='vehicle-card'>
                    <div>
                        <p style='font-size: 15px; font-weight: 800; margin: 0;'>{v['name']}</p>
                        <p style='font-size: 12px; color: #666; margin: 0; font-style:italic;'>{v['desc']}</p>
                    </div>
                    <p class='v-price'>{v['price']}K</p>
                </div>
                """, unsafe_allow_html=True)
            with col_btn:
                st.write("")
                if st.button("CHỌN", key=f"btn_{v['id']}", use_container_width=True):
                    st.session_state.chuyen_xe_da_chon = v
                    st.rerun()

    else:
        xe = st.session_state.chuyen_xe_da_chon
        if not st.session_state.da_xac_nhan:
            st.markdown(f"<div class='info-card' style='text-align:center; background:#000; color:#FFF !important;'><p style='margin:0; font-size:12px; letter-spacing:2px; color:#D4AF37;'>TỔNG THANH TOÁN</p><h2 style='margin:5px 0; color:#FFF;'>{xe['price']}.000 VND</h2><p style='margin:0; font-size:12px;'>{xe['name']} - Thẻ tín dụng đen</p></div>", unsafe_allow_html=True)
            if st.button("YÊU CẦU XE", use_container_width=True):
                st.session_state.da_xac_nhan = True
                st.rerun()
        else:
            st.markdown(f"""
            <div class='driver-card'>
                <div style='font-size:50px; line-height:1; border-radius:50%; border:2px solid #D4AF37; padding:5px;'>🕴️</div>
                <div>
                    <h3 style='margin: 0; font-size: 13px; color:#D4AF37 !important; letter-spacing:2px; text-transform:uppercase;'>Tài xế riêng đang đến</h3>
                    <b style='font-size: 22px; font-family:"Times New Roman", serif;'>James Tran</b>
                    <p style='margin: 5px 0 0 0; font-size: 12px; color:#CCC !important;'>{xe['name']} • Biển số: 51H-999.99<br>⭐️ 5.0 (VVIP Chauffeur)</p>
                </div>
            </div>
            """, unsafe_allow_html=True)

            st.write("---")
            if st.button("HỦY YÊU CẦU", use_container_width=True):
                st.session_state.searched = False
                st.session_state.da_xac_nhan = False
                st.session_state.chuyen_xe_da_chon = None
                st.rerun()
