"""GST JANO - data layer: loads the real workbook, classifies rows, searches, validates imports."""
import os
import re
from decimal import Decimal
import pandas as pd
from rapidfuzz import process, fuzz

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE = os.path.join(BASE_DIR, "gst_rates.xlsx")
CUSTOM_FILE = os.path.join(BASE_DIR, "gst_rates_custom.csv")

# Columns of the 'GST Rates' sheet of the master workbook
COL_ID = "ID"
COL_TYPE = "Type"
COL_CAT = "Category / Schedule"
COL_CODE = "HSN / SAC"
COL_NAME = "Goods / Service Name"
COL_RATE = "Current GST Rate (IGST)"
COL_OLD = "Old Rate (pre 22-Sep-2025)"
COL_CHANGE = "Rate Change"
COL_STATUS = "Rate Status"
COL_NOTES = "Notes"
REQUIRED_COLS = [COL_TYPE, COL_CODE, COL_NAME, COL_RATE]
ALL_COLS = [COL_ID, COL_TYPE, COL_CAT, COL_CODE, COL_NAME, COL_RATE, "CGST",
            "SGST / UTGST", COL_OLD, COL_CHANGE, COL_STATUS, COL_NOTES]
VALID_CURRENT_RATES = [0.0, 0.0025, 0.01, 0.015, 0.03, 0.05, 0.18, 0.40]
SPECIAL_RATES = [0.0025, 0.01, 0.015, 0.03]

NORMAL_COLS = ["id", "type", "category", "code", "name", "rate", "old_rate", "change",
               "status", "notes", "keywords", "source", "outside"]

# Small Hindi -> English helper so Hindi users can search the English database
HINDI_SYNONYMS = {
    "दूध": "milk", "चावल": "rice", "गेहूं": "wheat", "आटा": "flour", "चीनी": "sugar",
    "तेल": "oil", "घी": "ghee", "नमक": "salt", "कार": "car", "सोना": "gold",
    "चांदी": "silver", "होटल": "hotel", "बीमा": "insurance", "कपड़े": "apparel",
    "जूते": "footwear", "दवा": "medicine", "दवाई": "medicine", "पनीर": "paneer",
    "चाय": "tea", "कॉफी": "coffee", "साबुन": "soap", "किताब": "book", "मोबाइल": "mobile",
    "टीवी": "television", "बाइक": "motorcycle", "सीमेंट": "cement", "बिस्कुट": "biscuit",
    "रोटी": "roti", "दही": "curd", "मक्खन": "butter", "फल": "fruit", "सब्जी": "vegetable",
    "शिक्षा": "education", "रेस्टोरेंट": "restaurant", "जिम": "gym", "टूथपेस्ट": "toothpaste",
}


def _clean(v):
    if v is None:
        return ""
    if isinstance(v, float) and pd.isna(v):
        return ""
    return str(v).strip()


def _to_rate(v):
    """Return a float fraction or None."""
    s = _clean(v).replace("%", "")
    if s == "" or s == "-":
        return None
    try:
        return float(s)
    except ValueError:
        return None


def code_tokens(raw):
    """Extract searchable code tokens (digits only) from a messy HSN/SAC cell."""
    tokens = []
    for part in re.split(r"[,;/]", _clean(raw)):
        part = part.strip()
        if not part or part.lower().startswith("except"):
            continue
        m = re.match(r"\d[\d ]*", part)
        if m:
            tok = m.group(0).replace(" ", "")
            if len(tok) >= 2:
                tokens.append(tok)
    return tokens


def _find_sheet(xl, wanted):
    for name in xl.sheet_names:
        if name.strip().lower() == wanted.lower():
            return name
    return None


def _normalise_master(df, source):
    rows = []
    for _, r in df.iterrows():
        rate = _to_rate(r.get(COL_RATE))
        notes = _clean(r.get(COL_NOTES))
        rows.append({
            "id": _clean(r.get(COL_ID)), "type": _clean(r.get(COL_TYPE)) or "Goods",
            "category": _clean(r.get(COL_CAT)), "code": _clean(r.get(COL_CODE)),
            "name": _clean(r.get(COL_NAME)), "rate": rate,
            "old_rate": _to_rate(r.get(COL_OLD)), "change": _clean(r.get(COL_CHANGE)),
            "status": _clean(r.get(COL_STATUS)), "notes": notes, "keywords": "",
            "source": source, "outside": "outside gst" in notes.lower(),
        })
    return rows


def _normalise_everyday(df):
    rows = []
    for i, (_, r) in enumerate(df.iterrows(), start=1):
        raw_rate = _clean(r.get("Current GST Rate"))
        remark = _clean(r.get("Remark"))
        outside = "outside gst" in raw_rate.lower() or "outside gst" in remark.lower()
        rows.append({
            "id": "E%03d" % i, "type": "Goods/Service", "category": "Everyday Items",
            "code": _clean(r.get("HSN / SAC")), "name": _clean(r.get("Item (plain language)")),
            "rate": None if (outside and _to_rate(raw_rate) is None) else _to_rate(raw_rate),
            "old_rate": None, "change": "", "status": "Everyday item list (workbook)",
            "notes": remark, "keywords": _clean(r.get("Search Keywords (for app)")),
            "source": "Everyday Items", "outside": outside,
        })
    return rows


def classify(rate, outside, notes, category):
    """Return (status_key, category_key) used for labels in the UI."""
    nl = (notes or "").lower()
    if outside:
        return "outside", "cat_outside"
    if rate is None:
        return "outside", "cat_outside"
    if rate == 0:
        if "exempt" in nl:
            return "exempt", "cat_nil"
        if "nil" in nl:
            return "nil", "cat_nil"
        return "nil_or_exempt", "cat_nil"
    if abs(rate - 0.40) < 1e-9:
        return "applicable", "cat_demerit"
    if any(abs(rate - s) < 1e-9 for s in SPECIAL_RATES):
        return "applicable", "cat_special"
    if abs(rate - 0.05) < 1e-9:
        return "applicable", "cat_merit"
    if abs(rate - 0.18) < 1e-9:
        return "applicable", "cat_standard"
    return "applicable", "cat_other"


def load_custom():
    if not os.path.exists(CUSTOM_FILE):
        return []
    try:
        cdf = pd.read_csv(CUSTOM_FILE, dtype=str, keep_default_na=False)
    except Exception:
        return []
    return _normalise_master(cdf, "Imported file")


def load_data():
    """Load the master workbook (+ optional imported rows). Raises FileNotFoundError if missing."""
    if not os.path.exists(DATA_FILE):
        raise FileNotFoundError(DATA_FILE)
    xl = pd.ExcelFile(DATA_FILE)
    rows = []
    s = _find_sheet(xl, "GST Rates")
    if s is None:
        raise ValueError("Sheet 'GST Rates' not found in workbook")
    rows += _normalise_master(pd.read_excel(xl, s, dtype=str, keep_default_na=False), "GST Rates")
    s = _find_sheet(xl, "Everyday Items")
    if s is not None:
        rows += _normalise_everyday(pd.read_excel(xl, s, dtype=str, keep_default_na=False))
    rows += load_custom()
    df = pd.DataFrame(rows, columns=NORMAL_COLS)
    df = df[df["name"] != ""].reset_index(drop=True)
    cls = [classify(r.rate if pd.notna(r.rate) else None, r.outside, r.notes, r.category)
           for r in df.itertuples()]
    df["status_key"] = [c[0] for c in cls]
    df["cat_key"] = [c[1] for c in cls]
    df["tokens"] = df["code"].apply(code_tokens)
    df["name_l"] = df["name"].str.lower()
    df["kw_l"] = (df["keywords"] + " " + df["category"]).str.lower()
    df["text"] = df["name_l"] + " " + df["kw_l"]
    return df


def load_headline_changes():
    xl = pd.ExcelFile(DATA_FILE)
    s = _find_sheet(xl, "Rate Changes 2025")
    if s is None:
        return pd.DataFrame(columns=["Direction", "Category / Item", "Old GST", "New GST", "Change (pp)"])
    d = pd.read_excel(xl, s)
    d = d[d["Direction"].isin(["REDUCED", "INCREASED"])].copy()
    d["Change (pp)"] = d["Change (pp)"].round(2)
    return d.reset_index(drop=True)


# ---------------------------------------------------------------- search
_WORD = re.compile(r"[a-z0-9]+")


def _vocab(df):
    words = set()
    for t in df["text"]:
        words.update(w for w in _WORD.findall(t) if len(w) >= 3)
    return sorted(words)


def normalise_query(q):
    q = (q or "").strip()
    for hi, en in HINDI_SYNONYMS.items():
        q = q.replace(hi, en)
    return q


def is_code_query(q):
    return bool(re.fullmatch(r"[\d ]{2,}", (q or "").strip()))


def search(df, query, limit=300):
    """Search the real database. Returns a DataFrame (subset of df) with a 'score' column."""
    q = normalise_query(query)
    if not q:
        return df.iloc[0:0].assign(score=[])
    if is_code_query(q):
        qd = q.replace(" ", "")
        scores = []
        for toks in df["tokens"]:
            best = 0
            for tk in toks:
                if tk == qd:
                    best = max(best, 100)
                elif tk.startswith(qd):
                    best = max(best, 90)
                elif qd.startswith(tk):
                    best = max(best, 60 + len(tk))
            scores.append(best)
        out = df.assign(score=scores)
        out = out[out["score"] > 0]
        return out.sort_values(["score", "name"], ascending=[False, True]).head(limit)

    ql = q.lower()
    toks = _WORD.findall(ql)
    if not toks:
        return df.iloc[0:0].assign(score=[])
    all_text = " ".join(df["text"])
    vocab = None
    alts = []
    for tk in toks:
        options = [tk]
        if len(tk) >= 3 and tk not in all_text:
            if vocab is None:
                vocab = _vocab(df)
            near = process.extract(tk, vocab, scorer=fuzz.ratio, score_cutoff=78, limit=3)
            options = [n[0] for n in near]
        alts.append(options)

    scores = []
    for name_l, text in zip(df["name_l"], df["text"]):
        total = 0
        ok = True
        for options in alts:
            best = 0
            for o in options:
                if not o:
                    continue
                if re.search(r"\b" + re.escape(o) + r"(s|es)?\b", name_l):
                    best = max(best, 3)
                elif o in name_l:
                    best = max(best, 2)
                elif o in text:
                    best = max(best, 1)
            if best == 0:
                ok = False
                break
            total += best
        if ok:
            if re.search(r"\b" + re.escape(ql) + r"\b", name_l):
                total += 4
                if re.match(re.escape(ql) + r"\b", name_l):
                    total += 3
            scores.append(total)
        else:
            scores.append(0)
    out = df.assign(score=scores)
    out = out[out["score"] > 0]
    if out.empty and len(ql.replace(" ", "")) >= 4:
        compact = ql.replace(" ", "")
        mask = df["text"].str.replace(" ", "", regex=False).str.contains(re.escape(compact))
        out = df[mask].assign(score=1)
    out = out.assign(_len=out["name"].str.len())
    return out.sort_values(["score", "_len"], ascending=[False, True]).drop(columns="_len").head(limit)


def find_by_code(df, code):
    """Best row for a code (used to pre-fill rates). Returns Series or None."""
    qd = re.sub(r"\D", "", code or "")
    if len(qd) < 2:
        return None
    res = search(df, qd, limit=5)
    return None if res.empty else res.iloc[0]


# ---------------------------------------------------------------- import validation
def validate_upload(up, existing):
    """Validate an uploaded DataFrame. Returns dict(clean=DataFrame, errors=list, duplicates=int, total=int)."""
    errors = []
    up = up.copy()
    up.columns = [str(c).strip() for c in up.columns]
    missing = [c for c in REQUIRED_COLS if c not in up.columns]
    if missing:
        return {"clean": pd.DataFrame(columns=ALL_COLS), "total": len(up), "duplicates": 0,
                "errors": [("-", "Missing required column(s): " + ", ".join(missing))]}
    seen = set()
    for _, r in existing.iterrows():
        seen.add((r["type"].lower(), re.sub(r"\s", "", r["code"]).lower(), r["name_l"]))
    keep, dup = [], 0
    for i, r in up.iterrows():
        line = i + 2
        typ = _clean(r.get(COL_TYPE)).title()
        code = _clean(r.get(COL_CODE))
        name = _clean(r.get(COL_NAME))
        rate = _to_rate(r.get(COL_RATE))
        if typ not in ("Goods", "Service"):
            errors.append((line, "Type must be 'Goods' or 'Service'")); continue
        if not code or not code_tokens(code):
            errors.append((line, "HSN / SAC is empty or has no numeric code")); continue
        if not name:
            errors.append((line, "Name is empty")); continue
        if rate is None:
            errors.append((line, "Rate is empty or not a number")); continue
        if rate > 1:
            rate = rate / 100.0
        if not any(abs(rate - v) < 1e-9 for v in VALID_CURRENT_RATES):
            errors.append((line, "Rate %.4g is not a current GST slab (0, 0.25, 1, 1.5, 3, 5, 18, 40 %%)" % (rate * 100))); continue
        key = (typ.lower(), re.sub(r"\s", "", code).lower(), name.lower())
        if key in seen:
            dup += 1; continue
        seen.add(key)
        old = _to_rate(r.get(COL_OLD))
        if old is not None and old > 1:
            old = old / 100.0
        keep.append({
            COL_ID: _clean(r.get(COL_ID)) or "IMP%05d" % (len(keep) + 1), COL_TYPE: typ,
            COL_CAT: _clean(r.get(COL_CAT)) or "Imported", COL_CODE: code, COL_NAME: name,
            COL_RATE: rate, "CGST": rate / 2, "SGST / UTGST": rate / 2,
            COL_OLD: old if old is not None else rate,
            COL_CHANGE: _clean(r.get(COL_CHANGE)) or "No change",
            COL_STATUS: _clean(r.get(COL_STATUS)) or "Imported - verify",
            COL_NOTES: _clean(r.get(COL_NOTES)),
        })
    return {"clean": pd.DataFrame(keep, columns=ALL_COLS), "errors": errors,
            "duplicates": dup, "total": len(up)}


def save_custom(clean):
    """Append validated rows to the custom CSV. Returns number of rows now stored."""
    if os.path.exists(CUSTOM_FILE):
        old = pd.read_csv(CUSTOM_FILE, dtype=str, keep_default_na=False)
        merged = pd.concat([old, clean.astype(str)], ignore_index=True)
    else:
        merged = clean.astype(str)
    merged.to_csv(CUSTOM_FILE, index=False)
    return len(pd.read_csv(CUSTOM_FILE, dtype=str, keep_default_na=False))


# ---------------------------------------------------------------- customs duty sheet
CUSTOMS_SHEET_NAMES = ("custom duty", "customs duty", "custom duties", "customs duties")
_COND_WORDS = ("for manufacture", "sez", "personal use", "imported by", "for use in")


def _cell(v):
    if v is None:
        return ""
    if isinstance(v, float) and pd.isna(v):
        return ""
    if isinstance(v, float) and v.is_integer():
        return str(int(v))
    return str(v).strip()


def _dec_str(x):
    """Decimal/float -> tidy string without trailing zeros (7.5, 10, 0.25)."""
    d = Decimal(str(x)).normalize()
    s = format(d, "f")
    return s.rstrip("0").rstrip(".") if "." in s else s


def parse_customs_rate(v):
    """Turn a rate cell into a dict: kind in nil/adval/specific/higher/unknown."""
    if v is None or (isinstance(v, float) and pd.isna(v)) or str(v).strip() == "":
        return None
    if isinstance(v, (int, float)) and not isinstance(v, bool):
        x = Decimal(str(v))
        pct = x * 100 if x <= 1 else x          # 0.05 -> 5 ; 1 -> 100 ; 7.5 -> 7.5
        return {"kind": "adval", "pct": _dec_str(pct), "aidc": None, "amount": None, "unit": None}
    s = str(v).strip()
    sl = s.lower()
    if sl in ("nil", "exempt", "free", "0", "0%"):
        return {"kind": "nil", "pct": "0", "aidc": None, "amount": None, "unit": None}
    m = re.match(r"^([\d.]+)\s*%\s*bcd\s*\(\s*\+\s*([\d.]+)\s*%\s*aidc\s*\)$", sl)
    if m:
        return {"kind": "adval", "pct": _dec_str(m.group(1)), "aidc": _dec_str(m.group(2)), "amount": None, "unit": None}
    m = re.match(r"^([\d.]+)\s*%\s*or\s*(?:₹|rs\.?|re\.?)\s*([\d.,]+)\s*per\s*([a-z]+)\s*,?\s*whichever is higher$", sl)
    if m:
        return {"kind": "higher", "pct": _dec_str(m.group(1)), "aidc": None,
                "amount": _dec_str(m.group(2).replace(",", "")), "unit": m.group(3)}
    m = re.match(r"^(?:₹|rs\.?|re\.?)\s*([\d.,]+)\s*per\s*([a-z]+)$", sl)
    if m:
        return {"kind": "specific", "pct": None, "aidc": None,
                "amount": _dec_str(m.group(1).replace(",", "")), "unit": m.group(2)}
    m = re.match(r"^([\d.]+)\s*%$", sl)
    if m:
        return {"kind": "adval", "pct": _dec_str(m.group(1)), "aidc": None, "amount": None, "unit": None}
    return {"kind": "unknown", "pct": None, "aidc": None, "amount": None, "unit": None}


def parse_customs_hsn(raw):
    """Return (patterns, exclusions). patterns: list of ('prefix',code) / ('range',lo,hi) / ('chapter',code)."""
    s = _cell(raw)
    if not s:
        return [], []
    m = re.match(r"^chapter\s+(\d+)", s, re.I)
    if m:
        return [("chapter", m.group(1).zfill(2))], []
    if re.fullmatch(r"\d{1,2}", s):
        return [("chapter", s.zfill(2))], []
    excl = []
    m = re.search(r"\(\s*other than\s+([^)]*)\)", s, re.I)
    if m:
        for part in m.group(1).split(","):
            d = re.sub(r"\D", "", part)
            if d:
                excl.append(d)
        s = s[:m.start()] + s[m.end():]
    pats = []
    for part in s.split(","):
        part = part.strip()
        if not part:
            continue
        if re.search(r"\sto\s", part, re.I):
            lo, hi = re.split(r"\sto\s", part, maxsplit=1, flags=re.I)
            lo, hi = re.sub(r"\D", "", lo), re.sub(r"\D", "", hi)
            if lo and hi and len(lo) == len(hi):
                pats.append(("range", lo, hi))
            continue
        d = re.sub(r"\D", "", part)
        if len(d) >= 3:
            pats.append(("prefix", d))
        elif len(d) == 2:
            pats.append(("chapter", d))
    return pats, excl


def load_customs():
    """Read the 'Custom duty' sheet. Returns dict(df=DataFrame, notes=[str], error=None|str)."""
    empty = pd.DataFrame(columns=["product", "category", "hsn", "rate_raw", "basis", "source", "rate",
                                  "patterns", "excl", "conditional"])
    try:
        xl = pd.ExcelFile(DATA_FILE)
    except Exception as e:
        return {"df": empty, "notes": [], "error": str(e)[:150]}
    sheet = next((n for n in xl.sheet_names if n.strip().lower() in CUSTOMS_SHEET_NAMES), None)
    if sheet is None:
        return {"df": empty, "notes": [], "error": "no_sheet"}
    raw = pd.read_excel(xl, sheet, header=None, dtype=object)
    hdr = None
    for i in range(min(10, len(raw))):
        cells = [_cell(c).lower() for c in raw.iloc[i]]
        if any("hsn" in c for c in cells) and any("rate" in c for c in cells):
            hdr = i
            break
    if hdr is None:
        return {"df": empty, "notes": [], "error": "no_header"}
    names = [_cell(c).lower() for c in raw.iloc[hdr]]

    def col(*keys):
        for j, n in enumerate(names):
            if any(k in n for k in keys):
                return j
        return None
    c_prod, c_cat = col("product", "description", "item"), col("category")
    c_hsn, c_rate, c_basis, c_src = col("hsn"), col("rate"), col("basis"), col("source")
    if c_prod is None or c_hsn is None or c_rate is None:
        return {"df": empty, "notes": [], "error": "no_header"}
    rows, notes = [], []
    for i in range(hdr + 1, len(raw)):
        r = raw.iloc[i]
        product, hsn = _cell(r.iloc[c_prod]), _cell(r.iloc[c_hsn])
        rate = parse_customs_rate(r.iloc[c_rate])
        if not hsn and rate is None:
            # first text column may hold a free-text note (e.g. exempt drug list)
            texts = [_cell(c) for c in r if _cell(c)]
            if texts:
                notes.append(texts[0])
            continue
        if rate is None or not product:
            continue
        pats, excl = parse_customs_hsn(hsn)
        rows.append({
            "product": product, "category": _cell(r.iloc[c_cat]) if c_cat is not None else "",
            "hsn": hsn, "rate_raw": _cell(r.iloc[c_rate]), "basis": _cell(r.iloc[c_basis]) if c_basis is not None else "",
            "source": _cell(r.iloc[c_src]) if c_src is not None else "", "rate": rate,
            "patterns": pats, "excl": excl,
            "conditional": any(w in product.lower() for w in _COND_WORDS),
        })
    df = pd.DataFrame(rows, columns=empty.columns)
    for n in range(len(df)):
        # display text for the rate (numbers shown as %)
        r = df.at[n, "rate"]
        if r["kind"] == "adval":
            txt = _dec_str(r["pct"]) + "%" + (" + " + r["aidc"] + "% AIDC" if r["aidc"] else "")
            df.at[n, "rate_raw"] = txt
        elif r["kind"] == "nil":
            df.at[n, "rate_raw"] = "Nil"
    return {"df": df, "notes": notes, "error": None}


def search_customs(cdf, query):
    """Find customs entries by HSN code (digits) or by product name. Adds a 'match' column:
    code / range / related / text. Entries are ordered best-first."""
    q = (query or "").strip()
    if cdf.empty or not q:
        return cdf.iloc[0:0].assign(match=[], rank=[])
    out = []
    if re.fullmatch(r"[\d ]{2,}", q):
        qd = q.replace(" ", "")
        for idx, row in cdf.iterrows():
            best = None
            for p in row["patterns"]:
                if p[0] == "prefix":
                    if qd.startswith(p[1]):
                        if any(qd.startswith(e) for e in row["excl"]):
                            continue
                        cand = ("code", 1000 + len(p[1]))
                    elif p[1].startswith(qd):
                        cand = ("related", 500 + len(qd))
                    else:
                        continue
                elif p[0] == "range":
                    L = len(p[1])
                    if len(qd) >= L:
                        if p[1] <= qd[:L] <= p[2]:
                            cand = ("range", 900)
                        else:
                            continue
                    elif p[1][:len(qd)] <= qd <= p[2][:len(qd)]:
                        cand = ("related", 400)
                    else:
                        continue
                else:  # chapter-level entry: product specific, never auto-applied
                    if qd == p[1]:
                        cand = ("related", 100)
                    else:
                        continue
                if best is None or cand[1] > best[1]:
                    best = cand
            if best:
                out.append((idx, best[0], best[1]))
    else:
        toks = re.findall(r"[a-z0-9]+", q.lower())
        for idx, row in cdf.iterrows():
            text = (row["product"] + " " + row["category"]).lower()
            if toks and all(t in text for t in toks):
                out.append((idx, "text", 50))
    if not out:
        return cdf.iloc[0:0].assign(match=[], rank=[])
    res = cdf.loc[[o[0] for o in out]].copy()
    res["match"] = [o[1] for o in out]
    res["rank"] = [o[2] for o in out]
    return res.sort_values("rank", ascending=False, kind="stable")
