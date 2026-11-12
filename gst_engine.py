"""GST JANO - calculation engine (pure Python, Decimal arithmetic, no UI code)."""
import io
import os
import re
from decimal import Decimal, ROUND_HALF_UP, getcontext

import pandas as pd

getcontext().prec = 60
Q2 = Decimal("0.01")
MAX_AMOUNT = Decimal("1000000000000000")  # 1 quadrillion rupees upper guard

GSTIN_RE = re.compile(r"^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z]{1}[1-9A-Z]{1}Z[0-9A-Z]{1}$")
PAN_RE = re.compile(r"^[A-Z]{5}[0-9]{4}[A-Z]$")
CHARSET = "0123456789ABCDEFGHIJKLMNOPQRSTUVWXYZ"

STATE_CODES = {
    "01": "Jammu & Kashmir", "02": "Himachal Pradesh", "03": "Punjab", "04": "Chandigarh",
    "05": "Uttarakhand", "06": "Haryana", "07": "Delhi", "08": "Rajasthan", "09": "Uttar Pradesh",
    "10": "Bihar", "11": "Sikkim", "12": "Arunachal Pradesh", "13": "Nagaland", "14": "Manipur",
    "15": "Mizoram", "16": "Tripura", "17": "Meghalaya", "18": "Assam", "19": "West Bengal",
    "20": "Jharkhand", "21": "Odisha", "22": "Chhattisgarh", "23": "Madhya Pradesh",
    "24": "Gujarat", "26": "Dadra & Nagar Haveli and Daman & Diu", "27": "Maharashtra",
    "29": "Karnataka", "30": "Goa", "31": "Lakshadweep", "32": "Kerala", "33": "Tamil Nadu",
    "34": "Puducherry", "35": "Andaman & Nicobar", "36": "Telangana", "37": "Andhra Pradesh",
    "38": "Ladakh", "97": "Other Territory", "99": "Centre Jurisdiction",
}
PAN_ENTITY = {
    "P": "Individual", "C": "Company", "H": "Hindu Undivided Family", "F": "Firm / LLP",
    "A": "Association of Persons", "T": "Trust", "B": "Body of Individuals",
    "L": "Local Authority", "J": "Artificial Juridical Person", "G": "Government",
}


def q2(x):
    return Decimal(x).quantize(Q2, rounding=ROUND_HALF_UP)


def parse_amount(text, allow_zero=True):
    """Parse user text into Decimal. Returns (value, error_key). error_key is None when OK."""
    s = (text or "").strip().replace(",", "").replace("₹", "").replace(" ", "")
    if s == "":
        return None, "err_empty"
    if s.startswith("-"):
        return None, "err_negative"
    if not re.fullmatch(r"\d+(\.\d+)?", s):
        return None, "err_invalid"
    v = Decimal(s)
    if v > MAX_AMOUNT:
        return None, "err_too_large"
    if v == 0 and not allow_zero:
        return None, "err_zero"
    return v, None


def parse_percent(text):
    v, err = parse_amount(text)
    if err:
        return None, err
    if v > 100:
        return None, "err_percent"
    return v, None


def fmt_inr(x, decimals=2):
    """Format a Decimal as Indian rupees with lakh/crore grouping, e.g. ₹12,34,567.89."""
    x = Decimal(x)
    neg = x < 0
    x = abs(x)
    q = Decimal(1).scaleb(-decimals) if decimals else Decimal(1)
    x = x.quantize(q, rounding=ROUND_HALF_UP)
    s = format(x, "f")
    ip, _, fp = s.partition(".")
    if len(ip) > 3:
        head, tail = ip[:-3], ip[-3:]
        parts = []
        while len(head) > 2:
            parts.insert(0, head[-2:])
            head = head[:-2]
        if head:
            parts.insert(0, head)
        ip = ",".join(parts) + "," + tail
    out = "₹" + ip + ("." + fp if decimals else "")
    return "-" + out if neg else out


def fmt_pct(x):
    x = Decimal(x)
    s = format(x.normalize(), "f")
    if "." in s:
        s = s.rstrip("0").rstrip(".")
    return s + "%"


# ---------------------------------------------------------------- GST calculator
def calc_gst(amount, rate_pct, mode="add", supply="intra"):
    """
    mode   : 'add'    -> amount is GST-exclusive, GST is added
             'remove' -> amount is GST-inclusive, GST is removed
    supply : 'intra' (CGST+SGST), 'ut' (CGST+UTGST), 'inter' (IGST)
    """
    amount, rate = Decimal(amount), Decimal(rate_pct)
    if mode == "add":
        taxable = q2(amount)
        tax = q2(taxable * rate / 100)
        total = taxable + tax
    else:
        total = q2(amount)
        taxable = q2(total * 100 / (100 + rate))
        tax = total - taxable
    res = {"mode": mode, "supply": supply, "original": q2(amount), "rate": rate,
           "taxable": taxable, "tax": tax, "total": total}
    if supply == "inter":
        res["igst"] = tax
    else:
        half = q2(tax / 2)
        res["cgst"] = half
        other = tax - half
        if supply == "ut":
            res["utgst"] = other
        else:
            res["sgst"] = other
    return res


# ---------------------------------------------------------------- import / customs
def calc_import(invoice_inr, freight, insurance, landing_flag, bcd_pct, sws_pct,
                other_pct, other_fixed, igst_pct, bcd_rule=None, qty=None):
    """bcd_rule (optional): {'kind': 'specific'|'higher', 'amount': Decimal rupees per unit}; qty = number of units."""
    d = {k: Decimal(v) for k, v in dict(invoice=invoice_inr, freight=freight, insurance=insurance,
                                        bcd_pct=bcd_pct, sws_pct=sws_pct, other_pct=other_pct,
                                        other_fixed=other_fixed, igst_pct=igst_pct).items()}
    cif = q2(d["invoice"] + d["freight"] + d["insurance"])
    landing = q2(cif / 100) if landing_flag else Decimal("0.00")
    av = cif + landing
    bcd = q2(av * d["bcd_pct"] / 100)
    if bcd_rule and bcd_rule.get("kind") in ("specific", "higher") and qty is not None:
        spec = q2(Decimal(bcd_rule["amount"]) * Decimal(qty))
        bcd = spec if bcd_rule["kind"] == "specific" else max(bcd, spec)
    sws = q2(bcd * d["sws_pct"] / 100)
    other = q2(av * d["other_pct"] / 100)
    igst_base = av + bcd + sws + other
    igst = q2(igst_base * d["igst_pct"] / 100)
    duties = bcd + sws + other
    total_charges = duties + igst
    landed = av + total_charges + q2(d["other_fixed"])
    return {"cif": cif, "landing": landing, "av": av, "bcd": bcd, "sws": sws, "other": other,
            "igst_base": igst_base, "igst": igst, "duties": duties, "total_charges": total_charges,
            "other_fixed": q2(d["other_fixed"]), "landed": landed, "landed_net_credit": landed - igst}


# ---------------------------------------------------------------- export
def calc_export(value_inr, igst_pct, treatment):
    value, rate = Decimal(value_inr), Decimal(igst_pct)
    value = q2(value)
    igst = Decimal("0.00") if treatment == "lut" else q2(value * rate / 100)
    return {"value": value, "rate": rate, "igst_payable": igst, "invoice_total": value + igst,
            "treatment": treatment}


# ---------------------------------------------------------------- GSTIN / PAN
def gstin_check_char(first14):
    total = 0
    for i, c in enumerate(first14):
        v = CHARSET.index(c) * (1 if i % 2 == 0 else 2)
        total += v // 36 + v % 36
    return CHARSET[(36 - total % 36) % 36]


def validate_gstin(text):
    """Format + state-code + check-character validation. NOT proof of registration."""
    g = re.sub(r"\s", "", (text or "")).upper()
    out = {"input": g, "ok": False, "error": None}
    if not g:
        out["error"] = "gstin_err_empty"
    elif len(g) != 15:
        out["error"] = "gstin_err_len"
    elif not GSTIN_RE.match(g):
        out["error"] = "gstin_err_format"
    elif g[:2] not in STATE_CODES:
        out["error"] = "gstin_err_state"
    elif gstin_check_char(g[:14]) != g[14]:
        out["error"] = "gstin_err_check"
        out["expected_check"] = gstin_check_char(g[:14])
    if out["error"] is None:
        pan = g[2:12]
        out.update(ok=True, state=STATE_CODES[g[:2]], state_code=g[:2], pan=pan,
                   entity=PAN_ENTITY.get(pan[3], "Other"), entity_no=g[12])
    return out


def validate_pan(text):
    p = re.sub(r"\s", "", (text or "")).upper()
    if not p:
        return {"ok": False, "error": "pan_err_empty", "pan": p}
    if not PAN_RE.match(p):
        return {"ok": False, "error": "pan_err_format", "pan": p}
    return {"ok": True, "pan": p, "entity": PAN_ENTITY.get(p[3], "Other"), "error": None}


def provider_configured():
    """True when GSTIN_API_URL and GSTIN_API_KEY exist. No adapter is bundled, so this is only a flag."""
    return bool(os.environ.get("GSTIN_API_URL") and os.environ.get("GSTIN_API_KEY"))


# ---------------------------------------------------------------- report files
def to_csv_bytes(df):
    return df.to_csv(index=False).encode("utf-8-sig")


def to_xlsx_bytes(sheets):
    """sheets: dict name -> DataFrame. Returns bytes of a real .xlsx file."""
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as xw:
        for name, frame in sheets.items():
            frame.to_excel(xw, sheet_name=name[:31], index=False)
            ws = xw.sheets[name[:31]]
            for col in ws.columns:
                width = max(len(str(c.value)) if c.value is not None else 0 for c in col[:200])
                ws.column_dimensions[col[0].column_letter].width = min(max(width + 2, 10), 70)
    return buf.getvalue()
