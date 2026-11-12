"""GST JANO - Your Smart Guide to GST in India (Streamlit app)."""
import html
import os
from decimal import Decimal

import pandas as pd
import streamlit as st

import gst_data as gd
import gst_engine as ge
from i18n import tr

st.set_page_config(page_title="GST JANO", page_icon="🇮🇳", layout="wide",
                   initial_sidebar_state="collapsed")

PAGES = ["dashboard", "search", "calculator", "compare", "import_export", "verify", "payment"]
LOGO_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "logo.png")
PAYMENT_URL = "https://selfservice.gstsystem.in/Default.aspx"
VIDEO_URL = "https://www.youtube.com/watch?v=Bd4mOyVUsRY"
LINKS = {
    "CBIC GST rates": "https://cbic-gst.gov.in/gst-goods-services-rates.html",
    "GST Portal": "https://www.gst.gov.in/",
    "GSTIN search (GST Portal)": "https://services.gst.gov.in/services/searchtp",
    "GST notifications": "https://gst.gov.in/download/gstnotification",
    "GST Council": "https://gstcouncil.gov.in/",
    "ICEGATE (customs)": "https://www.icegate.gov.in/",
    "CBIC": "https://www.cbic.gov.in/",
}
RATE_OPTIONS = ["0", "0.25", "1", "1.5", "3", "5", "12", "18", "28", "40", "custom"]
COUNTRIES = ["China", "United States", "Germany", "Japan", "South Korea", "United Arab Emirates",
             "Singapore", "United Kingdom", "France", "Italy", "Vietnam", "Thailand", "Indonesia",
             "Malaysia", "Taiwan", "Russia", "Saudi Arabia", "Australia", "Other"]
CURRENCIES = ["INR", "USD", "EUR", "GBP", "AED", "CNY", "JPY", "SGD"]

ss = st.session_state


# ------------------------------------------------------------------ state
def init_state():
    if "init" in ss:
        return
    qp = st.query_params
    lang = qp.get("lang")
    ss.lang = lang if lang in ("en", "hi") else None
    ss.theme = qp.get("theme") if qp.get("theme") in ("dark", "light") else "dark"
    page = qp.get("page")
    if ss.lang is None:
        ss.page = "welcome"
    else:
        ss.page = page if page in PAGES else "dashboard"
    ss.init = True


def sync_qp():
    want = {"theme": ss.theme, "page": ss.page}
    if ss.lang:
        want["lang"] = ss.lang
    if dict(st.query_params) != want:
        st.query_params.from_dict(want)


CUR_LANG = "en"


def T(key, **kw):
    s = tr(key, CUR_LANG)
    return s.format(**kw) if kw else s


def go(page):
    ss.page = page


def set_lang():
    ss.lang = ss.lang_widget


def toggle_theme():
    ss.theme = "light" if ss.theme == "dark" else "dark"


# ------------------------------------------------------------------ data
def _stamp():
    a = os.path.getmtime(gd.DATA_FILE) if os.path.exists(gd.DATA_FILE) else 0
    b = os.path.getmtime(gd.CUSTOM_FILE) if os.path.exists(gd.CUSTOM_FILE) else 0
    return (a, b)


@st.cache_data(show_spinner=False)
def _load(stamp):
    return gd.load_data()


@st.cache_data(show_spinner=False)
def _load_headlines(stamp):
    return gd.load_headline_changes()


def get_df():
    return _load(_stamp())


@st.cache_data(show_spinner=False)
def _load_customs(stamp):
    return gd.load_customs()


def get_customs():
    return _load_customs(_stamp())


# ------------------------------------------------------------------ styling
CSS = """
<style>
:root{--bg:__BG__;--card:__CARD__;--card2:__CARD2__;--text:__TEXT__;--muted:__MUTED__;
--border:__BORDER__;--input:__INPUT__;--saffron:__SAF__;--green:__GRN__;--shadow:__SHADOW__;}
.stApp{background:__APPBG__;color:var(--text);}
[data-testid="stHeader"]{background:transparent;}
[data-testid="stToolbar"]{display:none;}
.block-container{padding-top:1rem;max-width:1220px;}
.stApp h1,.stApp h2,.stApp h3,.stApp h4,.stApp p,.stApp li,.stApp label,.stApp small,
.stApp [data-testid="stMarkdownContainer"],.stApp [data-testid="stCaptionContainer"]{color:var(--text)!important;}
.stApp [data-testid="stCaptionContainer"],.gj-muted{color:var(--muted)!important;}
.stApp a{color:var(--green)!important;}
.stApp input,.stApp textarea{background:var(--input)!important;color:var(--text)!important;
border:1px solid var(--border)!important;border-radius:10px!important;}
.stApp [data-baseweb="select"]>div{background:var(--input)!important;color:var(--text)!important;
border:1px solid var(--border)!important;border-radius:10px!important;}
.stApp [data-baseweb="select"] *{color:var(--text)!important;}
div[data-baseweb="popover"] ul,div[data-baseweb="popover"] div[role="listbox"]{background:var(--card)!important;}
div[data-baseweb="popover"] li,div[data-baseweb="popover"] li *{color:var(--text)!important;}
div[data-baseweb="popover"] li:hover{background:var(--card2)!important;}
.stApp .stButton button,.stApp .stDownloadButton button,.stApp [data-testid="stFormSubmitButton"] button,
.stApp [data-testid="stLinkButton"] a{background:var(--card)!important;color:var(--text)!important;
border:1px solid var(--border)!important;border-radius:10px!important;transition:all .15s;}
.stApp .stButton button p,.stApp .stDownloadButton button p,.stApp [data-testid="stFormSubmitButton"] button p,
.stApp [data-testid="stLinkButton"] a p{color:inherit!important;}
.stApp .stButton button:hover,.stApp .stDownloadButton button:hover,.stApp [data-testid="stLinkButton"] a:hover{
border-color:var(--saffron)!important;transform:translateY(-1px);}
.stApp button[data-testid="stBaseButton-primary"],.stApp button[data-testid="stBaseButton-primaryFormSubmit"]{
background:var(--saffron)!important;color:#fff!important;border:1px solid var(--saffron)!important;}
.stApp [class*="st-key-go_"] button{background:#2e8b3d!important;color:#fff!important;border:1px solid #2e8b3d!important;
font-weight:700;letter-spacing:.5px;}
[data-testid="stExpander"]{background:var(--card);border:1px solid var(--border)!important;border-radius:12px;}
[data-testid="stExpander"] summary,[data-testid="stExpander"] summary *{color:var(--text)!important;}
[data-testid="stAlert"]{background:var(--card2)!important;border:1px solid var(--border);border-radius:12px;}
[data-testid="stAlert"] *{color:var(--text)!important;}
[data-testid="stFileUploaderDropzone"]{background:var(--input)!important;border:1px dashed var(--border)!important;}
[data-testid="stFileUploaderDropzone"] *{color:var(--text)!important;}
button[data-baseweb="tab"] p{color:var(--muted)!important;font-weight:600;}
button[data-baseweb="tab"][aria-selected="true"] p{color:var(--saffron)!important;}
[data-baseweb="tab-highlight"]{background:var(--saffron)!important;}
.gj-stripe{height:4px;border-radius:4px;margin:.2rem 0 .8rem 0;
background:linear-gradient(90deg,var(--saffron) 0 33%,#e9e9e9 33% 66%,var(--green) 66% 100%);opacity:.8;}
.gj-brand{font-size:1.7rem;font-weight:800;letter-spacing:1px;color:var(--text);line-height:1.1;}
.gj-brand span{color:var(--saffron);}
.gj-tag{color:var(--muted);font-size:.85rem;margin-top:2px;}
.gj-card{background:var(--card);border:1px solid var(--border);border-radius:16px;padding:1.1rem 1.2rem;
box-shadow:var(--shadow);margin-bottom:.4rem;}
.gj-dcard{min-height:128px;border-top:4px solid var(--saffron);}
.gj-dcard.g{border-top-color:var(--green);}
.gj-dcard.w{border-top-color:#cfcfcf;}
.gj-dcard h4{margin:0 0 .35rem 0;font-size:1.08rem;}
.gj-dcard p{margin:0;font-size:.9rem;color:var(--muted)!important;}
.gj-hero{text-align:center;padding:1.3rem 0 .6rem 0;}
.gj-hero h1{font-size:2.3rem;margin:0;}
.gj-table-wrap{overflow-x:auto;border:1px solid var(--border);border-radius:12px;margin:.4rem 0 .8rem 0;}
table.gj-table{width:100%;border-collapse:collapse;font-size:.9rem;}
table.gj-table th{background:var(--card2);text-align:left;padding:.55rem .7rem;border-bottom:1px solid var(--border);
color:var(--text);white-space:nowrap;}
table.gj-table td{padding:.5rem .7rem;border-bottom:1px solid var(--border);color:var(--text);vertical-align:top;}
table.gj-table tr.strong td{font-weight:800;background:var(--card2);}
.gj-badge{display:inline-block;padding:.15rem .6rem;border-radius:999px;font-size:.78rem;font-weight:700;
border:1px solid var(--border);background:var(--card2);color:var(--text);}
.gj-up{color:#c0504d!important;font-weight:700;}.gj-down{color:#2e8b3d!important;font-weight:700;}
.gj-note{font-size:.82rem;color:var(--muted)!important;}
.st-key-nav_mobile{display:none;}
@media (max-width:900px){.st-key-nav_desktop{display:none!important;}.st-key-nav_mobile{display:block!important;}
.gj-hero h1{font-size:1.7rem;}}
</style>
"""
THEMES = {
    "dark": dict(BG="#1c1e22", CARD="#26292e", CARD2="#2f3338", TEXT="#ecebe6", MUTED="#a9a8a2",
                 BORDER="#3b4047", INPUT="#2b2f35", SAF="#c9863a", GRN="#5fae6b",
                 SHADOW="0 2px 8px rgba(0,0,0,.35)",
                 APPBG="linear-gradient(180deg,rgba(201,134,58,.10) 0%,#1c1e22 32%,#1c1e22 68%,rgba(95,174,107,.10) 100%)"),
    "light": dict(BG="#fbfaf7", CARD="#ffffff", CARD2="#f4f1ea", TEXT="#26282b", MUTED="#6a6c70",
                  BORDER="#e3dfd5", INPUT="#ffffff", SAF="#d98b3a", GRN="#2f8a43",
                  SHADOW="0 2px 10px rgba(60,50,30,.08)",
                  APPBG="linear-gradient(180deg,#fff1e0 0%,#ffffff 38%,#ffffff 62%,#e8f5e9 100%)"),
}


def apply_theme():
    css = CSS
    for k, v in THEMES[ss.theme].items():
        css = css.replace("__%s__" % k, v)
    st.markdown(css, unsafe_allow_html=True)


# ------------------------------------------------------------------ helpers
def esc(x):
    return html.escape(str(x))


def inr(x):
    return ge.fmt_inr(x)


def pct_str(rate_fraction):
    """0.18 -> '18', 0.0025 -> '0.25'."""
    d = Decimal(str(round(float(rate_fraction) * 100, 4))).normalize()
    s = format(d, "f")
    return s.rstrip("0").rstrip(".") if "." in s else s


def rate_label(r):
    return "—" if r is None or pd.isna(r) else pct_str(r) + "%"


def table_html(headers, rows, strong_last=False):
    h = "".join("<th>%s</th>" % esc(x) for x in headers)
    body = ""
    for i, r in enumerate(rows):
        cls = ' class="strong"' if (strong_last and i == len(rows) - 1) else ""
        body += "<tr%s>%s</tr>" % (cls, "".join("<td>%s</td>" % esc(c) for c in r))
    st.markdown('<div class="gj-table-wrap"><table class="gj-table"><thead><tr>%s</tr></thead><tbody>%s</tbody></table></div>'
                % (h, body), unsafe_allow_html=True)


def kv_table(rows, strong_last=True):
    table_html([T("col_item"), T("col_value")], rows, strong_last=strong_last)


def go_box(ctx):
    st.info(T("go_msg"))
    with st.container(key="go_%s" % ctx):
        st.button(T("go_btn"), key="gobtn_%s" % ctx, on_click=go, args=("payment",),
                  use_container_width=True)


def downloads(sheets, base, key):
    """sheets: dict name -> DataFrame. Real CSV + Excel files built from displayed results."""
    first = next(iter(sheets.values()))
    c1, c2, _ = st.columns([1, 1, 2])
    c1.download_button("⬇ " + T("dl_csv"), ge.to_csv_bytes(first), file_name=base + ".csv",
                       mime="text/csv", key="dlcsv_" + key, use_container_width=True)
    c2.download_button("⬇ " + T("dl_xlsx"), ge.to_xlsx_bytes(sheets), file_name=base + ".xlsx",
                       mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                       key="dlxlsx_" + key, use_container_width=True)


def err_msg(key):
    st.error(T(key))


def status_label(row):
    return T("st_" + row["status_key"])


# ------------------------------------------------------------------ chrome
def render_header():
    c1, c2, c3 = st.columns([4, 1.6, 1.1])
    with c1:
        if os.path.exists(LOGO_FILE):
            a, b = st.columns([1, 6])
            a.image(LOGO_FILE, width=56)
            b.markdown('<div class="gj-brand">GST <span>JANO</span></div><div class="gj-tag">%s</div>' % esc(T("tagline")),
                       unsafe_allow_html=True)
        else:
            st.markdown('<div class="gj-brand">🇮🇳 GST <span>JANO</span></div><div class="gj-tag">%s</div>' % esc(T("tagline")),
                        unsafe_allow_html=True)
    with c2:
        st.selectbox(T("language"), ["en", "hi"], index=["en", "hi"].index(ss.lang), key="lang_widget",
                     format_func=lambda x: "English" if x == "en" else "हिन्दी",
                     on_change=set_lang, label_visibility="collapsed")
    with c3:
        st.button("☀️ " + T("light") if ss.theme == "dark" else "🌙 " + T("dark"), key="theme_btn",
                  on_click=toggle_theme, use_container_width=True)
    st.markdown('<div class="gj-stripe"></div>', unsafe_allow_html=True)

    def nav_buttons(prefix):
        cols = st.columns(len(PAGES)) if prefix == "d" else [st.container() for _ in PAGES]
        for col, p in zip(cols, PAGES):
            with col:
                st.button(T("nav_" + p), key="nav_%s_%s" % (prefix, p), on_click=go, args=(p,),
                          type="primary" if ss.page == p else "secondary", use_container_width=True)

    with st.container(key="nav_desktop"):
        nav_buttons("d")
    with st.container(key="nav_mobile"):
        with st.expander("☰ " + T("menu")):
            nav_buttons("m")


# ------------------------------------------------------------------ pages
def page_welcome():
    st.markdown('<div class="gj-hero"><div style="font-size:3rem">🇮🇳</div><h1>GST JANO</h1>'
                '<p class="gj-muted">Your Smart Guide to GST in India<br>भारत में GST के लिए आपका स्मार्ट मार्गदर्शक</p></div>',
                unsafe_allow_html=True)
    if os.path.exists(LOGO_FILE):
        c = st.columns([2, 1, 2])[1]
        c.image(LOGO_FILE, use_container_width=True)
    st.markdown("<div style='text-align:center'>Welcome to GST JANO — please choose your language.<br>"
                "GST JANO में आपका स्वागत है — कृपया अपनी भाषा चुनें।</div>", unsafe_allow_html=True)
    c = st.columns([1, 1.2, 1])[1]
    with c:
        ss.setdefault("welcome_lang", "en")
        st.radio("Language / भाषा", ["en", "hi"], key="welcome_lang", horizontal=True,
                 format_func=lambda x: "English" if x == "en" else "हिन्दी")

        def cont():
            ss.lang = ss.welcome_lang
            ss.page = "dashboard"
        st.button("Continue / जारी रखें →", type="primary", on_click=cont, use_container_width=True, key="welcome_continue")


def start_search(query, page="search"):
    ss.search_q_input = query
    ss.page = page


def page_dashboard():
    df = get_df()
    st.markdown('<div class="gj-hero"><h1>%s</h1><p class="gj-muted">%s</p></div>'
                % (esc(T("dash_title")), esc(T("dash_sub"))), unsafe_allow_html=True)
    with st.form("dash_search"):
        c1, c2 = st.columns([6, 1.3])
        q = c1.text_input(T("search_label"), key="dash_q", placeholder=T("search_ph"), label_visibility="collapsed")
        sub = c2.form_submit_button("🔎 " + T("btn_search"), type="primary", use_container_width=True)
    if sub:
        if q.strip():
            start_search(q.strip())
            st.rerun()
        else:
            st.warning(T("enter_query"))
    cards = [("search", "🔎", "g"), ("calculator", "🧮", ""), ("compare", "⚖️", "w"),
             ("import_export", "🚢", "g"), ("verify", "🛡️", ""), ("payment", "💳", "w")]
    for row in (cards[:3], cards[3:]):
        cols = st.columns(3)
        for col, (p, icon, tone) in zip(cols, row):
            with col:
                st.markdown('<div class="gj-card gj-dcard %s"><h4>%s %s</h4><p>%s</p></div>'
                            % (tone, icon, esc(T("card_%s_t" % p)), esc(T("card_%s_d" % p))), unsafe_allow_html=True)
                st.button(T("open") + " →", key="card_" + p, on_click=go, args=(p,), use_container_width=True)
    n_goods = int((df["type"] == "Goods").sum())
    n_serv = int((df["type"] == "Service").sum())
    st.caption(T("dash_stats", n=len(df), g=n_goods, s=n_serv))
    st.caption(T("disclaimer"))


def render_detail(row):
    rate = row["rate"]
    st.markdown('<div class="gj-card">', unsafe_allow_html=True)
    st.markdown("### " + row["name"])
    badge = "%s · %s" % (status_label(row), T(row["cat_key"]))
    st.markdown('<span class="gj-badge">%s</span>' % esc(badge), unsafe_allow_html=True)
    rows = [(T("d_code"), row["code"] or "—"), (T("d_type"), row["type"])]
    if rate is not None and not pd.isna(rate) and row["status_key"] != "outside":
        rows.append((T("d_rate"), rate_label(rate)))
        rows.append((T("d_split"), "CGST %s + SGST/UTGST %s | IGST %s"
                     % (rate_label(rate / 2), rate_label(rate / 2), rate_label(rate))))
    else:
        rows.append((T("d_rate"), T("not_in_gst")))
    rows.append((T("d_status"), status_label(row)))
    rows.append((T("d_cat"), T(row["cat_key"])))
    old = row["old_rate"]
    if old is not None and not pd.isna(old):
        rows.append((T("d_old"), rate_label(old)))
        if row["change"] and row["change"] != "No change":
            rows.append((T("d_eff"), T("eff_changed", change=row["change"])))
        else:
            rows.append((T("d_eff"), T("eff_unchanged")))
    else:
        rows.append((T("d_eff"), T("eff_na")))
    rows.append((T("d_notes"), row["notes"] or "—"))
    rows.append((T("d_conf"), row["status"] or "—"))
    rows.append((T("d_src"), "%s (%s)" % (row["source"], row["id"])))
    kv_table(rows, strong_last=False)
    st.markdown("</div>", unsafe_allow_html=True)
    low = (row["status"] or "").lower()
    if "presumptive" in low or "verify" in low:
        st.warning(T("presumptive_warn"))
    return rows


def results_table(res, page_size, page_no):
    start = (page_no - 1) * page_size
    chunk = res.iloc[start:start + page_size]
    table_html([T("col_name"), T("col_code"), T("col_rate"), T("col_status")],
               [(r["name"][:140] + ("…" if len(r["name"]) > 140 else ""), r["code"][:40], rate_label(r["rate"]) if r["status_key"] != "outside" else "—",
                 status_label(r)) for _, r in chunk.iterrows()])
    return chunk


def clear_search():
    ss.search_q_input = ""


def calc_with(rate):
    ss.calc_rate = pct_str(rate) if pct_str(rate) in RATE_OPTIONS else "custom"
    if ss.calc_rate == "custom":
        ss.calc_custom = pct_str(rate)
    ss.page = "calculator"


def compare_with(name):
    ss.cmp_q_input = name[:60]
    ss.page = "compare"


def page_search():
    df = get_df()
    st.markdown("## 🔎 " + T("card_search_t"))
    ss.setdefault("search_q_input", "")
    with st.form("search_form"):
        c1, c2, c3 = st.columns([6, 1.3, 1.3])
        c1.text_input(T("search_label"), key="search_q_input", placeholder=T("search_ph"), label_visibility="collapsed")
        c2.form_submit_button("🔎 " + T("btn_search"), type="primary", use_container_width=True)
        c3.form_submit_button("✖ " + T("btn_clear"), on_click=clear_search, use_container_width=True)
    q = ss.search_q_input.strip()
    if not q:
        st.caption(T("try_examples"))
        cols = st.columns(5)
        for col, ex in zip(cols, ["Milk", "0401", "9983", "Toothpaste", "Hotel"]):
            col.button(ex, key="ex_" + ex, on_click=start_search, args=(ex, "search"), use_container_width=True)
    else:
        with st.spinner(T("loading")):
            res = gd.search(df, q)
        f1, f2, f3 = st.columns(3)
        typ = f1.selectbox(T("f_type"), ["all", "Goods", "Service"], format_func=lambda x: T("all") if x == "all" else T("type_" + x), key="f_type")
        rate_opts = ["all"] + [pct_str(r) for r in gd.VALID_CURRENT_RATES]
        rf = f2.selectbox(T("f_rate"), rate_opts, format_func=lambda x: T("all") if x == "all" else x + "%", key="f_rate")
        stf = f3.selectbox(T("f_status"), ["all", "applicable", "nil", "exempt", "nil_or_exempt", "outside"],
                           format_func=lambda x: T("all") if x == "all" else T("st_" + x), key="f_status")
        if typ != "all":
            res = res[res["type"].str.contains(typ)]
        if rf != "all":
            res = res[(res["rate"].notna()) & (res["rate"].round(6) == round(float(Decimal(rf) / 100), 6)) & (res["status_key"] != "outside")]
        if stf != "all":
            res = res[res["status_key"] == stf]
        if res.empty:
            st.warning(T("not_found"))
        else:
            st.success(T("n_results", n=len(res)))
            p1, p2 = st.columns(2)
            size = p1.selectbox(T("page_size"), [10, 25, 50, 100], index=1, key="s_size")
            pages = max(1, -(-len(res) // size))
            pg = p2.number_input(T("page_no", n=pages), min_value=1, max_value=pages, value=1, step=1, key="s_page")
            pg = min(int(pg), pages)
            chunk = results_table(res, size, pg)
            opts = list(chunk.index)
            pick = st.selectbox(T("select_result"), opts, key="s_pick",
                                format_func=lambda i: "%s — %s" % (df.loc[i, "name"][:90], df.loc[i, "code"][:25]))
            row = df.loc[pick]
            detail_rows = render_detail(row)
            b1, b2, b3 = st.columns(3)
            if row["rate"] is not None and not pd.isna(row["rate"]) and row["status_key"] != "outside":
                b1.button("🧮 " + T("use_in_calc"), key="to_calc", on_click=calc_with, args=(float(row["rate"]),), use_container_width=True)
            if row["old_rate"] is not None and not pd.isna(row["old_rate"]):
                b2.button("⚖️ " + T("see_compare"), key="to_cmp", on_click=compare_with, args=(row["name"],), use_container_width=True)
            full = res[["id", "type", "code", "name", "rate", "old_rate", "change", "status_key", "status", "notes", "source"]].copy()
            full.columns = ["ID", "Type", "HSN/SAC", "Name", "GST rate (IGST)", "Old rate", "Rate change", "GST status", "Rate confidence", "Notes", "Source"]
            for c in ("GST rate (IGST)", "Old rate"):
                full[c] = full[c].apply(lambda v: None if v is None or pd.isna(v) else round(float(v) * 100, 4))
            full = full.rename(columns={"GST rate (IGST)": "GST rate % (IGST)", "Old rate": "Old rate %"})
            downloads({"Search results": full}, "gst_jano_search_%s" % "".join(ch if ch.isalnum() else "_" for ch in q)[:30], "search")
            go_box("search")
    data_manager(df)


def admin_password():
    pw = os.environ.get("GSTJANO_ADMIN_PASSWORD")
    if pw:
        return pw
    try:
        return st.secrets.get("GSTJANO_ADMIN_PASSWORD")
    except Exception:
        return None


def data_manager(df):
    with st.expander("🛠 " + T("dm_title")):
        pw = admin_password()
        if not pw:
            st.info(T("dm_locked"))
            return
        entered = st.text_input(T("dm_pw"), type="password", key="dm_pw_in")
        if entered != pw:
            if entered:
                st.error(T("dm_wrong"))
            return
        up = st.file_uploader(T("dm_upload"), type=["xlsx", "csv"], key="dm_file")
        st.caption(T("dm_cols", cols=", ".join(gd.REQUIRED_COLS)))
        if up is None:
            return
        try:
            if up.name.lower().endswith(".csv"):
                raw = pd.read_csv(up, dtype=str, keep_default_na=False)
            else:
                xl = pd.ExcelFile(up)
                sheet = next((s for s in xl.sheet_names if s.strip().lower() == "gst rates"), xl.sheet_names[0])
                raw = pd.read_excel(xl, sheet, dtype=str, keep_default_na=False)
        except Exception as e:
            st.error(T("dm_unreadable", e=str(e)[:200]))
            return
        rep = gd.validate_upload(raw, df)
        st.write(T("dm_report", total=rep["total"], ok=len(rep["clean"]), dup=rep["duplicates"], bad=len(rep["errors"])))
        if rep["errors"]:
            table_html([T("dm_line"), T("dm_problem")], [(a, b) for a, b in rep["errors"][:50]])
        if len(rep["clean"]):
            if st.button(T("dm_apply", n=len(rep["clean"])), key="dm_apply", type="primary"):
                try:
                    before = len(gd.load_custom())
                    after = gd.save_custom(rep["clean"])
                    if after - before == len(rep["clean"]):
                        st.cache_data.clear()
                        st.success(T("dm_done", n=len(rep["clean"])))
                    else:
                        st.error(T("dm_fail"))
                except Exception as e:
                    st.error(T("dm_fail") + " " + str(e)[:150])
        elif not rep["errors"]:
            st.info(T("dm_nothing"))
        full = df[["id", "type", "code", "name", "rate", "old_rate", "change", "status", "notes", "source"]]
        st.download_button("⬇ " + T("dm_dl_all"), ge.to_xlsx_bytes({"GST database": full}), file_name="gst_jano_database.xlsx",
                           mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", key="dm_dl")


# ---- calculator
def reset_calc():
    ss.calc_amount = "1000"
    ss.calc_mode = "add"
    ss.calc_rate = "18"
    ss.calc_custom = ""
    ss.calc_supply = "intra"


def page_calculator():
    st.markdown("## 🧮 " + T("card_calculator_t"))
    for k, v in dict(calc_amount="1000", calc_mode="add", calc_rate="18", calc_custom="", calc_supply="intra").items():
        ss.setdefault(k, v)
    c1, c2 = st.columns(2)
    with c1:
        st.text_input(T("c_amount"), key="calc_amount", help=T("c_amount_help"))
        st.radio(T("c_mode"), ["add", "remove"], key="calc_mode", format_func=lambda x: T("c_mode_" + x))
    with c2:
        st.selectbox(T("c_rate"), RATE_OPTIONS, key="calc_rate",
                     format_func=lambda x: T("custom_rate") if x == "custom" else x + "%")
        if ss.calc_rate == "custom":
            st.text_input(T("c_custom"), key="calc_custom")
        st.radio(T("c_supply"), ["intra", "ut", "inter"], key="calc_supply", format_func=lambda x: T("c_supply_" + x))
    st.button("↺ " + T("btn_reset"), key="calc_reset", on_click=reset_calc)
    st.caption(T("c_hint"))
    amount, err = ge.parse_amount(ss.calc_amount)
    if err:
        err_msg(err)
        return
    if ss.calc_rate == "custom":
        rate, err = ge.parse_percent(ss.calc_custom)
        if err:
            err_msg(err)
            return
    else:
        rate = Decimal(ss.calc_rate)
    r = ge.calc_gst(amount, rate, ss.calc_mode, ss.calc_supply)
    rows = [(T("r_original"), inr(r["original"])), (T("r_rate"), ge.fmt_pct(r["rate"]))]
    if r["mode"] == "remove":
        rows.append((T("r_taxable"), inr(r["taxable"])))
    if r["supply"] == "inter":
        rows.append(("IGST", inr(r["igst"])))
    else:
        rows.append(("CGST (%s)" % ge.fmt_pct(r["rate"] / 2), inr(r["cgst"])))
        if r["supply"] == "ut":
            rows.append(("UTGST (%s)" % ge.fmt_pct(r["rate"] / 2), inr(r["utgst"])))
        else:
            rows.append(("SGST (%s)" % ge.fmt_pct(r["rate"] / 2), inr(r["sgst"])))
    rows.append((T("r_total_gst"), inr(r["tax"])))
    if r["mode"] == "add":
        rows.append((T("r_taxable"), inr(r["taxable"])))
    rows.append((T("r_final"), inr(r["total"])))
    kv_table(rows)
    if rate in (Decimal("12"), Decimal("28")):
        st.warning(T("c_old_slab"))
    rep = pd.DataFrame({"Item": [a for a, _ in rows], "Value": [b for _, b in rows]})
    meta = pd.DataFrame({"Item": [T("c_mode"), T("c_supply")], "Value": [T("c_mode_" + r["mode"]), T("c_supply_" + r["supply"])]})
    downloads({"GST breakdown": pd.concat([meta, rep], ignore_index=True)}, "gst_jano_calculation", "calc")
    go_box("calc")


# ---- compare
def clear_cmp():
    ss.cmp_q_input = ""


def page_compare():
    df = get_df()
    st.markdown("## ⚖️ " + T("card_compare_t"))
    t1, t2 = st.tabs([T("cmp_tab_item"), T("cmp_tab_head")])
    with t1:
        ss.setdefault("cmp_q_input", "")
        ss.setdefault("cmp_amount", "10000")
        with st.form("cmp_form"):
            a, b, c = st.columns([6, 1.3, 1.3])
            a.text_input(T("search_label"), key="cmp_q_input", placeholder=T("search_ph"), label_visibility="collapsed")
            b.form_submit_button("🔎 " + T("btn_search"), type="primary", use_container_width=True)
            c.form_submit_button("✖ " + T("btn_clear"), on_click=clear_cmp, use_container_width=True)
        q = ss.cmp_q_input.strip()
        base = df[df["old_rate"].notna() & df["rate"].notna() & (df["source"] != "Everyday Items")]
        if not q:
            st.info(T("cmp_hint"))
        else:
            res = gd.search(base, q)
            f1, f2 = st.columns(2)
            direction = f1.selectbox(T("f_change"), ["all", "up", "down", "same"],
                                     format_func=lambda x: T("all") if x == "all" else T("dir_" + x), key="cmp_dir")
            typ = f2.selectbox(T("f_type"), ["all", "Goods", "Service"],
                               format_func=lambda x: T("all") if x == "all" else T("type_" + x), key="cmp_type")
            if typ != "all":
                res = res[res["type"] == typ]
            if direction == "up":
                res = res[res["rate"] > res["old_rate"] + 1e-9]
            elif direction == "down":
                res = res[res["rate"] < res["old_rate"] - 1e-9]
            elif direction == "same":
                res = res[(res["rate"] - res["old_rate"]).abs() <= 1e-9]
            if res.empty:
                st.warning(T("not_found"))
            else:
                st.success(T("n_results", n=len(res)))
                show = res.head(100)
                table_html([T("col_name"), T("col_code"), T("col_old"), T("col_new"), T("col_dir")],
                           [(r["name"][:110], r["code"][:30], rate_label(r["old_rate"]), rate_label(r["rate"]), dir_text(r))
                            for _, r in show.iterrows()])
                if len(res) > 100:
                    st.caption(T("showing_100"))
                pick = st.selectbox(T("select_result"), list(show.index), key="cmp_pick",
                                    format_func=lambda i: "%s — %s" % (df.loc[i, "name"][:90], df.loc[i, "code"][:25]))
                row = df.loc[pick]
                st.text_input(T("cmp_amount"), key="cmp_amount", help=T("c_amount_help"))
                amt, err = ge.parse_amount(ss.cmp_amount)
                if err:
                    err_msg(err)
                else:
                    old_r = Decimal(str(round(row["old_rate"] * 100, 4)))
                    new_r = Decimal(str(round(row["rate"] * 100, 4)))
                    o = ge.calc_gst(amt, old_r, "add", "inter")
                    n = ge.calc_gst(amt, new_r, "add", "inter")
                    diff_tax = n["tax"] - o["tax"]
                    diff_tot = n["total"] - o["total"]
                    changed = row["change"] and row["change"] != "No change"
                    rows = [
                        (T("cmp_item"), row["name"][:120]), (T("col_code"), row["code"]),
                        (T("cmp_prev_rate"), ge.fmt_pct(old_r) + (" — " + T("cmp_until") if changed else "")),
                        (T("cmp_new_rate"), ge.fmt_pct(new_r) + (" — " + T("cmp_from") if changed else "")),
                        (T("cmp_taxable"), inr(o["taxable"])),
                        (T("cmp_prev_gst"), inr(o["tax"])), (T("cmp_new_gst"), inr(n["tax"])),
                        (T("cmp_diff_gst"), ("+" if diff_tax > 0 else "") + inr(diff_tax)),
                        (T("cmp_prev_total"), inr(o["total"])), (T("cmp_new_total"), inr(n["total"])),
                        (T("cmp_diff_total"), ("+" if diff_tot > 0 else "") + inr(diff_tot)),
                        (T("col_dir"), dir_text(row)),
                    ]
                    kv_table(rows, strong_last=False)
                    if diff_tax > 0:
                        st.markdown('<span class="gj-up">▲ %s</span>' % esc(T("dir_up")), unsafe_allow_html=True)
                    elif diff_tax < 0:
                        st.markdown('<span class="gj-down">▼ %s</span>' % esc(T("dir_down")), unsafe_allow_html=True)
                    else:
                        st.markdown("● " + T("dir_same"))
                    low = (row["status"] or "").lower()
                    if "presumptive" in low:
                        st.warning(T("presumptive_warn"))
                    rep = pd.DataFrame({"Item": [a for a, _ in rows], "Value": [b for _, b in rows]})
                    allres = res[["id", "type", "code", "name", "old_rate", "rate", "change", "status"]].copy()
                    allres["old_rate"] = (allres["old_rate"] * 100).round(4)
                    allres["rate"] = (allres["rate"] * 100).round(4)
                    allres.columns = ["ID", "Type", "HSN/SAC", "Name", "Old rate %", "New rate %", "Rate change", "Rate confidence"]
                    downloads({"Comparison": rep, "All matches": allres}, "gst_jano_old_vs_new", "cmp")
                    go_box("cmp")
    with t2:
        hd = _load_headlines(_stamp())
        d = st.selectbox(T("f_change"), ["all", "REDUCED", "INCREASED"],
                         format_func=lambda x: T("all") if x == "all" else T("dir_down" if x == "REDUCED" else "dir_up"), key="head_dir")
        if d != "all":
            hd = hd[hd["Direction"] == d]
        table_html([T("col_dir"), T("cmp_item"), T("col_old"), T("col_new"), T("pp")],
                   [(T("dir_down") if r["Direction"] == "REDUCED" else T("dir_up"), r["Category / Item"],
                     rate_label(r["Old GST"]), rate_label(r["New GST"]), "%+.0f" % r["Change (pp)"]) for _, r in hd.iterrows()])
        st.caption(T("head_src"))
        out = hd.copy()
        out["Old GST"] = (out["Old GST"] * 100).round(2)
        out["New GST"] = (out["New GST"] * 100).round(2)
        downloads({"Headline changes": out}, "gst_jano_headline_changes", "head")


def dir_text(r):
    diff = r["rate"] - r["old_rate"]
    if diff > 1e-9:
        return "▲ " + T("dir_up")
    if diff < -1e-9:
        return "▼ " + T("dir_down")
    return "● " + T("dir_same")


# ---- import / export
def pick_rate_cb(prefix):
    i = ss.get(prefix + "_pick", -1)
    if i == -1:
        return
    row = get_df().loc[i]
    if row["rate"] is not None and not pd.isna(row["rate"]) and row["status_key"] != "outside":
        ss[prefix + "_igst"] = pct_str(row["rate"])
    toks = gd.code_tokens(row["code"])
    if toks:
        ss[prefix + "_hsn"] = toks[0]
    if not ss.get(prefix + "_desc"):
        ss[prefix + "_desc"] = row["name"][:100]


def lookup_block(prefix):
    df = get_df()
    ss.setdefault(prefix + "_q", "")
    ss.setdefault(prefix + "_pick", -1)
    with st.form(prefix + "_lookup"):
        a, b = st.columns([6, 1.5])
        a.text_input(T("ie_lookup"), key=prefix + "_q", placeholder=T("search_ph"))
        b.write("")
        b.write("")
        b.form_submit_button("🔎 " + T("btn_search"), use_container_width=True)
    q = ss[prefix + "_q"].strip()
    if q:
        res = gd.search(df, q, limit=30)
        if res.empty:
            st.warning(T("not_found"))
        else:
            opts = [-1] + list(res.index)
            st.selectbox(T("select_result"), opts, key=prefix + "_pick", on_change=pick_rate_cb, args=(prefix,),
                         format_func=lambda i: "—" if i == -1 else "%s — %s — %s" % (df.loc[i, "name"][:70], df.loc[i, "code"][:20], rate_label(df.loc[i, "rate"]) if df.loc[i, "status_key"] != "outside" else T("not_in_gst")))


def page_import_export():
    st.markdown("## 🚢 " + T("card_import_export_t"))
    t1, t2 = st.tabs([T("ie_tab_import"), T("ie_tab_export")])
    with t1:
        tab_import()
    with t2:
        tab_export()


def pick_customs_cb():
    i = ss.get("imp_cpick", -1)
    if i == -1:
        return
    r = get_customs()["df"].loc[i]["rate"]
    if r["kind"] == "nil":
        ss.imp_bcd = "0"
        ss.imp_other = "0"
    elif r["kind"] == "adval":
        ss.imp_bcd = r["pct"]
        ss.imp_other = r["aidc"] or "0"
    elif r["kind"] == "higher":
        ss.imp_bcd = r["pct"]
        ss.imp_other = "0"
    elif r["kind"] == "specific":
        ss.imp_other = "0"
        ss.imp_qty = "1"


def customs_block():
    """Customs-duty lookup against the workbook's 'Custom duty' sheet. Returns (row or None, bcd_rule or None)."""
    cu = get_customs()
    st.markdown("**%s**" % T("cu_title"))
    if cu["error"]:
        st.info(T("cu_missing_sheet") if cu["error"] == "no_sheet" else T("cu_bad_sheet"))
        return None, None
    cdf = cu["df"]
    st.caption(T("cu_loaded", n=len(cdf)))
    for note in cu["notes"]:
        st.caption(T("cu_note", text=note))
    st.text_input(T("cu_query"), key="imp_cq")
    q = ss.imp_cq.strip() or ss.imp_hsn.strip()
    if not q:
        return None, None
    res = gd.search_customs(cdf, q)
    if res.empty:
        st.info(T("cu_none"))
        return None, None
    st.success(T("cu_found", n=len(res)))
    st.caption(T("cu_legend"))
    opts = [-1] + list(res.index)
    icons = {"code": "✔", "range": "✔", "related": "≈", "text": "🔤"}

    def fmt(i):
        if i == -1:
            return T("cu_manual")
        r = res.loc[i]
        return "%s %s — %s — %s" % (icons[r["match"]], r["product"][:70], r["hsn"][:30], r["rate_raw"])
    st.selectbox(T("cu_select"), opts, key="imp_cpick", on_change=pick_customs_cb, format_func=fmt)
    pick = ss.imp_cpick
    if pick == -1 or pick not in opts:
        return None, None
    row = cdf.loc[pick]
    r = row["rate"]
    rule = None
    if r["kind"] in ("specific", "higher"):
        rule = {"kind": r["kind"], "amount": Decimal(r["amount"]), "unit": r["unit"]}
        if r["kind"] == "specific":
            st.info(T("cu_specific", amt=r["amount"], unit=r["unit"]))
        else:
            st.info(T("cu_higher", pct=r["pct"], amt=r["amount"], unit=r["unit"]))
    elif r["kind"] == "unknown":
        st.warning(T("cu_unknown", raw=row["rate_raw"]))
    else:
        st.info(T("cu_applied", product=row["product"][:80], hsn=row["hsn"][:40], rate=row["rate_raw"], src=row["source"]))
    if row["conditional"]:
        st.warning(T("cu_conditional"))
    return row, rule


def tab_import():
    for k, v in dict(imp_desc="", imp_hsn="", imp_igst="18", imp_val="100000", imp_cur="INR", imp_fx="1",
                     imp_freight="0", imp_ins="0", imp_bcd="10", imp_sws="10", imp_other="0", imp_fixed="0",
                     imp_country="China", imp_cq="", imp_cpick=-1, imp_qty="1").items():
        ss.setdefault(k, v)
    st.caption(T("imp_intro"))
    lookup_block("imp")
    c1, c2 = st.columns(2)
    with c1:
        st.text_input(T("imp_desc"), key="imp_desc")
        st.text_input(T("imp_hsn"), key="imp_hsn")
        st.selectbox(T("imp_country"), COUNTRIES, key="imp_country")
    with c2:
        st.selectbox(T("imp_cur"), CURRENCIES, key="imp_cur")
        st.text_input(T("imp_val"), key="imp_val")
        st.text_input(T("imp_fx"), key="imp_fx", help=T("imp_fx_help"))
    crow, rule = customs_block()
    c3, c4 = st.columns(2)
    with c3:
        st.text_input(T("imp_freight"), key="imp_freight")
        st.text_input(T("imp_ins"), key="imp_ins")
        st.checkbox(T("imp_landing"), key="imp_landing", value=False)
    with c4:
        st.text_input(T("imp_bcd"), key="imp_bcd", help=T("imp_bcd_help"),
                      disabled=bool(rule and rule["kind"] == "specific"))
        st.text_input(T("imp_sws"), key="imp_sws", help=T("imp_sws_help"))
        st.text_input(T("imp_other"), key="imp_other", help=T("imp_other_help"))
        st.text_input(T("imp_fixed"), key="imp_fixed")
        st.text_input(T("imp_igst"), key="imp_igst")
        if rule:
            st.text_input(T("cu_qty", unit=rule["unit"]), key="imp_qty")

    def reset_imp():
        for k, v in dict(imp_desc="", imp_hsn="", imp_igst="18", imp_val="100000", imp_cur="INR", imp_fx="1",
                         imp_freight="0", imp_ins="0", imp_bcd="10", imp_sws="10", imp_other="0", imp_fixed="0",
                         imp_country="China", imp_landing=False, imp_q="", imp_pick=-1,
                         imp_cq="", imp_cpick=-1, imp_qty="1").items():
            ss[k] = v
    st.button("↺ " + T("btn_reset"), key="imp_reset", on_click=reset_imp)

    val, e1 = ge.parse_amount(ss.imp_val, allow_zero=False)
    fx, e2 = ge.parse_amount(ss.imp_fx, allow_zero=False)
    fr, e3 = ge.parse_amount(ss.imp_freight)
    ins, e4 = ge.parse_amount(ss.imp_ins)
    bcd, e5 = ge.parse_percent(ss.imp_bcd)
    sws, e6 = ge.parse_percent(ss.imp_sws)
    oth, e7 = ge.parse_percent(ss.imp_other)
    fixed, e8 = ge.parse_amount(ss.imp_fixed)
    igst, e9 = ge.parse_percent(ss.imp_igst)
    errs = [(T("imp_val"), e1), (T("imp_fx"), e2), (T("imp_freight"), e3), (T("imp_ins"), e4), (T("imp_bcd"), e5),
            (T("imp_sws"), e6), (T("imp_other"), e7), (T("imp_fixed"), e8), (T("imp_igst"), e9)]
    qty = None
    if rule:
        qty, e10 = ge.parse_amount(ss.imp_qty, allow_zero=False)
        errs.append((T("cu_qty", unit=rule["unit"]), e10))
    bad = [(n, e) for n, e in errs if e]
    if bad:
        for n, e in bad:
            st.error("%s: %s" % (n, T(e)))
        return
    if ss.imp_cur == "INR" and fx != 1:
        st.info(T("imp_inr_fx"))
    invoice_inr = ge.q2(val * (Decimal(1) if ss.imp_cur == "INR" else fx))
    r = ge.calc_import(invoice_inr, fr, ins, ss.imp_landing, bcd, sws, oth, fixed, igst, bcd_rule=rule, qty=qty)
    if rule and rule["kind"] == "specific":
        bcd_label = T("imp_r_bcd_spec", amt=_fmt_num(rule["amount"]), qty=_fmt_num(qty), unit=rule["unit"])
    elif rule:
        bcd_label = T("imp_r_bcd_higher", pct=ge.fmt_pct(bcd).rstrip("%"), amt=_fmt_num(rule["amount"]),
                      qty=_fmt_num(qty), unit=rule["unit"])
    else:
        bcd_label = "%s (%s)" % (T("imp_r_bcd"), ge.fmt_pct(bcd))
    rows = [
        (T("imp_r_invoice"), inr(invoice_inr)), (T("imp_r_cif"), inr(r["cif"])), (T("imp_r_landing"), inr(r["landing"])),
        (T("imp_r_av"), inr(r["av"])),
        (bcd_label, inr(r["bcd"])),
        ("%s (%s of BCD)" % (T("imp_r_sws"), ge.fmt_pct(sws)), inr(r["sws"])),
        ("%s (%s)" % (T("imp_r_other"), ge.fmt_pct(oth)), inr(r["other"])),
        (T("imp_r_base"), inr(r["igst_base"])),
        ("IGST (%s)" % ge.fmt_pct(igst), inr(r["igst"])),
        (T("imp_r_total"), inr(r["total_charges"])),
        (T("imp_r_fixed"), inr(r["other_fixed"])),
        (T("imp_r_net"), inr(r["landed_net_credit"])),
        (T("imp_r_landed"), inr(r["landed"])),
    ]
    kv_table(rows)
    st.warning(T("imp_warn"))
    used = (T("imp_manual") if crow is None else "%s | HSN %s | %s | %s" % (crow["product"][:80], crow["hsn"][:40], crow["rate_raw"], crow["source"]))
    meta = [(T("imp_desc"), ss.imp_desc or "—"), (T("imp_hsn"), ss.imp_hsn or "—"), (T("imp_country"), ss.imp_country),
            (T("imp_cur"), ss.imp_cur), (T("imp_val"), str(val)), (T("imp_fx"), str(fx)), (T("imp_src"), used)]
    rep = pd.DataFrame({"Item": [a for a, _ in meta + rows], "Value": [b for _, b in meta + rows]})
    downloads({"Import estimate": rep}, "gst_jano_import_estimate", "imp")
    st.markdown("**%s**" % T("official_links"))
    for name in ("ICEGATE (customs)", "CBIC", "CBIC GST rates"):
        st.markdown("- [%s](%s)" % (name, LINKS[name]))
    go_box("imp")


def _fmt_num(x):
    s = format(Decimal(x).normalize(), "f")
    return s.rstrip("0").rstrip(".") if "." in s else s


def tab_export():
    for k, v in dict(exp_desc="", exp_hsn="", exp_igst="18", exp_val="100000", exp_kind="goods",
                     exp_treat="lut").items():
        ss.setdefault(k, v)
    st.caption(T("exp_intro"))
    lookup_block("exp")
    c1, c2 = st.columns(2)
    with c1:
        st.radio(T("exp_kind"), ["goods", "services"], key="exp_kind", format_func=lambda x: T("exp_k_" + x), horizontal=True)
        st.text_input(T("imp_desc"), key="exp_desc")
        st.text_input(T("exp_code"), key="exp_hsn")
    with c2:
        st.radio(T("exp_treat"), ["lut", "pay"], key="exp_treat", format_func=lambda x: T("exp_t_" + x))
        st.text_input(T("exp_val"), key="exp_val")
        st.text_input(T("exp_igst"), key="exp_igst")
    conds = []
    if ss.exp_kind == "services":
        st.markdown("**%s**" % T("exp_conds"))
        for i in range(1, 6):
            conds.append(st.checkbox(T("exp_c%d" % i), key="exp_cond%d" % i, value=False))

    def reset_exp():
        for k, v in dict(exp_desc="", exp_hsn="", exp_igst="18", exp_val="100000", exp_kind="goods", exp_treat="lut",
                         exp_q="", exp_pick=-1).items():
            ss[k] = v
        for i in range(1, 6):
            ss["exp_cond%d" % i] = False
    st.button("↺ " + T("btn_reset"), key="exp_reset", on_click=reset_exp)

    val, e1 = ge.parse_amount(ss.exp_val, allow_zero=False)
    rate, e2 = ge.parse_percent(ss.exp_igst)
    if e1 or e2:
        if e1:
            st.error("%s: %s" % (T("exp_val"), T(e1)))
        if e2:
            st.error("%s: %s" % (T("exp_igst"), T(e2)))
        return
    eligible = True
    if ss.exp_kind == "services":
        missing = [i + 1 for i, c in enumerate(conds) if not c]
        if missing:
            eligible = False
            st.error(T("exp_not_zero", n=len(missing)))
    r = ge.calc_export(val, rate, ss.exp_treat)
    if not eligible:
        st.markdown("#### " + T("exp_result"))
        kv_table([(T("exp_val"), inr(r["value"])),
                  (T("exp_status"), T("exp_status_no")),
                  ("IGST", T("exp_dash"))], strong_last=False)
        rep = pd.DataFrame({"Item": [T("exp_val"), T("exp_status")], "Value": [inr(r["value"]), T("exp_status_no")]})
        downloads({"Export treatment": rep}, "gst_jano_export_treatment", "exp")
        return
    rows = [(T("exp_status"), T("exp_status_ok")), (T("exp_val"), inr(r["value"])), (T("exp_igst_rate"), ge.fmt_pct(rate))]
    if ss.exp_treat == "lut":
        rows += [(T("exp_igst_pay"), inr(r["igst_payable"])), (T("exp_invoice"), inr(r["invoice_total"])),
                 (T("exp_est_itc"), T("exp_itc_note"))]
    else:
        rows += [(T("exp_igst_pay"), inr(r["igst_payable"])), (T("exp_invoice"), inr(r["invoice_total"])),
                 (T("exp_refund_est"), inr(r["igst_payable"]) + " — " + T("exp_refund_note"))]
    st.markdown("#### " + T("exp_result"))
    kv_table(rows, strong_last=False)
    st.markdown("**%s**" % T("exp_zero_t"))
    st.write(T("exp_zero_d"))
    st.markdown("**%s**" % T("exp_proc_t"))
    st.write(T("exp_proc_" + ss.exp_treat + "_" + ss.exp_kind))
    st.markdown("**%s**" % T("exp_docs_t"))
    for i in range(1, 6):
        st.markdown("- " + T("exp_doc_%s_%d" % (ss.exp_kind, i)))
    st.warning(T("exp_warn"))
    meta = [(T("imp_desc"), ss.exp_desc or "—"), (T("exp_code"), ss.exp_hsn or "—"),
            (T("exp_kind"), T("exp_k_" + ss.exp_kind)), (T("exp_treat"), T("exp_t_" + ss.exp_treat))]
    rep = pd.DataFrame({"Item": [a for a, _ in meta + rows], "Value": [b for _, b in meta + rows]})
    downloads({"Export treatment": rep}, "gst_jano_export_treatment", "exp")
    st.markdown("**%s**" % T("official_links"))
    for name in ("GST Portal", "GST notifications", "ICEGATE (customs)", "CBIC GST rates"):
        st.markdown("- [%s](%s)" % (name, LINKS[name]))
    go_box("exp")


# ---- verify
def clear_verify():
    ss.v_gstin = ""
    ss.v_pan = ""


def page_verify():
    st.markdown("## 🛡️ " + T("card_verify_t"))
    ss.setdefault("v_gstin", "")
    ss.setdefault("v_pan", "")
    st.warning(T("v_notice"))
    t1, t2 = st.tabs([T("v_tab_gstin"), T("v_tab_pan")])
    with t1:
        with st.form("v_form"):
            a, b, c = st.columns([6, 1.3, 1.3])
            a.text_input(T("v_gstin"), key="v_gstin", max_chars=20, placeholder="27AAPFU0939F1ZV", label_visibility="collapsed")
            b.form_submit_button("✔ " + T("v_btn"), type="primary", use_container_width=True)
            c.form_submit_button("✖ " + T("btn_clear"), on_click=clear_verify, use_container_width=True)
        g = ss.v_gstin.strip()
        if g:
            r = ge.validate_gstin(g)
            if not r["ok"]:
                st.error(T(r["error"]))
                rows = [("GSTIN", r["input"]), (T("v_format"), T("v_invalid")), (T("v_reason"), T(r["error"]))]
            else:
                st.success(T("v_format_ok"))
                rows = [("GSTIN", r["input"]), (T("v_format"), T("v_valid")),
                        (T("v_state"), "%s (%s)" % (r["state"], r["state_code"])), ("PAN", r["pan"]),
                        (T("v_entity"), r["entity"]), (T("v_entity_no"), r["entity_no"]),
                        (T("v_legal"), T("v_na")), (T("v_trade"), T("v_na")), (T("v_status"), T("v_na")),
                        (T("v_regtype"), T("v_na")), (T("v_filing"), T("v_na"))]
            kv_table(rows, strong_last=False)
            if r["ok"]:
                if ge.provider_configured():
                    st.info(T("v_provider_noadapter"))
                else:
                    st.info(T("v_provider_missing"))
                st.link_button("🔗 " + T("v_official"), LINKS["GSTIN search (GST Portal)"])
            rep = pd.DataFrame({"Item": [a for a, _ in rows], "Value": [b for _, b in rows]})
            rep.loc[len(rep)] = ["Disclaimer", T("v_notice")]
            downloads({"GSTIN format check": rep}, "gst_jano_gstin_check", "ver")
    with t2:
        st.info(T("v_pan_info"))
        with st.form("p_form"):
            a, b = st.columns([6, 1.5])
            a.text_input(T("v_pan"), key="v_pan", max_chars=12, placeholder="AAPFU0939F")
            b.write("")
            b.write("")
            b.form_submit_button("✔ " + T("v_btn"), use_container_width=True)
        p = ss.v_pan.strip()
        if p:
            r = ge.validate_pan(p)
            if r["ok"]:
                st.success(T("v_pan_ok"))
                kv_table([("PAN", r["pan"]), (T("v_entity"), r["entity"])], strong_last=False)
            else:
                st.error(T(r["error"]))
        st.link_button("🔗 " + T("v_official"), LINKS["GSTIN search (GST Portal)"])
    with st.expander(T("v_how")):
        st.markdown(T("v_how_body"))
    go_box("ver")


# ---- payment guide
def page_payment():
    st.markdown("## 💳 " + T("card_payment_t"))
    st.write(T("pay_intro"))
    c1, c2 = st.columns(2)
    c1.link_button("🔗 " + T("pay_portal"), PAYMENT_URL, use_container_width=True)
    c2.link_button("▶ " + T("pay_video_btn"), VIDEO_URL, use_container_width=True)
    for i in range(1, 9):
        st.markdown('<div class="gj-card"><b>%s %d — %s</b><br>%s</div>'
                    % (esc(T("step")), i, esc(T("pay_s%d_t" % i)), esc(T("pay_s%d_d" % i))), unsafe_allow_html=True)
    st.markdown("### ▶ " + T("pay_video"))
    st.video(VIDEO_URL)
    st.caption(T("pay_note"))
    st.markdown("**%s**" % T("official_links"))
    for name in ("GST Portal", "CBIC GST rates", "GST Council"):
        st.markdown("- [%s](%s)" % (name, LINKS[name]))


# ------------------------------------------------------------------ main
def main():
    global CUR_LANG
    init_state()
    CUR_LANG = ss.lang or "en"
    apply_theme()
    if ss.lang is None or ss.page == "welcome":
        if ss.lang is not None:
            ss.page = "dashboard"
        else:
            page_welcome()
            sync_qp()
            return
    try:
        get_df()
    except Exception as e:
        render_header()
        st.error(T("data_missing") + " (%s)" % str(e)[:200])
        sync_qp()
        return
    render_header()
    {"dashboard": page_dashboard, "search": page_search, "calculator": page_calculator,
     "compare": page_compare, "import_export": page_import_export, "verify": page_verify,
     "payment": page_payment}[ss.page]()
    st.markdown('<div class="gj-note" style="text-align:center;margin-top:1.5rem">GST JANO · %s</div>' % esc(T("disclaimer")),
                unsafe_allow_html=True)
    sync_qp()


main()
