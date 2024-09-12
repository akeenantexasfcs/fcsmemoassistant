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
openai.api_key = os.getenv("OPENAI_API_KEY")
ASSISTANT_ID = os.getenv("OPENAI_ASSISTANT_ID")
AWS_ACCESS_KEY = os.getenv("AWS_ACCESS_KEY")
AWS_SECRET_KEY = os.getenv("AWS_SECRET_KEY")
AWS_REGION = os.getenv("AWS_REGION")
S3_BUCKET_NAME = os.getenv("S3_BUCKET_NAME")

# Initialize OpenAI client
client = openai.Client()

# Initialize AWS S3 client
s3 = boto3.client('s3', 
                  aws_access_key_id=AWS_ACCESS_KEY, 
                  aws_secret_access_key=AWS_SECRET_KEY,
                  region_name=AWS_REGION)

def process_pdf(file):
    pdf_reader = PdfReader(file)
    text = ""
    for page in pdf_reader.pages:
        text += page.extract_text()
    return text

def process_excel(file):
    workbook = load_workbook(file)
    sheet = workbook.active
    data = []
    for row in sheet.iter_rows(values_only=True):
        data.append(row)
    return str(data)  # Convert to string for simplicity

def process_supplemental(file):
    if file.type == "application/pdf":
        return process_pdf(file)
    elif file.type in ["image/jpeg", "image/jpg"]:
        image = Image.open(file)
        # Here you might want to use OCR to extract text from the image
        # For simplicity, we'll just return a placeholder
        return "Image content placeholder"
    else:
        return "Unsupported file type"

def generate_memo(term_sheet_text, pricing_data, supplemental_text):
    thread = client.beta.threads.create()
    
    # Add messages to the thread
    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content=f"Term Sheet: {term_sheet_text}\n\nPricing Data: {pricing_data}\n\nSupplemental Info: {supplemental_text}"
    )
    
    # Run the assistant
    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=ASSISTANT_ID,
        instructions="Please write a memo based on the provided information."
    )
    
    # Wait for the run to complete
    while True:
        run_status = client.beta.threads.runs.retrieve(thread_id=thread.id, run_id=run.id)
        if run_status.status == 'completed':
            break
        time.sleep(1)
    
    # Retrieve the assistant's response
    messages = client.beta.threads.messages.list(thread_id=thread.id)
    return messages.data[0].content[0].text.value

def create_word_document(memo_text):
    doc = docx.Document()
    doc.add_paragraph(memo_text)
    bio = io.BytesIO()
    doc.save(bio)
    return bio.getvalue()

def save_to_s3(doc_bytes):
    filename = f"memo_{int(time.time())}.docx"
    s3.put_object(Bucket=S3_BUCKET_NAME, Key=filename, Body=doc_bytes)
    return f"https://{S3_BUCKET_NAME}.s3.amazonaws.com/{filename}"

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

