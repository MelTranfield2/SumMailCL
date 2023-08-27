import os
import openai
import email
import imaplib
import requests
import html2text
import pandas as pd  # Import Pandas
from dotenv import load_dotenv
from email.header import decode_header
from datetime import datetime, timedelta


def fetch_emails_from_senders(sender_emails):
    try:
        load_dotenv()
        IMAP_SERVER = os.getenv('IMAP_SERVER')
        IMAP_USERNAME = os.getenv('IMAP_USERNAME')
        IMAP_PASSWORD = os.getenv('IMAP_PASSWORD')

        mail = imaplib.IMAP4_SSL(IMAP_SERVER, 993)
        mail.login(IMAP_USERNAME, IMAP_PASSWORD)

        mail.select("inbox")

        emails = []
        today = datetime.today()
        last_month = today - timedelta(days=30)
        # print("fetching emails")

        for sender_email in sender_emails:
            status, response = mail.search(None, "FROM", sender_email, "SINCE", last_month.strftime("%d-%b-%Y"))
            email_ids = response[0].split()

        for email_id in email_ids:
            status, response = mail.fetch(email_id, "(RFC822)")
            raw_email = response[0][1]
            email_message = email.message_from_bytes(raw_email)

            subject = decode_header(email_message["Subject"])[0][0]
            if isinstance(subject, bytes):
                subject = subject.decode()

            body = ""
            for part in email_message.walk():
                content_type = part.get_content_type()
                if content_type == "text/plain":
                    charset = part.get_content_charset()
                    body += str(part.get_payload(decode=True), str(charset), "ignore")

            body = html2text.html2text(body)
            chunk_size = 2037
            chunks = [body[i:i+chunk_size] for i in range(0, len(body), chunk_size)]

            emails.append((subject, chunks))

        return emails
    except Exception as e:
        print(f"An error occurred: {e}")
        return []


def summarize_chunks(chunks):
    try:

        # set up the OpenAI API client
        openai.api_key = os.getenv('OPENAI_API_KEY')

        # set up the API endpoint
        openai_url = "https://api.openai.com/v1/completions"

                # set up the request headers
        headers = {
            "Authorization": f"Bearer {openai.api_key}",
            "Content-Type": "application/json",
        }

        # summarize each chunk using OpenAI's text-davinci-003 model
        summaries = []
        for chunk in chunks:
            prompt = f"Summarize the content of this string using bulletpoints: {chunk}"
            data = {
                "model": "text-davinci-003",
                "prompt": prompt,
                "temperature": 1,
                "max_tokens": 1000
            }

            # make the HTTP request
            response = requests.post(openai_url, headers=headers, json=data)

            # extract the summary from the response
            # print(response.json())
            summary = response.json()["choices"][0]["text"].strip()
            summaries.append(summary)

        # join the bullet points into a single string
        bullet_list = "\n- ".join(summaries)

        return bullet_list
    except Exception as e:
        print(f"An error occurred: {e}") 

    #     bullet_list = "\n- ".join(summaries)
    #     return bullet_list
    # except Exception as e:
    #     print(f"An error occurred: {e}")
    #     return None


def insert_summaries_into_dataframe(emails):
    # Initialize empty DataFrame with columns 'Subject' and 'Summary'
    NewsletterSummaries = pd.DataFrame(columns=['Subject', 'Summary'])

    for subject, bullet_list in emails:
        # Append each row to the DataFrame
        NewsletterSummaries = NewsletterSummaries._append({'Subject': subject, 'Summary': bullet_list}, ignore_index=True)

    return NewsletterSummaries


def generate_newsletter_from_dataframe(df):
    try:
        # Load OpenAI API key from environment variables
        load_dotenv()
        openai_api_key = os.getenv('OPENAI_API_KEY')
        
        # Serialize DataFrame to text
        serialized_df = df.to_string()

        # Prepare the prompt for OpenAI's API
        prompt = f"Generate a newsletter from the following content:\n{serialized_df}"
        
        # API configuration
        api_url = "https://api.openai.com/v1/completions"  # Adjust if you use a different model
        headers = {
            "Authorization": f"Bearer {openai_api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": "text-davinci-003",
            "prompt": prompt,
            "max_tokens": 1700 # Adjust based on your needs
        }

        # Make the API request
        response = requests.post(api_url, headers=headers, json=payload)

        # Debug print
        print("API Response:", response.json())
        
        # Extract the generated text
        generated_text = response.json()['choices'][0]['text'].strip()
        
        return generated_text

    except Exception as e:
        print(f"An error occurred: {e}")
        return None


def main():
    sender_emails = ["csnetwork@substack.com", "info@womensequality.org.uk"]
    # print("Starting the process")
    emails = fetch_emails_from_senders(sender_emails)
    if not emails:
        print("No emails found from the specified sender.")
        return

    summarized_emails = []
    for subject, chunks in emails:
        bullet_list = summarize_chunks(chunks)
        if not bullet_list:
            print(f"Failed to summarize email with subject: {subject}")
            continue

        # print("Subject: " + subject)
        # print("Summary: \n- " + bullet_list)
        # print()

        summarized_emails.append((subject, bullet_list))

    # Insert summarized emails into DataFrame
    NewsletterSummaries = insert_summaries_into_dataframe(summarized_emails)
    print("Newsletter Summaries DataFrame:")
    print(NewsletterSummaries)
    formatted_df = NewsletterSummaries.to_string(index=False)
    print(formatted_df)


    # Generate the newsletter
    # newsletter_content = generate_newsletter_from_dataframe(NewsletterSummaries)

    # # Display the newsletter
    # if newsletter_content:
    #     print("Generated Newsletter:")
    #     print(newsletter_content)



if __name__ == "__main__":
    main()