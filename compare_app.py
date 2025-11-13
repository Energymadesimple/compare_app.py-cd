import streamlit as st
import pandas as pd
import pdfplumber
from difflib import HtmlDiff

st.title("PDF ↔ Excel Comparator")

pdf_file = st.file_uploader("Upload PDF", type="pdf")
excel_file = st.file_uploader("Upload Excel", type=["xlsx","xls"])

if pdf_file and excel_file:
    with st.spinner("Processing..."):
        # Extract PDF text
        text_pages = []
        tables = []
        with pdfplumber.open(pdf_file) as pdf:
            for page in pdf.pages:
                text_pages.append(page.extract_text() or "")
                for t in page.extract_tables():
                    if len(t) > 1:
                        df = pd.DataFrame(t[1:], columns=t[0])
                    else:
                        df = pd.DataFrame(t)
                    tables.append(df)
        pdf_text = "\n".join(text_pages)
        pdf_data = pd.concat(tables, ignore_index=True) if tables else pd.DataFrame()

        # Read Excel
        excel_data = pd.read_excel(excel_file)
        excel_text = "\n".join(excel_data.astype(str).fillna("").values.flatten())

        # Compare text
        html_diff = HtmlDiff().make_table(pdf_text.splitlines(), excel_text.splitlines(),
                                          fromdesc="PDF", todesc="Excel", context=True)
        st.subheader("Text Differences")
        st.markdown(html_diff, unsafe_allow_html=True)

        # Compare data
        shared_cols = set(excel_data.columns).intersection(pdf_data.columns)
        diffs = []
        for col in shared_cols:
            mismatches = pd.DataFrame({
                "Excel": excel_data[col].astype(str),
                "PDF": pdf_data[col].astype(str)
            }).loc[excel_data[col].astype(str) != pdf_data[col].astype(str)]
            if not mismatches.empty:
                mismatches["Column"] = col
                diffs.append(mismatches)
        if diffs:
            data_diff = pd.concat(diffs)
            st.subheader("Data Differences")
            st.dataframe(data_diff)
        else:
            st.info("No data differences found.")
