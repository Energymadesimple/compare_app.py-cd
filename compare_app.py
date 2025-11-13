import streamlit as st
import pandas as pd
import pdfplumber
from difflib import HtmlDiff

# --- Helper functions ---
def extract_pdf_text_and_tables(pdf_file):
    all_text, all_tables = [], []
    pdf = pdfplumber.open(pdf_file)
    total_pages = len(pdf.pages)
    for i, page in enumerate(pdf.pages):
        st.progress((i+1)/total_pages, text=f"Processing page {i+1}/{total_pages}")
        all_text.append(page.extract_text() or "")
        for t in page.extract_tables():
            if len(t) > 1:
                df = pd.DataFrame(t[1:], columns=t[0])
            else:
                df = pd.DataFrame(t)
            all_tables.append(df)
    pdf.close()
    combined_text = "\n".join(all_text)
    combined_data = pd.concat(all_tables, ignore_index=True) if all_tables else pd.DataFrame()
    return combined_text, combined_data

def match_columns(df1, df2):
    shared_cols = set(df1.columns).intersection(set(df2.columns))
    if not shared_cols:
        # Try case-insensitive matching
        df1_cols_lower = {c.lower(): c for c in df1.columns}
        df2_cols_lower = {c.lower(): c for c in df2.columns}
        shared_lower = set(df1_cols_lower.keys()).intersection(df2_cols_lower.keys())
        shared_cols = {df1_cols_lower[c]: df2_cols_lower[c] for c in shared_lower}
    return shared_cols

def compare_dataframes_smart(df_excel, df_pdf):
    shared_cols = match_columns(df_excel, df_pdf)
    diffs = []
    for col_excel, col_pdf in (shared_cols.items() if isinstance(shared_cols, dict) else zip(shared_cols, shared_cols)):
        s1 = df_excel[col_excel].astype(str).fillna("")
        s2 = df_pdf[col_pdf].astype(str).fillna("")
        max_len = max(len(s1), len(s2))
        s1 = s1.reindex(range(max_len), fill_value="")
        s2 = s2.reindex(range(max_len), fill_value="")
        mismatches = pd.DataFrame({"Excel": s1, "PDF": s2}).loc[s1 != s2]
        if not mismatches.empty:
            mismatches["Column"] = col_excel
            diffs.append(mismatches)
    return pd.concat(diffs) if diffs else pd.DataFrame()

def make_html_diff(text1, text2):
    diff = HtmlDiff(wrapcolumn=80)
    html = diff.make_table(text1.splitlines(), text2.splitlines(),
                           fromdesc="PDF Text", todesc="Excel Text", context=True)
    return html

def color_data_diff(df):
    """Highlight Excel/PDF mismatches."""
    def highlight(row):
        return [
            'background-color: #f8d7da' if col=="Excel" else 
            'background-color: #d4edda' if col=="PDF" else ''
            for col in df.columns
        ]
    return df.style.apply(highlight, axis=1)

# --- Streamlit UI ---
st.set_page_config(page_title="Smart PDF ↔ Excel Comparator", layout="wide")
st.title("📄 Smart PDF ↔ Excel Comparison Tool")

st.write("Upload a PDF and an Excel file to compare **data** and **text**. Columns/tables are matched automatically.")

pdf_file = st.file_uploader("Upload PDF file", type=["pdf"])
excel_file = st.file_uploader("Upload Excel file", type=["xlsx", "xls"])

if pdf_file and excel_file:
    if st.button("🔍 Compare Files"):
        with st.spinner("Extracting and comparing..."):
            # PDF extraction
            pdf_text, pdf_data = extract_pdf_text_and_tables(pdf_file)

            # Excel extraction
            excel_data = pd.read_excel(excel_file)
            excel_text = "\n".join(excel_data.astype(str).fillna("").values.flatten())

            # Compare data
            data_diff = compare_dataframes_smart(excel_data, pdf_data)

            # Compare text
            html_diff = make_html_diff(pdf_text, excel_text)

        st.success("✅ Comparison complete!")

        # Display data differences
        st.subheader("🧮 Data Differences")
        if not data_diff.empty:
            st.dataframe(color_data_diff(data_diff), use_container_width=True)
            csv = data_diff.to_csv(index=False).encode("utf-8")
            st.download_button("⬇️ Download Data Differences (CSV)", data=csv, file_name="data_diff_report.csv")
        else:
            st.info("No data differences found.")

        # Display text differences
        st.subheader("🧾 Text Differences")
        st.markdown("Red = deletions (Excel), Green = additions (PDF)")
        st.markdown(html_diff, unsafe_allow_html=True)
else:
    st.info("Please upload both a PDF and an Excel file.")
