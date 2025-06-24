from flask import Flask, request, render_template, jsonify
import boto3
from botocore.client import Config
import firebase_admin
from firebase_admin import credentials, firestore
from dotenv import load_dotenv
import os
from datetime import datetime

import base64
import json
app = Flask(__name__)
load_dotenv()


# decode the service account
firebase_json_str = base64.b64decode(os.getenv("FIREBASE_JSON")).decode("utf-8")
firebase_cred_dict = json.loads(firebase_json_str)

cred = credentials.Certificate(firebase_cred_dict)
firebase_admin.initialize_app(cred)

db = firestore.client()

# R2 Init (S3-Compatible)
s3_client = boto3.client(
    's3',
    aws_access_key_id=os.getenv('R2_ACCESS_KEY_ID'),
    aws_secret_access_key=os.getenv('R2_SECRET_ACCESS_KEY'),
    endpoint_url=os.getenv('R2_ENDPOINT'),
    config=Config(signature_version='s3v4')
)

@app.route('/', methods=['GET'])
def index():
    return render_template('index.html')

@app.route('/', methods=['POST'])
def upload():
    email = request.form.get('email')
    file = request.files.get('image')

    if not email or not file:
        return jsonify({'success': False, 'message': 'Email and image are required.'}), 400

    try:
        # Upload image to R2
        file_name = f"images/{datetime.now().timestamp()}_{file.filename}"
        s3_client.upload_fileobj(
            file,
            os.getenv('R2_BUCKET_NAME'),
            file_name,
            ExtraArgs={'ContentType': file.content_type}
        )
        image_url = f"{os.getenv('R2_PUBLIC_URL')}/{file_name}"

        # Save to Firestore
        db.collection('submissions').document().set({
            'email': email,
            'image_url': image_url,
            'ip': request.remote_addr,
            'user_agent': request.headers.get('User-Agent'),
            'timestamp': firestore.SERVER_TIMESTAMP
        })

        return jsonify({'success': True, 'message': 'Image received! Our unicorns are analyzing it now... 🦄Results will arrive in your inbox within an hour. ⏳'})

    except Exception as e:
        return jsonify({'success': False, 'message': str(e)}), 500

if __name__ == '__main__':
    app.run(debug=True)
