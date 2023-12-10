import imaplib
import email
import pandas as pd
import nltk
from io import BytesIO
import fitz  # PyMuPDF
import streamlit as st
from transformers import T5ForConditionalGeneration, T5Tokenizer

# Download NLTK resources
nltk.download('punkt')

# Streamlit app title
st.title("Automate2PDF: Simplified Data Transfer")

# Create input fields for the user, password, and email address
user = st.text_input("Enter your email address")
password = st.text_input("Enter your email password", type="password")
pdf_email_address = st.text_input("Enter the email address from which to extract PDFs")

# Function to extract text from PDF using PyMuPDF
def extract_text_from_pdf(pdf_bytes):
    pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
    text = ""
    for page_num in range(pdf_document.page_count):
        text += pdf_document[page_num].get_text()
    return text

# Function to summarize text using T5 model
def summarize_text_t5(text):
    model = T5ForConditionalGeneration.from_pretrained('t5-small')
    tokenizer = T5Tokenizer.from_pretrained('t5-small')
    inputs = tokenizer.encode("summarize: " + text, return_tensors="pt", max_length=512, truncation=True)
    summary_ids = model.generate(inputs, max_length=150, min_length=30, length_penalty=2.0, num_beams=4, early_stopping=True)
    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    return summary
# ... (Previous code remains the same)

# IMAP client setup for fetching emails
if st.button("Fetch and Display PDF Summaries"):
    try:
        # IMAP connection setup
        mail = imaplib.IMAP4_SSL('imap.gmail.com')
        mail.login(user, password)
        mail.select("inbox")

        # Search for emails based on the specified date
        result, data = mail.search(None, f'(SINCE {selected_date})')

        # Iterate through the fetched email IDs
        for num in data[0].split():
            result, data = mail.fetch(num, "(RFC822)")
            raw_email = data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Process the email content
            email_date = msg["Date"]
            email_subject = msg["Subject"]

            for part in msg.walk():
                if part.get_content_type() == "application/pdf":
                    # Extract text from PDF using PyMuPDF
                    pdf_bytes = part.get_payload(decode=True)
                    pdf_text = extract_text_from_pdf(pdf_bytes)

                    # Summarize the PDF content using T5-based summarizer
                    summary = summarize_text_t5(pdf_text)

                    # Display the summarized content
                    st.subheader(f"Received Date: {email_date}, Subject: {email_subject}")
                    st.write(summary)

    except Exception as e:
        st.error(f"An error occurred during IMAP connection: {str(e)}")
