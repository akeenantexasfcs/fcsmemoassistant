#!/usr/bin/env python
# coding: utf-8

# In[ ]:


import streamlit as st
import boto3
import time
from botocore.exceptions import NoCredentialsError
import pandas as pd
from io import BytesIO

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

# Initialize default values for the Loan Pricing Calculator
def initialize_defaults():
    st.session_state.default_values = {
        'Loan Type': "Insert Loan Type",
        'PD/LGD': "Insert PD/LGD",
        'Company Name': "Insert Company Name",
        'Eligibility': "Directly Eligible",
        'Patronage': "Non-Patronage",
        'Revolver': "No",
        'Direct Note Patronage (%)': 0.40,
        'Fee in lieu (%)': 0.00,
        'SPREAD (%)': 0.00,
        'CSA (%)': 0.00,
        'SOFR (%)': 0.00,
        'COFs (%)': 0.00,
        'Upfront Fee (%)': 0.00,
        'Servicing Fee (%)': 0.15,
        'Years to Maturity': 5.0,
        'Unused Fee (%)': 0.00
    }

# Reset callback function for Loan Pricing Calculator
def reset_defaults():
    if 'default_values' not in st.session_state:
        initialize_defaults()
    st.session_state.loans = [st.session_state.default_values.copy() for _ in range(4)]
    st.session_state.current_loan_count = 1

# Initialize session state for Loan Pricing Calculator
if 'loans' not in st.session_state:
    initialize_defaults()
    reset_defaults()

# Main Streamlit application
def main():
    st.title("PDF to Raw Text Converter and Loan Pricing Calculator")

    if check_password():
        # Section I
        st.header("Section I: PDF to Raw Text Converter using AWS Textract")
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

        # Section II
        st.header("Section II: PDF to Raw Text Converter II - [Suggested: Marketing Presentation]")
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

        st.markdown("---")  # Separator between sections

        # Section III
        st.header("Section III: Loan Pricing Calculator")
        create_loan_calculator()

# Function to create the Loan Pricing Calculator
def create_loan_calculator():
    # Show inputs for each loan
    for i in range(st.session_state.current_loan_count):
        with st.expander(f"Loan {i + 1} Details", expanded=True):
            loan_data = st.session_state.loans[i]
            # Loan Type Input
            loan_data['Loan Type'] = st.text_input(f"Loan Type {i + 1}", value=loan_data['Loan Type'], key=f'Loan Type {i}')

            # PD/LGD, Company Name, and Eligibility Inputs at the top
            loan_data['PD/LGD'] = st.text_input(f"PD/LGD {i + 1}", value=loan_data['PD/LGD'], key=f'PD/LGD {i}')
            loan_data['Company Name'] = st.text_input(f"Company Name {i + 1}", value=loan_data['Company Name'], key=f'Company Name {i}')
            eligibility_options = ["Directly Eligible", "Similar Entity"]
            loan_data['Eligibility'] = st.radio(f"Eligibility {i + 1}", options=eligibility_options, index=eligibility_options.index(loan_data['Eligibility']), key=f'Eligibility {i}')

            # Patronage Radio Button
            patronage_options = ["Patronage", "Non-Patronage"]
            loan_data['Patronage'] = st.radio(f"Patronage {i + 1}", options=patronage_options, index=patronage_options.index(loan_data['Patronage']), key=f'Patronage {i}')

            # Revolver Radio Button
            revolver_options = ["Yes", "No"]
            loan_data['Revolver'] = st.radio(f"Revolver {i + 1}", options=revolver_options, index=revolver_options.index(loan_data['Revolver']), key=f'Revolver {i}')

            # Unused Fee Input (shown if Revolver is "Yes")
            if loan_data['Revolver'] == "Yes":
                loan_data['Unused Fee (%)'] = st.number_input(f"Unused Fee (%) {i + 1}", value=loan_data['Unused Fee (%)'], step=0.01, format='%.2f', key=f'Unused Fee {i}')
            else:
                loan_data['Unused Fee (%)'] = 0.00

            # Direct Note Patronage Input
            loan_data['Direct Note Patronage (%)'] = st.number_input(f"Direct Note Patronage (%) {i + 1}", value=loan_data['Direct Note Patronage (%)'], step=0.01, format="%.2f", key=f'Direct Note Patronage {i}')

            # Fee in lieu Input
            loan_data['Fee in lieu (%)'] = st.number_input(f"Fee in lieu (%) {i + 1}", value=loan_data['Fee in lieu (%)'], step=0.01, format="%.2f", key=f'Fee in lieu {i}')

            # SPREAD, CSA, SOFR, and COFs Inputs
            loan_data['SPREAD (%)'] = st.number_input(f"SPREAD (%) {i + 1}", value=loan_data['SPREAD (%)'], step=0.01, format="%.2f", key=f'SPREAD {i}')
            loan_data['CSA (%)'] = st.number_input(f"CSA (%) {i + 1}", value=loan_data['CSA (%)'], step=0.01, format="%.2f", key=f'CSA {i}')
            loan_data['SOFR (%)'] = st.number_input(f"SOFR (%) {i + 1}", value=loan_data['SOFR (%)'], step=0.01, format="%.2f", key=f'SOFR {i}')
            loan_data['COFs (%)'] = st.number_input(f"COFs (%) {i + 1}", value=loan_data['COFs (%)'], step=0.01, format="%.2f", key=f'COFs {i}')

            # Upfront Fee Input
            loan_data['Upfront Fee (%)'] = st.number_input(f"Upfront Fee (%) {i + 1}", value=loan_data['Upfront Fee (%)'], step=0.01, format="%.2f", key=f'Upfront Fee {i}')

            # Servicing Fee Input
            loan_data['Servicing Fee (%)'] = st.number_input(f"Servicing Fee (%) {i + 1}", value=loan_data['Servicing Fee (%)'], step=0.01, format="%.2f", key=f'Servicing Fee {i}')

            # Years to Maturity Slider
            loan_data['Years to Maturity'] = st.slider(f"Years to Maturity {i + 1}", 0.0, 30.0, value=loan_data['Years to Maturity'], step=0.5, key=f'Years to Maturity {i}')

            # Calculate Association Spread
            assoc_spread = loan_data['SPREAD (%)'] + loan_data['CSA (%)'] + loan_data['SOFR (%)'] - loan_data['COFs (%)']

            # Calculate Income and Capital Yield
            income_yield = assoc_spread + loan_data['Direct Note Patronage (%)'] + (loan_data['Upfront Fee (%)'] / loan_data['Years to Maturity']) - loan_data['Servicing Fee (%)']
            patronage_value = 0.71 if loan_data['Patronage'] == "Patronage" else 0
            capital_yield = income_yield - patronage_value

            # Create DataFrame for main components and a separate one for details
            data_main = {
                'Component': ['Assoc Spread', 'Patronage', 'Fee in lieu', 'Servicing Fee', 'Upfront Fee', 'Direct Note Pat', 'Income Yield', 'Capital Yield'],
                f"{loan_data['Loan Type']}": [f"{assoc_spread:.2f}%", f"-{patronage_value:.2f}%", f"{loan_data['Fee in lieu (%)']:.2f}%", f"-{loan_data['Servicing Fee (%)']:.2f}%", f"{(loan_data['Upfront Fee (%)'] / loan_data['Years to Maturity']):.2f}%", f"{loan_data['Direct Note Patronage (%)']:.2f}%", f"{income_yield:.2f}%", f"{capital_yield:.2f}%"]
            }
            data_secondary = {
                'ID': ['PD', 'Name', 'Eligibility', 'Years to Maturity', 'Unused Fee'],
                'Value': [loan_data['PD/LGD'], loan_data['Company Name'], loan_data['Eligibility'], f"{loan_data['Years to Maturity']:.1f} years", f"{loan_data['Unused Fee (%)']:.2f}%"]
            }
            df_main = pd.DataFrame(data_main)
            df_secondary = pd.DataFrame(data_secondary)

            # Display the DataFrames
            st.write("Pricing Information:")
            st.dataframe(df_main)
            st.write("Details:")
            st.dataframe(df_secondary)

    # Add a new loan button if less than 4 loans
    if st.session_state.current_loan_count < 4:
        if st.button("Add Another Loan"):
            st.session_state.current_loan_count += 1

    # Export to Excel with all information
    if st.button("Export to Excel"):
        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            for i in range(st.session_state.current_loan_count):
                loan_data = st.session_state.loans[i]

                # Calculate values
                assoc_spread = loan_data['SPREAD (%)'] + loan_data['CSA (%)'] + loan_data['SOFR (%)'] - loan_data['COFs (%)']
                patronage_value = 0.71 if loan_data['Patronage'] == "Patronage" else 0
                income_yield = assoc_spread + loan_data['Direct Note Patronage (%)'] + (loan_data['Upfront Fee (%)'] / loan_data['Years to Maturity']) - loan_data['Servicing Fee (%)']
                capital_yield = income_yield - patronage_value

                # Create DataFrame for main pricing information
                data_main = {
                    'Component': ['Assoc Spread', 'Patronage', 'Fee in lieu', 'Servicing Fee', 'Upfront Fee', 'Direct Note Pat', 'Income Yield', 'Capital Yield'],
                    f"{loan_data['Loan Type']}": [f"{assoc_spread:.2f}%", f"-{patronage_value:.2f}%", f"{loan_data['Fee in lieu (%)']:.2f}%", f"-{loan_data['Servicing Fee (%)']:.2f}%", f"{(loan_data['Upfront Fee (%)'] / loan_data['Years to Maturity']):.2f}%", f"{loan_data['Direct Note Patronage (%)']:.2f}%", f"{income_yield:.2f}%", f"{capital_yield:.2f}%"]
                }
                df_main = pd.DataFrame(data_main)

                # Create DataFrame for additional details
                data_details = {
                    'ID': ['Loan Type', 'PD/LGD', 'Company Name', 'Eligibility', 'Patronage', 'Revolver', 'Direct Note Patronage (%)', 'Fee in lieu (%)', 'SPREAD (%)', 'CSA (%)', 'SOFR (%)', 'COFs (%)', 'Upfront Fee (%)', 'Servicing Fee (%)', 'Years to Maturity', 'Unused Fee (%)'],
                    'Value': [loan_data['Loan Type'], loan_data['PD/LGD'], loan_data['Company Name'], loan_data['Eligibility'], loan_data['Patronage'], loan_data['Revolver'], f"{loan_data['Direct Note Patronage (%)']:.2f}%", f"{loan_data['Fee in lieu (%)']:.2f}%", f"{loan_data['SPREAD (%)']:.2f}%", f"{loan_data['CSA (%)']:.2f}%", f"{loan_data['SOFR (%)']:.2f}%", f"{loan_data['COFs (%)']:.2f}%", f"{loan_data['Upfront Fee (%)']:.2f}%", f"{loan_data['Servicing Fee (%)']:.2f}%", f"{loan_data['Years to Maturity']:.1f} years", f"{loan_data['Unused Fee (%)']:.2f}%"]
                }
                df_details = pd.DataFrame(data_details)

                # Write to Excel
                df_main.to_excel(writer, sheet_name=f'Loan {i + 1}', startrow=1, index=False)
                df_details.to_excel(writer, sheet_name=f'Loan {i + 1}', startrow=len(df_main) + 3, index=False)

                # Add basic formatting
                workbook = writer.book
                worksheet = writer.sheets[f'Loan {i + 1}']
                header_format = workbook.add_format({'bold': True})

                # Apply formatting to main pricing information
                for col_num, value in enumerate(df_main.columns.values):
                    worksheet.write(0, col_num, value, header_format)

                # Apply formatting to additional details
                details_start_row = len(df_main) + 3
                for col_num, value in enumerate(df_details.columns.values):
                    worksheet.write(details_start_row - 1, col_num, value, header_format)

        output.seek(0)
        st.download_button(
            label="Download Excel file",
            data=output.getvalue(),
            file_name="loan_pricing_calculations.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        )

    # Clear button with a callback to reset defaults
    st.button("Reset", on_click=reset_defaults)

if __name__ == "__main__":
    main()

