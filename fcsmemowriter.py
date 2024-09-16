#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import streamlit as st
import boto3
import time
from botocore.exceptions import NoCredentialsError

# Initialize boto3 session with credentials from secrets.toml
session = boto3.Session(
    aws_access_key_id=st.secrets["aws"]["aws_access_key_id"],
    aws_secret_access_key=st.secrets["aws"]["aws_secret_access_key"],
    region_name=st.secrets["aws"]["region_name"]
)

# Create clients
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

# Main Streamlit application
def main():
    st.title("PDF to Raw Text Converter using AWS Textract")

    if check_password():
        # Section 1
        st.header("PDF to Raw Text Converter using AWS Textract")
        uploaded_file1 = st.file_uploader("Upload a PDF file", type="pdf", key="uploader1")
        if uploaded_file1 is not None:
            # Access the S3 bucket name from secrets
            bucket_name = st.secrets["aws"]["s3_bucket_name"]
            object_name = uploaded_file1.name

            # Upload the PDF file to S3
            with st.spinner('Uploading file to S3...'):
                upload_to_s3(uploaded_file1, bucket_name, object_name)

            # Start the text detection job
            with st.spinner('Starting text detection job...'):
                job_id = start_text_detection(bucket_name, object_name)

            # Wait for the job to complete
            with st.spinner('Processing the document...'):
                if is_job_complete(job_id):
                    # Retrieve and display the extracted text
                    raw_text = get_text_from_response(job_id)
                    st.success('Text extraction completed!')
                    st.text_area("Extracted Text", raw_text, height=400)
        else:
            st.info("Please upload a PDF file to begin.")

        st.markdown("---")  # Separator between sections

        # Section 2
        st.header("PDF to Raw Text Converter II - [Suggested: Marketing Presentation]")
        uploaded_file2 = st.file_uploader("Upload a second PDF file", type="pdf", key="uploader2")
        if uploaded_file2 is not None:
            # Access the S3 bucket name from secrets
            bucket_name = st.secrets["aws"]["s3_bucket_name"]
            object_name = uploaded_file2.name

            # Upload the PDF file to S3
            with st.spinner('Uploading second file to S3...'):
                upload_to_s3(uploaded_file2, bucket_name, object_name)

            # Start the text detection job
            with st.spinner('Starting text detection job for the second file...'):
                job_id = start_text_detection(bucket_name, object_name)

            # Wait for the job to complete
            with st.spinner('Processing the second document...'):
                if is_job_complete(job_id):
                    # Retrieve and display the extracted text
                    raw_text = get_text_from_response(job_id)
                    st.success('Second text extraction completed!')
                    st.text_area("Extracted Text from Second File", raw_text, height=400)
        else:
            st.info("Please upload a second PDF file to begin.")

if __name__ == "__main__":
    main()

