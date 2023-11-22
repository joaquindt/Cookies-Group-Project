import smtplib
import mysql.connector
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import concurrent.futures
import threading
import time
import random

database_lock = threading.Lock()
def send_email_via_gmail():
    time.sleep(random.randint(1, 30))
    global database_lock
    # Connect to the database
    database_lock.acquire()
    cnx = mysql.connector.connect(user='root', password='Fuchsstern',
                              host='127.0.0.1',
                              database='example')
    cursor = cnx.cursor()
    # Fetch account information from the database
    cursor.execute("SELECT username, app_password, recipient, cookie_type, cookie_quantity FROM email_accounts")
    
    accounts = cursor.fetchall()
    account = accounts[0]
    cursor.execute("SELECT username, app_password, recipient, cookie_type, cookie_quantity FROM email_accounts")
    for (username, app_password, recipient, cookie_type, cookie_quantity) in cursor:
        print(f"Account: {username}, App Password: {app_password}, Recipient: {recipient}, cookie_type: {cookie_type}, cookie_quantity: {cookie_quantity}")


    delete_query = """
    DELETE FROM email_accounts 
    WHERE username = %s AND app_password = %s AND recipient = %s AND cookie_type = %s AND cookie_quantity = %s
    """
    cursor.execute(delete_query, (account[0], account[1], account[2], account[3], account[4]))

    print("test")
    cursor.execute("SELECT username, app_password, recipient, cookie_type, cookie_quantity FROM email_accounts")
    for (username, app_password, recipient, cookie_type, cookie_quantity) in cursor:
        print(f"Account: {username}, App Password: {app_password}, Recipient: {recipient}, cookie_type: {cookie_type}, cookie_quantity: {cookie_quantity}")
    database_lock.release()
    message = "This is a test email from Gmail."

    try: 
        msg = MIMEMultipart()
        msg['From'] = account[0]  # username
        msg['To'] = account[2]    # recipient
        msg['Subject'] = f"{account[0]},{account[3]},{account[4]}"
        msg.attach(MIMEText(message, 'plain'))

        server = smtplib.SMTP('smtp.gmail.com', 587)
        server.starttls()
        server.login(account[0], account[1])  # username and app_password
        server.send_message(msg)
        print(f"Email sent from {account[0]} to {account[2]}")
    except Exception as e:
        print(f"Error sending email from {account[0]}: {e}")
    finally:
        server.quit()

    
    cursor.close()
    cnx.close()


#send_email_via_gmail()

with concurrent.futures.ThreadPoolExecutor() as executor:
    futures = [executor.submit(send_email_via_gmail) for _ in range(3)]  # Adjust the range as needed based on the number of emails you want to send
    for future in concurrent.futures.as_completed(futures):
        future.result()
