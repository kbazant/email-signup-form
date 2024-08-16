from flask import Flask, render_template, request, redirect, url_for
from azure.data.tables import TableServiceClient
from azure.communication.email import EmailClient
from azure.core.credentials import AzureKeyCredential
from config import Config
import uuid
import base64
import logging

app = Flask(__name__)
app.config.from_object(Config)

# Initialize Azure Table Service Client
table_service_client = TableServiceClient.from_connection_string(app.config['AZURE_CONNECTION_STRING'])
table_client = table_service_client.get_table_client(table_name="subscribers")

def add_padding(base64_string):
    """Add padding to a base64 string if necessary."""
    return base64_string + '=' * (-len(base64_string) % 4)

# Initialize Azure Communication Service Email Client
email_credential = AzureKeyCredential(add_padding(app.config['AZURE_COMMUNICATION_SERVICE_KEY']))
email_client = EmailClient(app.config['AZURE_COMMUNICATION_SERVICE_ENDPOINT'], email_credential)

# Configure logging
logging.basicConfig(level=logging.DEBUG)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        firstname = request.form['firstname']
        email = request.form['email']
        
        # Generate a unique identifier for RowKey
        unique_id = str(uuid.uuid4())
        
        # Insert data into Azure Table Storage
        entity = {
            'PartitionKey': 'subscribers',
            'RowKey': unique_id,
            'firstname': firstname,
            'email': email
        }
        table_client.create_entity(entity=entity)
        
        # Prepare and send email
        message = {
            "content": {
                "subject": "Welcome to our service",
                "plainText": f"Hello {firstname},\n\nThank you for registering with us!",
                "html": f"<html><p>Hello {firstname},</p><p>Thank you for registering with us!</p></html>"
            },
            "recipients": {
                "to": [
                    {
                        "address": email,
                        "displayName": firstname
                    }
                ]
            },
            "senderAddress": app.config['AZURE_COMMUNICATION_SERVICE_SENDER']
        }
        
        try:
            logging.debug("Sending email to %s", email)
            poller = email_client.begin_send(message)
            result = poller.result()
            logging.debug("Email sent successfully: %s", result)
        except Exception as e:
            logging.error("Failed to send email: %s", e)
        
        return redirect(url_for('index'))
    
    return render_template('signup.html')

if __name__ == '__main__':
    app.run()