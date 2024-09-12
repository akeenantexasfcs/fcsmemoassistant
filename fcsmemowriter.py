#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import streamlit as st
import openai
import boto3
from PyPDF2 import PdfReader
from openpyxl import load_workbook
from PIL import Image
import io
import docx
import os
import time

# ... [previous code for environment variables and function definitions remains the same] ...

def main():
    st.title("AI Memo Writer")
    
    # Initialize session state for file uploads
    if 'term_sheet' not in st.session_state:
        st.session_state.term_sheet = None
    if 'pricing_table' not in st.session_state:
        st.session_state.pricing_table = None
    if 'supplemental' not in st.session_state:
        st.session_state.supplemental = None
    
    # File uploaders
    term_sheet = st.file_uploader("Upload Term Sheet (PDF)", type="pdf", key="term_sheet_uploader")
    pricing_table = st.file_uploader("Upload Pricing Table (XLSX)", type="xlsx", key="pricing_table_uploader")
    supplemental = st.file_uploader("Upload Supplemental Document (Optional)", type=["pdf", "jpg", "jpeg"], key="supplemental_uploader")
    
    # Update session state if files are uploaded
    if term_sheet:
        st.session_state.term_sheet = term_sheet
    if pricing_table:
        st.session_state.pricing_table = pricing_table
    if supplemental:
        st.session_state.supplemental = supplemental
    
    # Display uploaded file names
    if st.session_state.term_sheet:
        st.write(f"Term Sheet: {st.session_state.term_sheet.name}")
    if st.session_state.pricing_table:
        st.write(f"Pricing Table: {st.session_state.pricing_table.name}")
    if st.session_state.supplemental:
        st.write(f"Supplemental Document: {st.session_state.supplemental.name}")
    
    # Generate Memo button
    if st.session_state.term_sheet and st.session_state.pricing_table:
        if st.button("Generate Memo"):
            with st.spinner("Processing files and generating memo..."):
                term_sheet_text = process_pdf(st.session_state.term_sheet)
                pricing_data = process_excel(st.session_state.pricing_table)
                supplemental_text = process_supplemental(st.session_state.supplemental) if st.session_state.supplemental else ""
                
                memo_text = generate_memo(term_sheet_text, pricing_data, supplemental_text)
                
                doc_bytes = create_word_document(memo_text)
                
                s3_link = save_to_s3(doc_bytes)
                
            st.success("Memo generated successfully!")
            st.markdown(f"[Download Memo]({s3_link})")
    else:
        st.write("Please upload both the Term Sheet and Pricing Table to generate the memo.")

if __name__ == "__main__":
    main()

