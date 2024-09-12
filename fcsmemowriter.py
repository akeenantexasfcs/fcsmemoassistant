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

def process_pdf(file):
    try:
        pdf_reader = PdfReader(file)
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    except Exception as e:
        st.error(f"Error processing PDF: {str(e)}")
        return None

def process_excel(file):
    try:
        workbook = load_workbook(file)
        sheet = workbook.active
        data = []
        for row in sheet.iter_rows(values_only=True):
            data.append(row)
        return str(data)  # Convert to string for simplicity
    except Exception as e:
        st.error(f"Error processing Excel file: {str(e)}")
        return None

def process_supplemental(file):
    if file is None:
        return ""
    try:
        if file.type == "application/pdf":
            return process_pdf(file)
        elif file.type in ["image/jpeg", "image/jpg"]:
            image = Image.open(file)
            # Placeholder for image processing - you might want to implement OCR here
            return "Image content placeholder"
        else:
            return "Unsupported file type"
    except Exception as e:
        st.error(f"Error processing supplemental file: {str(e)}")
        return None

def generate_memo(term_sheet_text, pricing_data, supplemental_text):
    try:
        thread = client.beta.threads.create()
        
        client.beta.threads.messages.create(
            thread_id=thread.id,
            role="user",
            content=f"Term Sheet: {term_sheet_text}\n\nPricing Data: {pricing_data}\n\nSupplemental Info: {supplemental_text}"
        )
        
        run = client.beta.threads.runs.create(
            thread_id=thread.id,
            assistant_id=ASSISTANT_ID,
            instructions="Please write a memo based on the provided information."
        )
        
        while True:
            run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
            if run_status.status == 'completed':
                break
            time.sleep(1)
        
        messages = client.beta.threads.messages.list(thread_id=thread.id)
        return messages.data[0].content[0].text.value
    except Exception as e:
        st.error(f"Error generating memo: {str(e)}")
        return None

def create_word_document(memo_text):
    try:
        doc = docx.Document()
        doc.add_paragraph(memo_text)
        bio = io.BytesIO()
        doc.save(bio)
        return bio.getvalue()
    except Exception as e:
        st.error(f"Error creating Word document: {str(e)}")
        return None

def save_to_s3(doc_bytes):
    try:
        filename = f"memo_{int(time.time())}.docx"
        s3.put_object(Bucket=S3_BUCKET_NAME, Key=filename, Body=doc_bytes)
        return f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{filename}"
    except Exception as e:
        st.error(f"Error saving to S3: {str(e)}")
        return None

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
                    supplemental_text = process_supplemental(supplemental)
                    
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

if __name__ == "__main__":
    main()

