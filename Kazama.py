import imaplib
import email
import pandas as pd
import nltk
from io import BytesIO
import fitz  # PyMuPDF
import streamlit as st
from transformers import T5ForConditionalGeneration, T5Tokenizer
import sentencepiece

# Download NLTK resources
nltk.download('punkt')

# Streamlit app title
st.title("Automate2PDF: Simplified Data Transfer")

# Create input fields for the user, password, and email address
user = st.text_input("Enter your email address")
password = st.text_input("Enter your email password", type="password")
pdf_email_address = st.text_input("Enter the email address from which to extract PDFs")
selected_date = st.text_input("Enter the date (YYYY-MM-DD) to filter emails")

# Function to extract chapters from PDF using PyMuPDF
def extract_chapters_from_pdf(pdf_bytes):
    pdf_document = fitz.open(stream=pdf_bytes, filetype="pdf")
    chapters = []

    for page_num in range(pdf_document.page_count):
        page_text = pdf_document[page_num].get_text()

        # Assuming chapters are separated by a keyword, adjust this based on your document structure
        chapter_start_keywords = ["Chapter", "CHAPTER", "Section", "SECTION"]
        
        for start_keyword in chapter_start_keywords:
            if start_keyword in page_text:
                # Split the text at the chapter start keyword
                chapter_text = page_text.split(start_keyword, 1)[-1]
                chapters.append(chapter_text)

    return chapters

# Function to summarize text using T5 model
def summarize_text_t5(text):
    model = T5ForConditionalGeneration.from_pretrained('t5-small')
    tokenizer = T5Tokenizer.from_pretrained('t5-small')
    inputs = tokenizer.encode("summarize: " + text, return_tensors="pt", max_length=512, truncation=True)
    summary_ids = model.generate(inputs, max_length=150, min_length=30, length_penalty=2.0, num_beams=4, early_stopping=True)
    summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)
    return summary

# Convert date format for IMAP search
try:
    imap_date_format = pd.to_datetime(selected_date).strftime("%d-%b-%Y").upper()
except Exception as e:
    st.error(f"Error converting date format: {str(e)}")
    st.stop()

if st.button("Fetch and Display PDF Summaries"):
    try:
        # URL for IMAP connection
        imap_url = 'imap.gmail.com'

        # Connection with GMAIL using SSL
        with imaplib.IMAP4_SSL(imap_url) as my_mail:
            # Log in using user and password
            my_mail.login(user, password)

            # Select the Inbox to fetch messages
            my_mail.select('inbox')

            # Define the key and value for email search
            key = 'SINCE'
            value = imap_date_format  # Use the user-specified date to search
            _, data = my_mail.search(None, key, value)

            mail_id_list = data[0].split()

            info_list = []

            # Iterate through messages
            for num in mail_id_list:
                typ, data = my_mail.fetch(num, '(RFC822)')
                msg = email.message_from_bytes(data[0][1])

                for part in msg.walk():
                    if part.get_content_type() == 'application/pdf':
                        # Extract email date
                        email_date = msg["Date"]

                        # Extract chapters from PDF using PyMuPDF
                        pdf_bytes = part.get_payload(decode=True)
                        chapters = extract_chapters_from_pdf(pdf_bytes)

                        for chapter_num, chapter_text in enumerate(chapters, start=1):
                            # Summarize each chapter using T5 model
                            summary = summarize_text_t5(chapter_text)

                            info = {"Summarized Content": summary, "Received Date": email_date, "Chapter": chapter_num}
                            info_list.append(info)

            # Display the summarized content
            for info in info_list:
                st.subheader(f"Chapter {info['Chapter']} - Received Date: {info['Received Date']}")
                st.write(info["Summarized Content"])

            # Download button
            if st.button("Download Summaries as Text File"):
                summary_text = "\n\n".join(f"Chapter {info['Chapter']} - Received Date: {info['Received Date']}\n{info['Summarized Content']}" for info in info_list)
                st.download_button(
                    label="Download Summaries",
                    data=summary_text,
                    key="download_summaries_txt",
                    file_name="summaries.txt",
                )

    except Exception as e:
        st.error(f"An error occurred during IMAP connection: {str(e)}")
