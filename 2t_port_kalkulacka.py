import streamlit as st
import math
import matplotlib.pyplot as plt
import matplotlib.patches as patches
import pandas as pd

st.set_page_config(page_title="2T Port Kalkulačka", layout="wide")
st.title("🔧 Profesionálna 2T Motor Port Kalkulačka - Vylepšené vykreslenie")

# --- Sidebar ---
st.sidebar.header("🔧 Parametre Motora")
bore = st.sidebar.number_input("Priemer valca (mm)", 20.0, 120.0, 54.0)
stroke = st.sidebar.number_input("Zdvih (mm)", 20.0, 120.0, 54.0)
rod_length = st.sidebar.number_input("Dĺžka ojnice (mm)", 60.0, 160.0, 110.0)
rpm = st.sidebar.slider("Otáčky (RPM)", 1000, 18000, 9000, 100)
tdc = 0.0
bdc = stroke

port_descriptions = {
    "Výfuk": "Port výfuku umožňuje vypustenie spálených plynov z valca. Kľúčový pre správne časovanie a výkon motora.",
    "Pomocný výfuk": "Pomocný výfuk zlepšuje odvod spalín a môže pomôcť s výkonom pri vyšších otáčkach.",
    "Boost": "Boost porty zvyšujú prietok plniacej zmesi do valca, čím zvyšujú výkon a reakciu motora.",
    "Plniaci": "Plniace porty slúžia na nasávanie palivovej zmesi do valca a ovplyvňujú charakteristiku plnenia.",
    "Sací": "Sacie porty umožňujú prívod vzduchu alebo zmesi paliva do valca, dôležité pre efektívne spaľovanie."
}

available_ports = ["Výfuk", "Pomocný výfuk", "Boost", "Plniaci", "Sací"]
port_types = st.sidebar.multiselect("Zvoľ typy portov:", available_ports)

shape_descriptions = {
    "Obdĺžnik": "Obdĺžnikový tvar je jednoduchý a ľahko vyrobiteľný. Poskytuje stabilný a predvídateľný prietok, ideálny pre bežné aplikácie.",
    "Lichobežník": "Lichobežníkový tvar pomáha zlepšiť rozloženie prietoku a minimalizovať turbulencie, čo môže zlepšiť efektivitu plnenia valca.",
    "Oválny": "Oválny tvar zabezpečuje hladší prietok s menšími stratami, vhodný pre vysokootáčkové motory a lepšie plnenie."
}

for port in port_types:
    st.sidebar.markdown(f"**{port} port:** {port_descriptions.get(port, 'Popis nie je dostupný.')}")

def timing_from_height(h, stroke):
    try:
        theta_rad = math.acos(1 - (2 * h / stroke))
        angle_deg = math.degrees(theta_rad)
        return 180 - angle_deg, 180 + angle_deg, 2 * angle_deg
    except ValueError:
        return 0.0, 0.0, 0.0

def height_from_timing(timing, stroke):
    angle_rad = math.radians(timing / 2)
    h = (stroke / 2) * (1 - math.cos(angle_rad))
    return h

def rpm_from_duration(duration_deg, stroke):
    return int(1000000 / ((duration_deg / 360) * (stroke / 1000)))

def port_area(shape, width, height):
    if shape == "Obdĺžnik":
        return width * height
    elif shape == "Lichobežník":
        top_width = width * 0.6
        return (width + top_width) / 2 * height
    elif shape == "Oválny":
        return math.pi * (width / 2) * (height / 2)
    return 0

def draw_port(ax, y_pos, width, height, shape, bore, color='skyblue'):
    x_center = bore / 2
    x_left = x_center - width / 2

    if shape == "Obdĺžnik":
        rect = patches.Rectangle((x_left, y_pos), width, height, edgecolor='black', facecolor=color)
        ax.add_patch(rect)
    elif shape == "Lichobežník":
        top_width = width * 0.6
        verts = [(x_left, y_pos), 
                 (x_left + width, y_pos), 
                 (x_left + width - (width - top_width)/2, y_pos + height), 
                 (x_left + (width - top_width)/2, y_pos + height)]
        poly = patches.Polygon(verts, closed=True, edgecolor='black', facecolor=color)
        ax.add_patch(poly)
    elif shape == "Oválny":
        ellipse = patches.Ellipse((x_center, y_pos + height/2), width, height, edgecolor='black', facecolor=color)
        ax.add_patch(ellipse)

# --- Port inputs ---
st.header("🏛️ Parametre Portov")
port_inputs = {}
with st.form("port_input_form"):
    auto_calc = st.checkbox("🔄 Automaticky vypočítať porty na základe parametrov")

    for port in port_types:
        st.subheader(f"{port} port")
        col0, col1, col2, col3 = st.columns([1, 2, 3, 3])
        shape = col0.selectbox(f"Tvar portu - {port}", ["Obdĺžnik", "Lichobežník", "Oválny"], key=f"shape_{port}")
        col0.markdown(f"*{shape_descriptions[shape]}*")

        width = col1.number_input(f"Šírka (mm) - {port}", 5.0, bore * 1.5, 20.0, key=f"width_{port}")

        if not auto_calc:
            mode = col2.radio(f"Spôsob zadania - {port}", ["Z výšky", "Z časovania"], key=f"mode_{port}")
            if mode == "Z výšky":
                value = col3.number_input(f"Výška portu (mm) - {port}", 1.0, stroke, 30.0, key=f"val_{port}")
            else:
                value = col3.slider(f"Časovanie (krátke CA) - {port}", 90, 210, 180, key=f"val_{port}")
        else:
            duration_target = col2.slider(f"Cieľové trvanie časovania (CA) - {port}", 90, 210, 180, key=f"auto_duration_{port}")
            value = duration_target
            mode = "Z časovania"

        port_inputs[port] = {"mode": mode, "value": value, "width": width, "shape": shape}

    submitted = st.form_submit_button("✅ Vypočítať a vykresliť")

# --- Výpočet a vykreslenie ---
if submitted:
    st.subheader("📊 Výsledky a Schéma")

    results = []
    fig, ax = plt.subplots(figsize=(8, 12))

    # Vykreslenie valca
    cylinder_height = stroke
    cylinder_width = bore
    ax.add_patch(patches.Rectangle((0, 0), cylinder_width, cylinder_height, edgecolor='black', facecolor='#f0f0f0', lw=2))
    ax.text(cylinder_width / 2, cylinder_height + 5, "Valec", ha='center', fontsize=12)

    # Vykreslenie piesta na dolnej pozícii (BDC)
    piston_height = bore * 0.1
    piston_y = 0  # na spodku valca = BDC
    piston = patches.Rectangle((0, piston_y), cylinder_width, piston_height, edgecolor='red', facecolor='red', alpha=0.5)
    ax.add_patch(piston)
    ax.text(cylinder_width / 2, piston_y + piston_height + 2, "Piest", ha='center', color='red')

    # Kľuka a ojnica - vedľa valca
    crank_x = cylinder_width + 50
    crank_y = cylinder_height / 2

    # Kľuka - kruh
    crank_radius = stroke / 4
    crank_circle = patches.Circle((crank_x, crank_y), crank_radius, edgecolor='gray', facecolor='none', linestyle='--', lw=2)
    ax.add_patch(crank_circle)
    ax.text(crank_x, crank_y + crank_radius + 10, "Kľuka", ha='center', color='gray')

    # Ojnica - čiara od stredu kľuky smerom hore
    rod_angle_rad = math.radians(90)  # fixná poloha
    rod_length_scaled = rod_length / 10
    rod_end_x = crank_x + rod_length_scaled * math.cos(rod_angle_rad)
    rod_end_y = crank_y + rod_length_scaled * math.sin(rod_angle_rad)
    ax.plot([crank_x, rod_end_x], [crank_y, rod_end_y], 'r-', lw=3)
    ax.text(rod_end_x + 5, rod_end_y, "Ojnica", color='red')

    # Výpočet portov a ich vykreslenie na valci
    for idx, (port, params) in enumerate(port_inputs.items()):
        mode = params["mode"]
        val = params["value"]
        width = params["width"]
        shape = params["shape"]

        if mode == "Z výšky":
            h = val
            open_ca, close_ca, duration = timing_from_height(h, stroke)
        else:
            duration = val
            h = height_from_timing(duration, stroke)
            open_ca, close_ca, _ = timing_from_height(h, stroke)

        rpm_estimate = rpm_from_duration(duration, stroke)
        area = port_area(shape, width, h)

        results.append({
            "Port": port,
            "Tvar": shape,
            "Šírka (mm)": round(width, 2),
            "Výška (mm)": round(h, 2),
            "Otvorenie (°CA)": round(open_ca, 1),
            "Zatvorenie (°CA)": round(close_ca, 1),
            "Trvanie (°CA)": round(duration, 1),
            "Plocha (mm²)": round(area, 1),
            "Odhad RPM": rpm_estimate
        })

        # Vykreslenie portu na valci na správnej výške (y pozícia = h)
        draw_port(ax, h, width, piston_height, shape, bore, color='skyblue')
        ax.text(bore / 2, h + piston_height + 3, f"{port}\n{round(h,1)} mm", ha='center', fontsize=10)

    ax.set_xlim(-20, crank_x + rod_length_scaled + 30)
    ax.set_ylim(-10, cylinder_height + 50)
    ax.set_aspect('equal')
    ax.axis('off')

    st.pyplot(fig)

    df = pd.DataFrame(results)
    st.dataframe(df)

else:
    st.info("Vyber parametre a porty, potom klikni na 'Vypočítať a vykresliť'.")
