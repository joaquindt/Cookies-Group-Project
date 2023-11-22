import mysql.connector

# Connect to the database
cnx = mysql.connector.connect(user='root', password='Fuchsstern',
                              host='127.0.0.1',
                              database='example')
cursor = cnx.cursor()

# Assuming you have a table named 'email_accounts' with columns 'username', 'app_password', and 'recipient'
accounts = [
    {'username': 'renzenbrinktest@gmail.com', 'app_password': 'bvui nuhv rzmy muvd', 'recipient': 'kristens.cookie.store@gmail.com','cookie_type':'Chocolate Chip', 'cookie_quantity':'3'},
    {'username': 'renzenbrinktest@gmail.com', 'app_password': 'bvui nuhv rzmy muvd', 'recipient': 'kristens.cookie.store@gmail.com','cookie_type':'Chocolate Chip', 'cookie_quantity':'5'}
    # Add more accounts as needed
]

# Inserting each account into the table
#for account in accounts:
#    cursor.execute(
#        "INSERT INTO email_accounts (username, app_password, recipient, cookie_type, cookie_quantity) VALUES (%s, %s, %s, %s, %s)",
#        (account['username'], account['app_password'], account['recipient'], account['cookie_type'], account['cookie_quantity'] )
#    )
#cnx.commit()

# Optionally, retrieving and printing all account details
query = "SELECT username, app_password, recipient, cookie_type, cookie_quantity FROM email_accounts"
cursor.execute(query)
for (username, app_password, recipient, cookie_type, cookie_quantity) in cursor:
    print(f"Account: {username}, App Password: {app_password}, Recipient: {recipient}, cookie_type: {cookie_type}, cookie_quantity: {cookie_quantity}")

cursor.close()
cnx.close()


