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

# Set up configuration
OPEN_AI_API_KEY = os.getenv("OPEN_AI_API_KEY")
ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# Initialize OpenAI client
client = openai.Client(api_key=OPEN_AI_API_KEY)

# Initialize AWS S3 client
s3 = boto3.client('s3', 
                  aws_access_key_id=AWS_ACCESS_KEY, 
                  aws_secret_access_key=AWS_SECRET_KEY,
                  region_name=AWS_REGION)

# ... (keep all the processing functions as they were) ...

def main():
    st.title("AI Memo Writer")
    
    # Initialize session state
    if 'stage' not in st.session_state:
        st.session_state.stage = 'initial'
    
    if st.session_state.stage == 'initial':
        if st.button("Commence"):
            st.session_state.stage = 'upload'
    
    if st.session_state.stage == 'upload':
        st.session_state.term_sheet = st.file_uploader("Upload Term Sheet (PDF)", type="pdf", key="term_sheet")
        st.session_state.pricing_table = st.file_uploader("Upload Pricing Table (XLSX)", type="xlsx", key="pricing_table")
        st.session_state.supplemental = st.file_uploader("Upload Supplemental Document (Optional)", type=["pdf", "jpg", "jpeg"], key="supplemental")
        
        if st.session_state.term_sheet and st.session_state.pricing_table:
            if st.button("Generate Memo"):
                st.session_state.stage = 'generate'
    
    if st.session_state.stage == 'generate':
        with st.spinner("Processing files and generating memo..."):
            term_sheet_text = process_pdf(st.session_state.term_sheet)
            pricing_data = process_excel(st.session_state.pricing_table)
            supplemental_text = process_supplemental(st.session_state.supplemental)
            
            if term_sheet_text and pricing_data:
                memo_text = generate_memo(term_sheet_text, pricing_data, supplemental_text)
                
                if memo_text:
                    doc_bytes = create_word_document(memo_text)
                    
                    if doc_bytes:
                        s3_link = save_to_s3(doc_bytes)
                        
                        if s3_link:
                            st.success("Memo generated successfully!")
                            st.markdown(f"[Download Memo]({s3_link})")
                        else:
                            st.error("Failed to save memo to S3.")
                    else:
                        st.error("Failed to create Word document.")
                else:
                    st.error("Failed to generate memo.")
            else:
                st.error("Failed to process input files.")
        
        if st.button("Start Over"):
            st.session_state.stage = 'initial'
            # Clear the uploaded files
            st.session_state.term_sheet = None
            st.session_state.pricing_table = None
            st.session_state.supplemental = None

if __name__ == "__main__":
    main()

