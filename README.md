# GST JANO — Your Smart Guide to GST in India

GST JANO is a bilingual (English / Hindi) Streamlit app for Indian GST and customs questions. It works only from the data workbook in this repository, and it never invents rates or business records.

## Features

| Page | What it does |
|---|---|
| GST Search | Search goods and services by name, HSN or SAC code (typo tolerant, a few common Hindi words). Shows rate, GST status (applicable / nil-rated / exempt / outside GST), old rate, effective date and notes. Results download as CSV or Excel. |
| GST Calculator | Add or remove GST, with a CGST + SGST, CGST + UTGST or IGST breakdown. Uses exact decimal arithmetic and Indian number format. |
| Old vs New | Old (pre 22-Sep-2025) vs new rate, tax and final-price difference, plus the headline 2025 changes. |
| Import / Export | Import: customs value, BCD, SWS, other duties, IGST and landed cost, with BCD looked up from the `Custom duty` sheet (percentage, nil, specific and higher-of duties). Export: zero-rated treatment, LUT or payment of IGST, refund guidance and documents. |
| GSTIN Check | Format, state-code and check-character validation, and PAN format check. This is NOT official verification (see Limitations). |
| Payment Guide | Step-by-step GST payment guide with the official portal link and video. |

Other features: dark mode by default and a light mode, language and theme saved in the URL, a mobile menu, and an admin panel to import extra rate files.

## Files in this repository

| File | Purpose |
|---|---|
| `app.py` | The Streamlit application (pages, theme, navigation). Run this file. |
| `gst_data.py` | Data layer: loads the workbook, search, customs lookup, import validation. |
| `gst_engine.py` | Calculation engine: GST, import duty, export, GSTIN/PAN checks, CSV/Excel reports. |
| `i18n.py` | All English and Hindi text. |
| `gst_rates.xlsx` | The data workbook (sheets: `GST Rates`, `Everyday Items`, `Rate Changes 2025`, `Custom duty`). |
| `requirements.txt` | Python packages. |
| `logo.png` | Optional logo. If missing, a text logo is shown. |
| `.streamlit/config.toml` | Dark base theme. |

## Run locally

```bash
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Community Cloud

1. Upload all files above to a GitHub repository (the workbook must be named `gst_rates.xlsx`).
2. Go to https://share.streamlit.io and sign in with GitHub.
3. Click **Create app**, choose the repository, branch `main`, and set the main file path to `app.py`.
4. Click **Deploy**. The first start takes a minute or two.

Optional secret (Streamlit Cloud: App settings, then Secrets) to enable the admin import panel:

```toml
GSTJANO_ADMIN_PASSWORD = "choose-a-strong-password"
```

## Updating the data

- To change rates, edit `gst_rates.xlsx` and upload it to GitHub again. Keep the sheet names and column headers unchanged.
- The `Custom duty` sheet needs the columns Product, Category, HSN, Rate as notified, Duty basis, Source. Rates may be a number (0.05 means 5%, and 1 means 100%), `Nil`, `₹35 per kg`, `20% or ₹60 per piece, whichever is higher`, or `2.5% BCD (+0.5% AIDC)`.
- The admin panel (Search page) can add extra rows from an `.xlsx` or `.csv` file. On Streamlit Community Cloud these additions are temporary and disappear when the app restarts. Put permanent changes into `gst_rates.xlsx`.

## Limitations (please read)

- **Rates are only as good as the workbook.** Rows marked "Presumptive / verify" follow the general reform rule (12% to 5%, 28% to 18%) and must be confirmed on the CBIC rate finder.
- **Customs duty** covers only the items in the `Custom duty` sheet (Budget 2026-27 annexure items). A missing entry does not mean zero duty. Enter BCD from the Customs Tariff.
- **GSTIN check is not verification.** The app checks format, state code and the check character only. Legal name, status and filing history need the GST Portal or an authorized GST API provider. No provider is connected; set `GSTIN_API_URL` and `GSTIN_API_KEY` and add an adapter in `gst_engine.py` to integrate one.
- **Search updates when the user presses Enter** or the Search button, not on every keystroke.
- Reports are provided as CSV and Excel (no PDF).

## Disclaimer

For information only. This is not legal, tax or customs advice. Always confirm rates and procedures on the official CBIC / GST Portal / ICEGATE.
