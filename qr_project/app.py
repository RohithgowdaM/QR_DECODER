from flask import Flask, request, jsonify, render_template
import numpy as np
import cv2
import datetime
import requests
from urllib.parse import urlencode
import json

app = Flask(__name__)

# Function to decode QR code using OpenCV
def decode_qr(image):
    # Convert the image to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Create the QRCodeDetector object
    detector = cv2.QRCodeDetector()
    
    # Detect and decode the QR code
    value, pts, qr_code = detector.detectAndDecode(gray)
    
    if value:
        return value  # Return the decoded value from the QR code
    return None  # Return None if no QR code is found

# Replace with your actual SheetDB URL
sheetdb_url = "https://sheetdb.io/api/v1/91s1zw3wghp5q"

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_photo():
    if 'photo' not in request.files:
        return jsonify({"error": "No photo uploaded"}), 400

    # Process uploaded image
    file = request.files['photo']
    np_img = np.frombuffer(file.read(), np.uint8)
    img = cv2.imdecode(np_img, cv2.IMREAD_COLOR)

    # Decode QR code
    qr_data = decode_qr(img)
    if not qr_data:
        return jsonify({"error": "No QR code detected"}), 400
    
    response_messages = []

    try:
        qr_data = json.loads(qr_data)  # Assuming the QR code contains JSON data
        Email = qr_data.get("Email")
        Phone = qr_data.get("Phone")
        timestamp = datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')

        # Search the entry in SheetDB
        search_params = {"Email address": Email, "Phone Number": Phone}
        query_string = urlencode(search_params)
        response = requests.get(f"{sheetdb_url}/search?{query_string}")
        response_data = response.json()

        if response.status_code == 200 and response_data:
            # Get the row ID for updating
            row_id = response_data[0].get("id")
            name= response_data[0].get("Full Name")
            if row_id:
                update_data = {"Attended Event?": "Attended"}
                update_response = requests.patch(
                    f"{sheetdb_url}/id/{row_id}", json={"data": update_data}
                )

                if update_response.status_code == 200:
                    response_messages.append({
                        "Email": Email,
                        "Phone": Phone,
                        "Name":name,
                        "message": f"Attendance marked for {name}."
                    })
                else:
                    response_messages.append({
                        "Email": Email,
                        "Phone": Phone,
                        "message": f"Failed to update status for {Email}."
                    })
            else:
                response_messages.append({
                    "Email": Email,
                    "Phone": Phone,
                    "message": f"Could not find a valid row ID for {Email}."
                })
        else:
            response_messages.append({
                "Email": Email,
                "Phone": Phone,
                "message": f"No matching entry found for {Email}."
            })

    except Exception as e:
        print(f"Error processing QR Code: {str(e)}")
        response_messages.append({
            "Email": None,
            "Phone": None,
            "message": f"Error processing QR code: {str(e)}"
        })

    return jsonify({"responses": response_messages})

if __name__ == '__main__':
    app.run(debug=True)
