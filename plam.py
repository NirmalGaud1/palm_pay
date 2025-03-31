import streamlit as st
import cv2
import numpy as np
import json
import requests
import hashlib
import datetime
import time
import os
import base64
from cryptography.fernet import Fernet
from PIL import Image
from io import BytesIO

# Set page configuration
st.set_page_config(
    page_title="Palm UPI Payment System",
    page_icon="💳",
    layout="centered"
)

# Configuration settings
CONFIG = {
    "upi_gateway_url": "https://api.upipayment.com/transaction",  # Example URL
    "merchant_id": "MERCHANT123456",
    "timeout_seconds": 30,
    "retry_attempts": 3
}

class PalmUPIPayment:
    def __init__(self):
        # In a real application, we would use a database
        # For this demo, we'll use session state to store data
        if 'palm_db' not in st.session_state:
            st.session_state.palm_db = {}
        
        # Initialize encryption key
        if 'encryption_key' not in st.session_state:
            st.session_state.encryption_key = Fernet.generate_key()
        
        self.cipher_suite = Fernet(st.session_state.encryption_key)
        
    def register_new_palm(self, user_id, palm_image):
        """Register a new palm for a user"""
        # Extract palm features using computer vision
        palm_features = self._extract_palm_features(palm_image)
        
        # Generate a unique palm ID
        palm_hash = hashlib.sha256(str(palm_features).encode()).hexdigest()
        
        # Encrypt the UPI ID associated with this palm
        encrypted_upi_id = self.cipher_suite.encrypt(user_id["upi_id"].encode())
        
        # Store in database
        st.session_state.palm_db[palm_hash] = {
            "user_id": user_id["user_id"],
            "encrypted_upi_id": encrypted_upi_id,
            "registration_date": datetime.datetime.now().isoformat(),
            "palm_features": palm_features
        }
        
        return {"status": "success", "palm_id": palm_hash}
    
    def _extract_palm_features(self, palm_image):
        """Extract unique features from palm image"""
        # Convert image to grayscale
        gray = cv2.cvtColor(np.array(palm_image), cv2.COLOR_RGB2GRAY)
        
        # Apply Gaussian blur to reduce noise
        blur = cv2.GaussianBlur(gray, (5, 5), 0)
        
        # Use adaptive thresholding to identify palm lines
        thresh = cv2.adaptiveThreshold(blur, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                      cv2.THRESH_BINARY_INV, 11, 2)
        
        # Find contours in the thresholded image
        contours, _ = cv2.findContours(thresh, cv2.RETR_TREE, cv2.CHAIN_APPROX_SIMPLE)
        
        # Extract key points from the contours
        key_points = []
        for contour in contours:
            if cv2.contourArea(contour) > 100:  # Filter small contours
                moments = cv2.moments(contour)
                if moments["m00"] != 0:
                    cx = int(moments["m10"] / moments["m00"])
                    cy = int(moments["m01"] / moments["m00"])
                    key_points.append((cx, cy))
        
        return key_points
    
    def authenticate_palm(self, palm_image):
        """Authenticate a palm image against registered palms"""
        # Extract features from the presented palm
        presented_features = self._extract_palm_features(palm_image)
        
        # Find the best match in our database
        best_match = None
        best_score = 0
        
        for palm_id, data in st.session_state.palm_db.items():
            score = self._match_palm_features(presented_features, data["palm_features"])
            if score > best_score and score > 0.8:  # 80% confidence threshold
                best_score = score
                best_match = palm_id
        
        if best_match:
            return {"status": "authenticated", "palm_id": best_match, "score": best_score}
        else:
            return {"status": "failed", "message": "Palm not recognized"}
    
    def _match_palm_features(self, features1, features2):
        """Compare two sets of palm features and return a similarity score"""
        # This would be a complex algorithm in production
        # Using a simple matching percentage for this example
        
        if not features1 or not features2:
            return 0
            
        matches = 0
        threshold = 10  # pixel distance threshold for a "match"
        
        for p1 in features1:
            for p2 in features2:
                # Calculate Euclidean distance between points
                dist = np.sqrt((p1[0] - p2[0])**2 + (p1[1] - p2[1])**2)
                if dist < threshold:
                    matches += 1
                    break
        
        return matches / len(features1) if len(features1) > 0 else 0
    
    def initiate_payment(self, palm_id, amount, merchant_vpa, description=""):
        """Initiate a UPI payment using authenticated palm"""
        if palm_id not in st.session_state.palm_db:
            return {"status": "failed", "message": "Invalid palm ID"}
        
        user_data = st.session_state.palm_db[palm_id]
        
        # Decrypt the UPI ID
        upi_id = self.cipher_suite.decrypt(user_data["encrypted_upi_id"]).decode()
        
        # Generate transaction ID
        transaction_id = f"TXN{int(time.time())}{user_data['user_id'][-4:]}"
        
        # Prepare payment request
        payment_request = {
            "transaction_id": transaction_id,
            "payer_vpa": upi_id,
            "payee_vpa": merchant_vpa,
            "amount": amount,
            "description": description,
            "merchant_id": CONFIG["merchant_id"]
        }
        
        # In a real application, this would connect to the UPI gateway
        # For this demo, we'll simulate a successful payment
        
        # Simulated payment response
        payment_response = {
            "status": "success",
            "transaction_id": transaction_id,
            "message": "Payment processed successfully"
        }
        
        return payment_response

# Helper functions for the Streamlit app
def get_image_display_size(img):
    """Return display dimensions for an image"""
    height, width = img.shape[:2]
    max_height = 300
    max_width = 500
    
    # Calculate scaling factor
    scale = min(max_height/height, max_width/width)
    
    return int(width * scale), int(height * scale)

def main():
    # Initialize the payment system
    payment_system = PalmUPIPayment()
    
    # App header
    st.title("Palm UPI Payment System")
    
    # Navigation tabs
    tab1, tab2, tab3 = st.tabs(["Home", "Register", "Make Payment"])
    
    with tab1:
        st.header("Welcome to Palm UPI")
        st.write("""
        This innovative payment system allows you to make UPI payments using your palm print as authentication.
        
        ### How it works:
        1. **Register**: Link your UPI ID with your palm print
        2. **Pay**: Simply scan your palm to authenticate and make payments
        
        ### Benefits:
        - No need to remember UPI IDs or passwords
        - Quick and secure transactions
        - Contactless payments
        """)
        
        st.image("https://www.example.com/palm_payment.jpg", 
                 use_column_width=True, 
                 caption="Palm Authentication Technology")
    
    with tab2:
        st.header("Register Your Palm")
        
        # User information input
        user_name = st.text_input("Full Name")
        user_id = st.text_input("User ID (e.g., mobile number)")
        upi_id = st.text_input("UPI ID (e.g., username@upi)")
        
        # Palm image upload
        uploaded_file = st.file_uploader("Upload Palm Image", type=["jpg", "jpeg", "png"])
        
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption="Uploaded Palm Image", width=300)
            
            # Registration button
            if st.button("Register Palm"):
                if not user_name or not user_id or not upi_id:
                    st.error("Please fill in all user information")
                else:
                    user_data = {
                        "user_id": user_id,
                        "user_name": user_name,
                        "upi_id": upi_id
                    }
                    
                    # Process registration
                    with st.spinner("Processing palm registration..."):
                        result = payment_system.register_new_palm(user_data, image)
                    
                    if result["status"] == "success":
                        st.success(f"Palm registered successfully! Your Palm ID: {result['palm_id'][:8]}...")
                        st.session_state.last_registered_palm = result["palm_id"]
                    else:
                        st.error("Registration failed. Please try again.")
    
    with tab3:
        st.header("Make a Payment")
        
        # Payment details
        merchant_vpa = st.text_input("Merchant UPI ID")
        amount = st.number_input("Amount (₹)", min_value=1.0, step=1.0)
        description = st.text_input("Description (optional)")
        
        # Palm image upload for authentication
        uploaded_file = st.file_uploader("Scan Your Palm", type=["jpg", "jpeg", "png"], key="payment_palm")
        
        if uploaded_file is not None:
            image = Image.open(uploaded_file)
            st.image(image, caption="Scanned Palm", width=300)
            
            # Payment button
            if st.button("Authenticate & Pay"):
                if not merchant_vpa or amount <= 0:
                    st.error("Please enter valid payment details")
                else:
                    # Process payment
                    with st.spinner("Authenticating your palm..."):
                        auth_result = payment_system.authenticate_palm(image)
                    
                    if auth_result["status"] == "authenticated":
                        st.success(f"Authentication successful! Match score: {auth_result['score']:.2f}")
                        
                        with st.spinner("Processing payment..."):
                            payment_result = payment_system.initiate_payment(
                                auth_result["palm_id"],
                                amount,
                                merchant_vpa,
                                description
                            )
                        
                        if payment_result["status"] == "success":
                            st.success(f"Payment successful! Transaction ID: {payment_result['transaction_id']}")
                            
                            # Display transaction details
                            st.write("### Transaction Details")
                            st.write(f"**Amount:** ₹{amount}")
                            st.write(f"**To:** {merchant_vpa}")
                            st.write(f"**Transaction ID:** {payment_result['transaction_id']}")
                            st.write(f"**Date & Time:** {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
                            
                            # Add a download button for receipt
                            receipt_html = f"""
                            <html>
                            <body>
                                <h2>Payment Receipt</h2>
                                <p><b>Transaction ID:</b> {payment_result['transaction_id']}</p>
                                <p><b>Amount:</b> ₹{amount}</p>
                                <p><b>Merchant:</b> {merchant_vpa}</p>
                                <p><b>Date & Time:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                                <p><b>Status:</b> Successful</p>
                            </body>
                            </html>
                            """
                            st.download_button(
                                label="Download Receipt",
                                data=receipt_html,
                                file_name="payment_receipt.html",
                                mime="text/html"
                            )
                        else:
                            st.error(f"Payment failed: {payment_result.get('message', 'Unknown error')}")
                    else:
                        st.error("Authentication failed. Palm not recognized.")
    
    # Display registered palms (for demo purposes)
    if st.session_state.palm_db:
        st.sidebar.header("Registered Palms")
        for palm_id, data in st.session_state.palm_db.items():
            st.sidebar.write(f"**User:** {data['user_id']}")
            st.sidebar.write(f"**Palm ID:** {palm_id[:8]}...")
            st.sidebar.write(f"**Registered:** {data['registration_date']}")
            st.sidebar.write("---")

if __name__ == "__main__":
    main()
