from bs4 import BeautifulSoup
from selenium import webdriver
from google_auth_oauthlib.flow import InstalledAppFlow
from google.auth.transport.requests import Request
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from email.mime.multipart import MIMEMultipart
from email.mime.image import MIMEImage
from email.mime.text import MIMEText

import os
import base64
import requests
import mimetypes

url = "https://www.ccilindia.com/OMRPT_2Deals.aspx"
client_id ="542648783693-e1e6uvevlh2cpj67a38g1684hqiaeqel.apps.googleusercontent.com"
client_secret = "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"
SCOPES = ['https://www.googleapis.com/auth/gmail.send']


def scrape():
    soup = BeautifulSoup(s.get(url).content, "html.parser")
    # print(soup.prettify())
    sl = 0.00
    ol = 0.00
    u_ol = 0.00
    u_sl = 0.00
    og = 0
    # Standard Lot Total value
    table = soup.find('table', id='grdNDSOMReg')
    if (table != None):
        rows = table.select('tr')
        data = rows[-2].select('td')
        sl = float(data[-1].get_text())
    # Odd Lot Total Value
    table_OL = soup.find('table', id='grdNDSOMOL')
    if (table_OL != None):
        rows_OL = table_OL.select('tr')
        data_OL = rows_OL[-2].select('td')
        ol = float(data_OL[-1].get_text())
    # Unconfirmed Standard Lot
    U_SL = soup.find('table', id='grdNDSOMUNReg')
    if (U_SL != None):
        rows = U_SL.select('tr')
        data = rows[-2].select('td')
        u_sl = float(data[-1].get_text())
    # Unconfirmed Odd Lot
    U_OL = soup.find('table', id='grdNDSOMUNOL')
    if (U_OL != None):
        rows = U_OL.select('tr')
        data = rows[-2].select('td')
        u_ol = float(data[-1].get_text())
    curr = sl + ol + u_ol + u_sl
    return curr


def take_screenshot():
    options = webdriver.ChromeOptions()
    options.headless = True
    driver = webdriver.Chrome(options=options)
    driver.get(url)
    driver.save_screenshot(screenshot_path)
    driver.quit()


def get_gmail_service():
    creds = None
    # The file token.json stores the user's access and refresh tokens, and is
    # created automatically when the authorization flow completes for the first
    # time.
    if os.path.exists('token.json'):
        creds = Credentials.from_authorized_user_file('token.json', SCOPES)
    # If there are no (valid) credentials available, let the user log in.
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            flow = InstalledAppFlow.from_client_secrets_file('credentials.json', SCOPES)
            creds = flow.run_local_server(port=3000)
        # Save the credentials for the next run
        with open('token.json', 'w') as token:
            token.write(creds.to_json())
    return build('gmail', 'v1', credentials=creds)

def create_message(sender, to, subject, message_text, file):
    message = MIMEMultipart()
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject
    msg = MIMEText(message_text)
    message.attach(msg)
    content_type, encoding = mimetypes.guess_type(file)
    main_type, sub_type = content_type.split('/', 1)
    if main_type == 'image':
        with open(file, 'rb') as fp:
            img = MIMEImage(fp.read(), _subtype=sub_type)
            img.add_header('Content-Disposition', 'attachment', filename=os.path.basename(file))
            message.attach(img)
    else:
        raise ValueError('The provided file does not seem to be an image')

    raw = base64.urlsafe_b64encode(message.as_bytes())
    raw = raw.decode()
    return {'raw': raw}


def send_message(service, user_id, message):
    try:
        message = (service.users().messages().send(userId=user_id, body=message).execute())
        print(f'Message Id: {message["id"]}')
        return message
    except Exception as error:
        print(f'An error occurred: {error}')


def orchestrate_flow():
    global s, screenshot_path
    with requests.session() as s:
        # Scrape website
        total_value = scrape()
        total_value_text = "Standard Lot + Odd Lot + Unconfirmed Standard Lot + Unconfirmed Odd Lot = " + str(
            total_value)

        # Configuration comment
        screenshot_path = "website_screenshot.png"

        # Take a screenshot
        take_screenshot()

        # Mail screenshot
        service = get_gmail_service()
        message = create_message('me', 'shubhi.moti@gmail.com', 'CCIL T+2 Reported Deals', total_value_text,
                                 screenshot_path)
        send_message(service, 'me', message)


if __name__ == "__main__":
    orchestrate_flow()





























    # # Send email
    # msg = EmailMessage()
    # msg['Subject'] = 'Website Screenshot'
    # msg['From'] = sender_email
    # msg['To'] = receiver_email
    # msg.set_content('Find attached the screenshot of the website.')
    #
    # with open(screenshot_path, 'rb') as f:
    #     file_data = f.read()
    #     msg.add_attachment(file_data, maintype='image', subtype='png', filename=screenshot_path)
    #
    # with smtplib.SMTP_SSL('smtp.gmail.com', 465) as smtp:
    #     smtp.login(sender_email, email_password)
    #     smtp.send_message(msg)
    #
    # print("Screenshot sent successfully.")
    #
    # # Clean up
    # os.remove(screenshot_path)

