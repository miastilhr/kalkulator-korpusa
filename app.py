
import json, datetime, io, csv
import streamlit as st

st.set_page_config(page_title="Kalkulator korpusa – v27 (final)", page_icon="🧮", layout="wide")

# ==== Čitljivost: crno na bijelom + kompaktne, uokvirene KV tablice ====
st.markdown(
    """
    <style>
      :root { color-scheme: light only; }
      body, .stApp { background: #ffffff !important; color: #000 !important; }
      h1, h2, h3 { font-weight: 700; color: #000; }
      label, .stMarkdown, .stText, .stCaption, .stRadio, .stSelectbox, .stNumberInput { color: #000 !important; }
      /* prisilno crni font u svim streamlit tablicama */
      .stTable td, .stTable th, .stDataFrame td, .stDataFrame th { color: #000 !important; }
      /* naše key-value tablice */
      table.kv { width: 100%; border-collapse: collapse; font-size: 0.95rem; }
      table.kv th, table.kv td { border: 1px solid #d1d5db; padding: 6px 8px; }
      table.kv th { background: #f3f4f6; text-align: left; width: 55%; font-weight: 700; }
      table.kv td { text-align: right; width: 45%; font-variant-numeric: tabular-nums; }
      .kv-title { margin: 8px 0 2px; font-weight: 700; }
      .total { background: #eef7ee; font-weight: 800; }
      .warn { color: #b91c1c; font-weight: 700; }
      .muted { color: #374151; font-size: 0.9rem; }
    </style>
    """, unsafe_allow_html=True
)

@st.cache_resource
def load_cjenik():
    with open("cjenik.json", "r", encoding="utf-8") as f:
        return json.load(f)

def mm2_to_m2(mm2: float) -> float: return mm2 / 1_000_000.0
def mm_to_m(mm: float) -> float: return mm / 1000.0
def kant_length_mm_longshort(w, d, long_cnt:int, short_cnt:int):
    long_e = max(w, d); short_e = min(w, d)
    long_cnt = max(0, min(2, int(long_cnt))); short_cnt = max(0, min(2, int(short_cnt)))
    return long_cnt * long_e + short_cnt * short_e
def fmt_eur(x): return f"{x:,.2f} €".replace(",", " ").replace(".", ",")
def fmt_m(x): return f"{x:,.2f} m".replace(",", " ").replace(".", ",")
def fmt_m2(x): return f"{x:,.3f} m²".replace(",", " ").replace(".", ",")

CJE = load_cjenik()
MATS = {m["sifra"]: m for m in CJE.get("materijali", [])}
TRAK = {t["sifra"]: t for t in CJE.get("abs_trake", [])}
FRONTS = {m["sifra"]: m for m in CJE.get("materijali_fronta", [])}
FTRAK = {t["sifra"]: t for t in CJE.get("abs_trake_fronta", [])}
USLG = {u["sifra"]: u for u in CJE.get("usluge", [])}

st.title("🧮 Kalkulator korpusa – generalne → radne dimenzije (v27)")
st.caption("Final: crno na bijelom • KV tablice s okvirima • stabilan PDF export • spremno za Streamlit Cloud.")

# ---------- FORM ----------
with st.form("ulazi"):
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1: W = st.number_input("Širina W (mm)", min_value=1, value=800, step=10)
    with c2: H = st.number_input("Visina H (mm)", min_value=1, value=720, step=10)
    with c3: D = st.number_input("Dubina D (mm)", min_value=1, value=320, step=10)
    with c4: t = st.number_input("Debljina ploče t (mm)", min_value=1, value=18, step=1)
    with c5: n_police = st.number_input("Broj polica", min_value=0, value=2, step=1)

    cb1, cb2, cb3 = st.columns(3)
    with cb1: include_back = st.checkbox("Leđa (HDF) uključena", value=True)
    with cb2: pod_vrsta_vanjski = st.checkbox("Pod VANJSKI (preko stranica)", value=True)
    with cb3: kapa_vrsta_vanjska = st.checkbox("Kapa VANJSKA (preko stranica)", value=False)

    st.markdown("**Dodaci**")
    d1, d2, d3 = st.columns([2,2,3])
    with d1: include_kapa_povez = st.checkbox("Dodaj Kapa_povez", value=False)
    with d2: kapa_povez_mode = st.radio("Širina Kapa_povez", ["Fiksno (mm)", "% dubine"], horizontal=True)
    with d3:
        kapa_povez_sirina_mm = st.number_input("Kapa_povez – širina (mm)", min_value=1, value=150, step=1)
        kapa_povez_posto = st.slider("Kapa_povez – % dubine D", min_value=1, max_value=100, value=50)

    st.markdown("**Fronta (vrata)**")
    include_fronta = st.checkbox("Dodaj frontu", value=False)
    fronta_tip = st.selectbox("Tip fronte", ["Jednokrilna", "Dvokrilna"])
    fronta_montaza = st.selectbox("Montaža", ["Unutarnja (u korpusu)", "Vanjska (preko korpusa)"])
    f1, f2, f3 = st.columns(3)
    with f1: razmak_hor = st.number_input("Razmak horizontalno (mm)", min_value=0.0, value=2.0, step=0.5)
    with f2: razmak_ver = st.number_input("Razmak vertikalno (mm)", min_value=0.0, value=2.0, step=0.5)
    with f3: razmak_srednji = st.number_input("Srednji razmak (dvokrilna) (mm)", min_value=0.0, value=2.0, step=0.5)
    f4, f5 = st.columns(2)
    with f4: preklop_hor = st.number_input("Preklop horizontalno (mm)", min_value=0.0, value=0.0, step=0.5)
    with f5: preklop_ver = st.number_input("Preklop vertikalno (mm)", min_value=0.0, value=0.0, step=0.5)

    st.markdown("**Materijali i usluge**")
    m1, m2, m3, m4 = st.columns(4)
    with m1:
        default_mat = st.selectbox("Materijal korpusa", list(MATS.keys()),
            format_func=lambda k: f'{k} – {MATS[k]["naziv"]} ({MATS[k]["cijena_eur_po_m2"]:.2f} €/m²)')
    with m2:
        default_traka = st.selectbox("ABS traka korpusa", list(TRAK.keys()),
            format_func=lambda k: f'{k} – {TRAK[k]["naziv"]} ({TRAK[k]["cijena_eur_po_m"]:.2f} €/m)')
    with m3:
        default_mat_fr = st.selectbox("Materijal fronte", list(FRONTS.keys()),
            format_func=lambda k: f'{k} – {FRONTS[k]["naziv"]} ({FRONTS[k]["cijena_eur_po_m2"]:.2f} €/m²)')
    with m4:
        default_traka_fr = st.selectbox("ABS traka fronte", list(FTRAK.keys()),
            format_func=lambda k: f'{k} – {FTRAK[k]["naziv"]} ({FTRAK[k]["cijena_eur_po_m"]:.2f} €/m)')

    u1, u2 = st.columns(2)
    with u1:
        rez_keys = [k for k,v in USLG.items() if "cijena_eur_po_m" in v]
        rez_usl = st.selectbox("Usluga rezanja (€/m)", rez_keys,
            format_func=lambda k: f'{k} – {USLG[k]["naziv"]} ({USLG[k]["cijena_eur_po_m"]:.2f} €/m)')
    with u2:
        kant_keys = [k for k,v in USLG.items() if "cijena_eur_po_m" in v]
        kant_usl = st.selectbox("Usluga kantiranja (€/m)", kant_keys,
            format_func=lambda k: f'{k} – {USLG[k]["naziv"]} ({USLG[k]["cijena_eur_po_m"]:.2f} €/m)')

    st.markdown("**Radni sati**")
    r1, r2, r3 = st.columns(3)
    with r1:
        h_tp = st.number_input("Tehnička priprema – sati", min_value=0.0, value=0.5, step=0.25)
        r_tp = st.number_input("Cijena rada TP (€/h)", min_value=0.0, value=28.0, step=1.0)
    with r2:
        h_cnc = st.number_input("CNC i strojna obrada – sati", min_value=0.0, value=0.8, step=0.25)
        r_cnc = st.number_input("Cijena rada CNC (€/h)", min_value=0.0, value=35.0, step=1.0)
    with r3:
        h_skl = st.number_input("Sklapanje & montaža – sati", min_value=0.0, value=0.7, step=0.25)
        r_skl = st.number_input("Cijena rada SKL (€/h)", min_value=0.0, value=30.0, step=1.0)
    rp1, rp2 = st.columns(2)
    with rp1:
        h_pak = st.number_input("Pakiranje – sati", min_value=0.0, value=0.3, step=0.25)
    with rp2:
        r_pak = st.number_input("Cijena rada PAK (€/h)", min_value=0.0, value=22.0, step=1.0)

    st.markdown("**Opcije: otpad i marža**")
    o1, o2 = st.columns(2)
    with o1:
        use_waste = st.checkbox("Uključi otpad (%)", value=True)
        waste_pct = st.number_input("Postotak otpada (%)", min_value=0.0, value=8.0, step=0.5)
        st.caption("Otpad se računa na materijale i trake.")
    with o2:
        use_markup = st.checkbox("Uključi maržu (%)", value=False)
        markup_pct = st.number_input("Postotak marže (%)", min_value=0.0, value=15.0, step=0.5)
        st.caption("Marža se primjenjuje na samom kraju.")

    submit = st.form_submit_button("🧮  IZRAČUNAJ", use_container_width=True)

# --- funkcije ---
def validate_inputs(W,H,D,t, include_fronta, fronta_montaza, razmak_hor, razmak_ver, preklop_hor, preklop_ver):
    msgs = []
    inner_w = max(W - 2*t, 0)
    if include_fronta and fronta_montaza.startswith("Unutarnja"):
        if razmak_hor >= inner_w: msgs.append(("error", f"Razmak horizontalno ({razmak_hor} mm) ≥ unutarnja širina ({inner_w} mm)."))
        if razmak_ver >= H: msgs.append(("error", f"Razmak vertikalno ({razmak_ver} mm) ≥ visina ({H} mm)."))
    if include_fronta and fronta_montaza.startswith("Vanjska"):
        if preklop_hor > 2*D: msgs.append(("warning", f"Preklop horizontalno ({preklop_hor} mm) izgleda velik."))
        if preklop_ver > 6*t: msgs.append(("warning", f"Preklop vertikalno ({preklop_ver} mm) izgleda velik."))
    if D <= 0 or W <= 0 or H <= 0 or t <= 0:
        msgs.append(("error", "Dimenzije moraju biti veće od nule."))
    return msgs

def derive_rows(W,H,D,t,n_police, include_back, default_mat, default_traka, pod_vrsta_vanjski, kapa_vrsta_vanjska, include_kapa_povez, kapa_povez_mode, kapa_povez_sirina_mm, kapa_povez_posto, include_fronta, fronta_tip, fronta_montaza, razmak_hor, razmak_ver, razmak_srednji, preklop_hor, preklop_ver, default_mat_fr, default_traka_fr):
    inner_w = max(W - 2*t, 0)
    rows = []
    rows.append({"naziv":"Stranica", "mat": default_mat, "traka": default_traka, "A_mm":max(H - t, 1), "B_mm":D, "kom":2, "kant_dugi":1, "kant_kratki":1, "auto": True})
    kapa_w = W if kapa_vrsta_vanjska else inner_w
    rows.append({"naziv":"Kapa", "mat": default_mat, "traka": default_traka, "A_mm":kapa_w, "B_mm":D, "kom":1, "kant_dugi":1, "kant_kratki":0, "auto": False})
    pod_w = W if pod_vrsta_vanjski else inner_w
    rows.append({"naziv":"Pod", "mat": default_mat, "traka": default_traka, "A_mm":pod_w, "B_mm":D, "kom":1, "kant_dugi":1, "kant_kratki":1, "auto": True})
    if n_police > 0:
        pol_w = max(inner_w - 2, 1); pol_d = max(D - 10, 1)
        rows.append({"naziv":"Polica", "mat": default_mat, "traka": default_traka, "A_mm":pol_w, "B_mm":pol_d, "kom":int(n_police), "kant_dugi":2, "kant_kratki":2, "auto": True})
    if include_kapa_povez:
        width = int(round(D * (kapa_povez_posto / 100.0))) if kapa_povez_mode == "% dubine" else int(kapa_povez_sirina_mm)
        width = max(1, min(width, int(D)))
        rows.append({"naziv":"Kapa_povez", "mat": default_mat, "traka": default_traka, "A_mm":inner_w, "B_mm":width, "kom":1, "kant_dugi":1, "kant_kratki":0, "auto": False})
    if include_back:
        rows.append({"naziv":"Leđa (HDF)", "mat": "HDF-001", "traka": default_traka, "A_mm":max(W-2,1), "B_mm":max(H-2,1), "kom":1, "kant_dugi":0, "kant_kratki":0, "auto": False})
    if include_fronta:
        if fronta_montaza.startswith("Unutarnja"):
            target_w = max(inner_w - razmak_hor, 1); target_h = max(H - razmak_ver, 1)
        else:
            target_w = W + preklop_hor; target_h = H + preklop_ver
        if fronta_tip == "Jednokrilna":
            rows.append({"naziv":"Fronta", "mat": default_mat_fr, "traka": default_traka_fr, "A_mm":target_h, "B_mm":target_w, "kom":1, "kant_dugi":2, "kant_kratki":2, "auto": True})
        else:
            if fronta_montaza.startswith("Unutarnja"):
                ukupna_sirina = max(inner_w - razmak_hor, 1)
            else:
                ukupna_sirina = W + preklop_hor
            left_w = max((ukupna_sirina - razmak_srednji)/2.0, 1)
            rows.append({"naziv":"Fronta L", "mat": default_mat_fr, "traka": default_traka_fr, "A_mm":target_h, "B_mm":int(round(left_w)), "kom":1, "kant_dugi":2, "kant_kratki":2, "auto": True})
            rows.append({"naziv":"Fronta D", "mat": default_mat_fr, "traka": default_traka_fr, "A_mm":target_h, "B_mm":int(round(left_w)), "kom":1, "kant_dugi":2, "kant_kratki":2, "auto": True})
    return rows

def calculate(report_rows, rez_usl, kant_usl):
    rez_cij_m = USLG[rez_usl]["cijena_eur_po_m"]; kant_usl_cij_m = USLG[kant_usl]["cijena_eur_po_m"]
    total_area_m2 = total_rezanje_m = total_kant_m = 0.0
    cijena_mat_eur = cijena_kant_traka_eur = cijena_kant_usl_eur = cijena_rez_eur = 0.0
    iveral_area_m2 = iveral_eur = 0.0; hdf_area_m2 = hdf_eur = 0.0
    def rezanje_rule(A, B): return mm_to_m(max(A,B) + min(A,B))
    report = []
    for r in report_rows:
        A = float(r["A_mm"]); B = float(r["B_mm"]); k = int(r["kom"])
        rez_m_tot = rezanje_rule(A, B) * k
        naziv = str(r["naziv"]).lower(); auto = bool(r.get("auto", False))
        if auto and naziv.startswith("pod"): kant_mm_kom = A*1 + B*2
        elif auto and naziv.startswith("stranica"): kant_mm_kom = max(A,B) + min(A,B)
        elif auto and (naziv.startswith("polica") or naziv.startswith("fronta")): kant_mm_kom = 2*max(A,B) + 2*min(A,B)
        else: kant_mm_kom = kant_length_mm_longshort(A, B, int(r.get("kant_dugi",0)), int(r.get("kant_kratki",0)))
        kant_m_tot = mm_to_m(kant_mm_kom) * k; area_m2_tot = mm2_to_m2(A*B) * k
        mat_price = (MATS.get(r["mat"]) or FRONTS.get(r["mat"]) or {}).get("cijena_eur_po_m2", 0.0)
        traka_price = (TRAK.get(r["traka"]) or FTRAK.get(r["traka"]) or {}).get("cijena_eur_po_m", 0.0)
        mat_cij = mat_price * area_m2_tot; traka_cij = traka_price * kant_m_tot; rez_cij = rez_cij_m * rez_m_tot; kant_usl_e = kant_usl_cij_m * kant_m_tot
        if r["mat"] == "HDF-001": hdf_area_m2 += area_m2_tot; hdf_eur += mat_cij
        else: iveral_area_m2 += area_m2_tot; iveral_eur += mat_cij
        total_area_m2 += area_m2_tot; total_rezanje_m += rez_m_tot; total_kant_m += kant_m_tot
        cijena_mat_eur += mat_cij; cijena_kant_traka_eur += traka_cij; cijena_kant_usl_eur += kant_usl_e; cijena_rez_eur += rez_cij
        report.append({"Naziv": r["naziv"], "Mat": r["mat"], "Traka": r["traka"], "A (mm)": int(A), "B (mm)": int(B), "Kom": k,
                       "Kant m": round(kant_m_tot, 3), "Rezanje m": round(rez_m_tot, 3), "Površina m²": round(area_m2_tot, 3),
                       "€ Materijal": round(mat_cij, 2), "€ Traka": round(traka_cij, 2), "€ Usl. kant": round(kant_usl_e, 2),
                       "€ Rezanje": round(rez_cij, 2), "€ Element (ukupno)": round(mat_cij + traka_cij + rez_cij + kant_usl_e, 2)})
    metrics = dict(total_area_m2=total_area_m2, total_rezanje_m=total_rezanje_m, total_kant_m=total_kant_m,
                   cijena_mat_eur=cijena_mat_eur, cijena_kant_traka_eur=cijena_kant_traka_eur,
                   cijena_kant_usl_eur=cijena_kant_usl_eur, cijena_rez_eur=cijena_rez_eur,
                   iveral_area_m2=iveral_area_m2, iveral_eur=iveral_eur, hdf_area_m2=hdf_area_m2, hdf_eur=hdf_eur)
    return report, metrics

def kv_table(title, rows):
    html = ['<div class="kv-title">'+title+'</div><table class="kv">']
    for lab, val, *cls in rows:
        cls_attr = f' class="{cls[0]}"' if cls else ""
        html.append(f"<tr><th>{lab}</th><td{cls_attr}>{val}</td></tr>")
    html.append("</table>")
    st.markdown("\n".join(html), unsafe_allow_html=True)

def materials_services_summary(metrics, use_waste, waste_pct):
    eur_mats_total = metrics['cijena_mat_eur']
    eur_trake = metrics['cijena_kant_traka_eur']
    eur_rezanje = metrics['cijena_rez_eur']
    eur_kant_usl = metrics['cijena_kant_usl_eur']
    eur_waste = (waste_pct/100.0)*(eur_mats_total + eur_trake) if use_waste else 0.0
    subtotal = eur_mats_total + eur_trake + eur_rezanje + eur_kant_usl + eur_waste

    kv_table("📊 Materijal + usluge", [
        ("m² iveral", fmt_m2(metrics['iveral_area_m2'])),
        ("€ iveral", fmt_eur(metrics['iveral_eur'])),
        ("m² HDF", fmt_m2(metrics['hdf_area_m2'])),
        ("€ HDF", fmt_eur(metrics['hdf_eur'])),
        ("m² ukupno", fmt_m2(metrics['total_area_m2'])),
        ("€ materijal ukupno", fmt_eur(eur_mats_total)),
        ("Rezanje (m)", fmt_m(metrics['total_rezanje_m'])),
        ("€ rezanje", fmt_eur(eur_rezanje)),
        ("Kantiranje (m)", fmt_m(metrics['total_kant_m'])),
        ("€ trake", fmt_eur(eur_trake)),
        ("€ usluga kantiranja", fmt_eur(eur_kant_usl)),
        ("€ otpad", fmt_eur(eur_waste)),
        ("Materijal + usluge + otpad", fmt_eur(subtotal), "total"),
    ])
    return subtotal, eur_waste

def labor_summary(h_tp,r_tp,h_cnc,r_cnc,h_skl,r_skl,h_pak,r_pak):
    rows = [
        ("Tehnička priprema (h × €/h)", f"{h_tp:.2f} × {r_tp:.2f}"),
        ("€ TP", fmt_eur(h_tp*r_tp)),
        ("CNC i strojna obrada (h × €/h)", f"{h_cnc:.2f} × {r_cnc:.2f}"),
        ("€ CNC", fmt_eur(h_cnc*r_cnc)),
        ("Sklapanje i montaža (h × €/h)", f"{h_skl:.2f} × {r_skl:.2f}"),
        ("€ SKL", fmt_eur(h_skl*r_skl)),
        ("Pakiranje (h × €/h)", f"{h_pak:.2f} × {r_pak:.2f}"),
        ("€ PAK", fmt_eur(h_pak*r_pak)),
    ]
    total = h_tp*r_tp + h_cnc*r_cnc + h_skl*r_skl + h_pak*r_pak
    rows.append(("Rad ukupno", fmt_eur(total), "total"))
    kv_table("🛠️ Rad – obračun", rows)
    return total

def final_summary(mats_services_total, labor_total, use_markup, markup_pct):
    pre_markup = mats_services_total + labor_total
    eur_markup = (markup_pct/100.0)*pre_markup if use_markup else 0.0
    ukupno = pre_markup + eur_markup
    kv_table("🧾 Završni zbir", [
        ("Materijal + usluge + otpad", fmt_eur(mats_services_total)),
        ("Rad (sati × €/h)", fmt_eur(labor_total)),
        ("Zbroj (prije marže)", fmt_eur(pre_markup)),
        ("Marža", fmt_eur(eur_markup) + (f"  ({markup_pct:.1f} %)" if use_markup else "  (0 %)")),
        ("UKUPNO", fmt_eur(ukupno), "total"),
    ])

def export_section(report, metrics, labor_total, mats_services_total, markup_pct, use_markup, eur_waste):
    st.markdown("**📤 Izvoz**")
    timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
    # CSV
    csv_filename = f"izracun_{timestamp}.csv"; csv_buffer = io.StringIO()
    if report:
        fieldnames = list(report[0].keys())
        writer = csv.DictWriter(csv_buffer, fieldnames=fieldnames)
        writer.writeheader()
        for row in report: writer.writerow(row)
        writer.writerow({k: "" for k in fieldnames})
        writer.writerow({"Naziv":"--- MATERIJAL + USLUGE ---"})
        writer.writerow({"Naziv":"€ Materijal", "€ Element (ukupno)": f"{metrics['cijena_mat_eur']:.2f}"})
        writer.writerow({"Naziv":"€ Trake", "€ Element (ukupno)": f"{metrics['cijena_kant_traka_eur']:.2f}"})
        writer.writerow({"Naziv":"€ Usl. kant", "€ Element (ukupno)": f"{metrics['cijena_kant_usl_eur']:.2f}"})
        writer.writerow({"Naziv":"€ Rezanje", "€ Element (ukupno)": f"{metrics['cijena_rez_eur']:.2f}"})
        writer.writerow({"Naziv":"€ Otpad", "€ Element (ukupno)": f"{eur_waste:.2f}"})
        writer.writerow({"Naziv":"Materijal + usluge + otpad", "€ Element (ukupno)": f"{mats_services_total:.2f}"})
        writer.writerow({k: "" for k in fieldnames})
        writer.writerow({"Naziv":"--- RAD ---"})
        writer.writerow({"Naziv":"Rad ukupno", "€ Element (ukupno)": f'{labor_total:.2f}'})
        writer.writerow({k: "" for k in fieldnames})
        writer.writerow({"Naziv":"--- ZAVRŠNI ZBIR ---"})
        pre_markup = mats_services_total + labor_total
        writer.writerow({"Naziv":"Zbroj prije marže", "€ Element (ukupno)": f'{pre_markup:.2f}'})
        writer.writerow({"Naziv":"Marža", "€ Element (ukupno)": f'{(pre_markup*markup_pct/100.0 if use_markup else 0.0):.2f}'})
        writer.writerow({"Naziv":"UKUPNO", "€ Element (ukupno)": f'{(pre_markup*(1+markup_pct/100.0) if use_markup else pre_markup):.2f}'})

    st.download_button("⬇️ Izvoz u CSV", data=csv_buffer.getvalue().encode("utf-8"), file_name=csv_filename, mime="text/csv")

    # PDF – stable buffer handling
    pdf_filename = f"izracun_{timestamp}.pdf"
    pdf_bytes = None
    try:
        from reportlab.lib.pagesizes import A4
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
        from reportlab.lib.styles import getSampleStyleSheet
        from reportlab.lib import colors
        from reportlab.lib.units import mm

        buf = io.BytesIO()
        doc = SimpleDocTemplate(buf, pagesize=A4, leftMargin=12*mm, rightMargin=12*mm, topMargin=12*mm, bottomMargin=12*mm)
        styles = getSampleStyleSheet()
        elems = [Paragraph("Izračun korpusa – sažetak (v27)", styles["Title"]), Spacer(1,6)]

        # Materijal + usluge
        met = [
            ["m² iveral", f"{metrics['iveral_area_m2']:.3f}", "€ iveral", f"{metrics['iveral_eur']:.2f}"],
            ["m² HDF", f"{metrics['hdf_area_m2']:.3f}", "€ HDF", f"{metrics['hdf_eur']:.2f}"],
            ["m² ukupno", f"{metrics['total_area_m2']:.3f}", "€ materijal ukupno", f"{metrics['cijena_mat_eur']:.2f}"],
            ["Rezanje m", f"{metrics['total_rezanje_m']:.2f}", "€ rezanje", f"{metrics['cijena_rez_eur']:.2f}"],
            ["Kantiranje m", f"{metrics['total_kant_m']:.2f}", "€ trake", f"{metrics['cijena_kant_traka_eur']:.2f}"],
            ["", "", "€ usluga kantiranja", f"{metrics['cijena_kant_usl_eur']:.2f}"],
            ["", "", "€ otpad", f"{(mats_services_total - metrics['cijena_mat_eur'] - metrics['cijena_kant_traka_eur'] - metrics['cijena_rez_eur'] - metrics['cijena_kant_usl_eur']):.2f}"],
        ]
        t1 = Table(met, hAlign='LEFT', colWidths=[28*mm, 28*mm, 35*mm, 30*mm])
        t1.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.whitesmoke), ('GRID',(0,0),(-1,-1),0.4,colors.grey), ('ALIGN',(1,0),(-1,-1),'RIGHT'), ('FONT',(0,0),(-1,-1),'Helvetica',9)]))
        elems += [Paragraph("Materijal + usluge", styles["Heading3"]), t1, Spacer(1,8)]

        # Završni zbir
        pre_markup = mats_services_total + labor_total
        eur_markup = pre_markup*(markup_pct/100.0) if use_markup else 0.0
        ukupno = pre_markup + eur_markup
        frows = [["Stavka","€","Udio"]]
        frows.append(["Materijal + usluge + otpad", f"{mats_services_total:.2f}", f"{(mats_services_total/ukupno*100 if ukupno>0 else 0):.1f}%"])
        frows.append(["Rad", f"{labor_total:.2f}", f"{(labor_total/ukupno*100 if ukupno>0 else 0):.1f}%"])
        frows.append(["Marža", f"{eur_markup:.2f}", f"{(eur_markup/ukupno*100 if ukupno>0 else 0):.1f}%"])
        frows.append(["UKUPNO", f"{ukupno:.2f}", "100%"])
        t2 = Table(frows, hAlign='LEFT', colWidths=[60*mm, 30*mm, 25*mm])
        t2.setStyle(TableStyle([('GRID',(0,0),(-1,-1),0.25,colors.grey), ('FONT',(0,0),(-1,0),'Helvetica-Bold',10), ('FONT',(0,1),(-1,-1),'Helvetica',10), ('ALIGN',(1,1),(-1,-1),'RIGHT')]))
        elems += [Paragraph("Završni zbir", styles["Heading3"]), t2]

        doc.build(elems)
        pdf_bytes = buf.getvalue()  # do NOT close buf before reading
    except Exception as e:
        pdf_bytes = f"PDF izvoz nije dostupan: {e}".encode("utf-8")

    st.download_button("⬇️ Izvoz u PDF", data=pdf_bytes, file_name=pdf_filename, mime="application/pdf")

# ---------- RUN ----------
if submit:
    problems = validate_inputs(W,H,D,t, include_fronta=False, fronta_montaza="Unutarnja", razmak_hor=0, razmak_ver=0, preklop_hor=0, preklop_ver=0)
    for level, msg in problems:
        (st.error if level=="error" else st.warning)(msg)
    if any(level=="error" for level,_ in problems): st.stop()

    rows = derive_rows(W,H,D,t,n_police, include_back, default_mat, default_traka, pod_vrsta_vanjski, kapa_vrsta_vanjska,
                       include_kapa_povez, kapa_povez_mode, kapa_povez_sirina_mm, kapa_povez_posto,
                       include_fronta, fronta_tip, fronta_montaza, razmak_hor, razmak_ver, razmak_srednji, preklop_hor, preklop_ver,
                       default_mat_fr, default_traka_fr)

    st.subheader("📋 Radne dimenzije – auto pravila (uredivo)")
    edited = st.data_editor(rows, num_rows="dynamic", use_container_width=True,
                            column_config={
                                "A_mm": st.column_config.NumberColumn("Dim A (mm)", min_value=1, step=1),
                                "B_mm": st.column_config.NumberColumn("Dim B (mm)", min_value=1, step=1),
                                "kom": st.column_config.NumberColumn("Kom", min_value=1, step=1),
                                "kant_dugi": st.column_config.SelectboxColumn("Kant DUGI", options=[0,1,2]),
                                "kant_kratki": st.column_config.SelectboxColumn("Kant KRATKI", options=[0,1,2]),
                                "auto": st.column_config.CheckboxColumn("✔️ Auto pravilo"),
                                "mat": st.column_config.SelectboxColumn("Materijal", options=list(set(list(MATS.keys())+list(FRONTS.keys())))),
                                "traka": st.column_config.SelectboxColumn("ABS traka", options=list(set(list(TRAK.keys())+list(FTRAK.keys())))),
                            })

    st.subheader("🧾 Rezultati po elementu")
    report, metrics = calculate(edited, rez_usl, kant_usl)
    st.dataframe(report, use_container_width=True)

    mats_services_total, eur_waste = materials_services_summary(metrics, use_waste, waste_pct)
    labor_total = labor_summary(h_tp,r_tp,h_cnc,r_cnc,h_skl,r_skl,h_pak,r_pak)
    final_summary(mats_services_total, labor_total, use_markup, markup_pct)

    export_section(report, metrics, labor_total, mats_services_total, markup_pct, use_markup, eur_waste)

    st.success("✅ Izračun dovršen. KV tablice su uokvirene i lako čitljive. PDF export ispravan.")
