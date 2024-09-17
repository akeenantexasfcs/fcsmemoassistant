#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import streamlit as st
import boto3
import time
from botocore.exceptions import NoCredentialsError
import pandas as pd
import openai
from io import BytesIO

# Import OpenAI error classes
from openai.error import OpenAIError, InvalidRequestError, APIError, RateLimitError

# Ensure the OpenAI library is up to date
# Run: pip install --upgrade openai

# Initialize boto3 session with credentials from secrets.toml
session = boto3.Session(
    aws_access_key_id=st.secrets["aws"]["aws_access_key_id"],
    aws_secret_access_key=st.secrets["aws"]["aws_secret_access_key"],
    region_name=st.secrets["aws"]["region_name"]
)

# OpenAI API key
openai.api_key = st.secrets["openai"]["api_key"]

# Create AWS clients
s3 = session.client('s3')
textract = session.client('textract')

# Function to upload file to S3
def upload_to_s3(fileobj, bucket_name, object_name):
    try:
        s3.upload_fileobj(fileobj, bucket_name, object_name)
        print(f"File uploaded to {bucket_name}/{object_name}")
    except NoCredentialsError:
        print("AWS credentials not available.")

# Function to start Textract job
def start_text_detection(bucket_name, object_name):
    response = textract.start_document_text_detection(
        DocumentLocation={
            'S3Object': {
                'Bucket': bucket_name,
                'Name': object_name
            }
        }
    )
    return response['JobId']

# Function to check if the Textract job is complete
def is_job_complete(job_id):
    while True:
        response = textract.get_document_text_detection(JobId=job_id)
        status = response['JobStatus']
        if status == 'SUCCEEDED':
            return True
        elif status == 'FAILED':
            raise Exception("Text detection job failed.")
        else:
            time.sleep(5)  # Wait before polling again

# Function to retrieve and parse the Textract response
def get_text_from_response(job_id):
    response = textract.get_document_text_detection(JobId=job_id)
    blocks = response['Blocks']
    text = ''

    # Handle pagination
    next_token = response.get('NextToken')
    while next_token:
        response = textract.get_document_text_detection(JobId=job_id, NextToken=next_token)
        blocks.extend(response['Blocks'])
        next_token = response.get('NextToken')

    for block in blocks:
        if block['BlockType'] == 'LINE':
            text += block['Text'] + '\n'
    return text

# Password protection
def check_password():
    def password_entered():
        if st.session_state["password"] == st.secrets["passwords"]["app_password"]:
            st.session_state["password_correct"] = True
            del st.session_state["password"]  # Remove password from session state
        else:
            st.session_state["password_correct"] = False

    if "password_correct" not in st.session_state:
        # First run, show input for password
        st.text_input("Enter the password", type="password", on_change=password_entered, key="password")
        return False
    elif not st.session_state["password_correct"]:
        # Password not correct, show input + error
        st.text_input("Enter the password", type="password", on_change=password_entered, key="password")
        st.error("😕 Password incorrect")
        return False
    else:
        # Password correct
        return True

# Function to generate memo using OpenAI Assistant
def generate_memo(marketing_presentation, term_sheet, pricing):
    prompt = f"""
    Generate a memo for the executive loan committee based on the following:

    Marketing Presentation: {marketing_presentation or 'Not Provided'}
    Term Sheet: {term_sheet or 'Not Provided'}
    Pricing Details: {pricing or 'Not Provided'}
    """

    try:
        response = openai.ChatCompletion.create(
            model="gpt-4",  # Use "gpt-3.5-turbo" if you don't have access to GPT-4
            messages=[
                {"role": "system", "content": "You are an assistant that helps generate memos."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=500,
            n=1,
            stop=None,
            temperature=0.7,
        )
        return response['choices'][0]['message']['content'].strip()
    except InvalidRequestError as e:
        st.error(f"Invalid request: {e}")
        return None
    except RateLimitError as e:
        st.error(f"Rate limit exceeded: {e}")
        return None
    except APIError as e:
        st.error(f"API error: {e}")
        return None
    except OpenAIError as e:
        st.error(f"An OpenAI error occurred: {e}")
        return None
    except Exception as e:
        st.error(f"An unexpected error occurred: {e}")
        return None

# Main Streamlit application
def main():
    st.title("PDF to Raw Text Converter and Loan Pricing Calculator")

    if check_password():
        # Section I - Marketing Presentation
        st.header("Section I: Marketing Presentation (PDF to Raw Text)")
        uploaded_file1 = st.file_uploader("Upload the Marketing Presentation PDF", type="pdf", key="uploader1")
        if uploaded_file1 is not None:
            # Upload file to S3 and extract text
            bucket_name = st.secrets["aws"]["s3_bucket_name"]
            object_name = uploaded_file1.name
            upload_to_s3(uploaded_file1, bucket_name, object_name)
            job_id = start_text_detection(bucket_name, object_name)
            if is_job_complete(job_id):
                marketing_presentation_text = get_text_from_response(job_id)
                st.text_area("Extracted Marketing Presentation", marketing_presentation_text, height=400)
                st.session_state['marketing_presentation_text'] = marketing_presentation_text
        else:
            marketing_presentation_text = st.session_state.get('marketing_presentation_text', None)
            st.info("Please upload the Marketing Presentation PDF to proceed.")

        # Section II - Term Sheet
        st.header("Section II: Term Sheet (PDF to Raw Text)")
        uploaded_file2 = st.file_uploader("Upload the Term Sheet PDF", type="pdf", key="uploader2")
        if uploaded_file2 is not None:
            # Upload file to S3 and extract text
            bucket_name = st.secrets["aws"]["s3_bucket_name"]
            object_name = uploaded_file2.name
            upload_to_s3(uploaded_file2, bucket_name, object_name)
            job_id = start_text_detection(bucket_name, object_name)
            if is_job_complete(job_id):
                term_sheet_text = get_text_from_response(job_id)
                st.text_area("Extracted Term Sheet", term_sheet_text, height=400)
                st.session_state['term_sheet_text'] = term_sheet_text
        else:
            term_sheet_text = st.session_state.get('term_sheet_text', None)
            st.info("Please upload the Term Sheet PDF to proceed.")

        # Section III - Pricing Details
        st.header("Section III: Pricing Details (Enter Manually)")
        pricing_text = st.text_area("Enter Pricing Details", height=200)
        st.session_state['pricing_text'] = pricing_text if pricing_text else st.session_state.get('pricing_text', None)

        # Omnipresent Submit to Assistant button
        if st.button("Submit to Assistant"):
            # Collect available data from session state
            marketing_presentation_text = st.session_state.get('marketing_presentation_text', '')
            term_sheet_text = st.session_state.get('term_sheet_text', '')
            pricing_text = st.session_state.get('pricing_text', '')

            # Generate memo with what is available
            memo_text = generate_memo(
                marketing_presentation_text, 
                term_sheet_text, 
                pricing_text
            )
            if memo_text:
                st.success("Memo generated successfully!")
                st.text_area("Generated Memo", memo_text, height=300)
            else:
                st.error("Failed to generate memo.")

if __name__ == "__main__":
    main()

