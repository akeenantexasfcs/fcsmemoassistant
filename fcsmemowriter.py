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

# Load environment variables (you should set these up in your environment)
OPEN_AI_API_KEY = os.getenv("OPEN_AI_API_KEY")
ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# Initialize OpenAI client with explicit API key
client = openai.Client(api_key=OPEN_AI_API_KEY)

# Initialize AWS S3 client
s3 = boto3.client('s3', 
                  aws_access_key_id=AWS_ACCESS_KEY, 
                  aws_secret_access_key=AWS_SECRET_KEY,
                  region_name=AWS_REGION)

# ... (rest of the code remains the same)

def main():
    st.title("AI Memo Writer")
    
    if st.button("Commence"):
        term_sheet = st.file_uploader("Upload Term Sheet (PDF)", type="pdf")
        pricing_table = st.file_uploader("Upload Pricing Table (XLSX)", type="xlsx")
        supplemental = st.file_uploader("Upload Supplemental Document (Optional)", type=["pdf", "jpg", "jpeg"])
        
        if term_sheet and pricing_table:
            if st.button("Generate Memo"):
                with st.spinner("Processing files and generating memo..."):
                    term_sheet_text = process_pdf(term_sheet)
                    pricing_data = process_excel(pricing_table)
                    supplemental_text = process_supplemental(supplemental) if supplemental else ""
                    
                    memo_text = generate_memo(term_sheet_text, pricing_data, supplemental_text)
                    
                    doc_bytes = create_word_document(memo_text)
                    
                    s3_link = save_to_s3(doc_bytes)
                    
                st.success("Memo generated successfully!")
                st.markdown(f"[Download Memo]({s3_link})")

if __name__ == "__main__":
    main()

