import streamlit as st
import cv2
import numpy as np
import mediapipe as mp
import hashlib
import datetime
import time
from cryptography.fernet import Fernet
from PIL import Image
import io

# Initialize MediaPipe Hands
mp_hands = mp.solutions.hands
hands = mp_hands.Hands(
    static_image_mode=True,
    max_num_hands=1,
    min_detection_confidence=0.7,
    min_tracking_confidence=0.5
)

# Set page configuration
st.set_page_config(
    page_title="Palm UPI Payment System",
    page_icon="💳",
    layout="centered"
)

# Configuration settings
CONFIG = {
    "upi_gateway_url": "https://api.upipayment.com/transaction",
    "merchant_id": "MERCHANT123456",
    "timeout_seconds": 30,
    "retry_attempts": 3
}

class PalmUPIPayment:
    def __init__(self):
        if 'palm_db' not in st.session_state:
            st.session_state.palm_db = {}
        
        if 'encryption_key' not in st.session_state:
            st.session_state.encryption_key = Fernet.generate_key()
        
        self.cipher_suite = Fernet(st.session_state.encryption_key)
    
    def _extract_palm_features(self, palm_image):
        """Extract palm features using MediaPipe Hand Landmarks"""
        img_array = np.array(palm_image)
        results = hands.process(cv2.cvtColor(img_array, cv2.COLOR_RGB2BGR))
        
        if not results.multi_hand_landmarks:
            return None
        
        # Extract and normalize landmarks
        hand_landmarks = results.multi_hand_landmarks[0]
        features = []
        for landmark in hand_landmarks.landmark:
            features.extend([landmark.x, landmark.y, landmark.z])
        
        return features
    
    def register_new_palm(self, user_id, palm_image):
        palm_features = self._extract_palm_features(palm_image)
        if palm_features is None:
            return {"status": "error", "message": "No hand detected in image"}
        
        palm_hash = hashlib.sha256(np.array(palm_features).tobytes()).hexdigest()
        encrypted_upi_id = self.cipher_suite.encrypt(user_id["upi_id"].encode())
        
        st.session_state.palm_db[palm_hash] = {
            "user_id": user_id["user_id"],
            "encrypted_upi_id": encrypted_upi_id,
            "registration_date": datetime.datetime.now().isoformat(),
            "palm_features": palm_features
        }
        
        return {"status": "success", "palm_id": palm_hash}
    
    def _match_palm_features(self, features1, features2):
        """Compare palm features using cosine similarity"""
        if features1 is None or features2 is None:
            return 0
        
        vec1 = np.array(features1)
        vec2 = np.array(features2)
        
        # Handle potential different lengths
        min_length = min(len(vec1), len(vec2))
        vec1 = vec1[:min_length]
        vec2 = vec2[:min_length]
        
        # Cosine similarity
        cosine_sim = np.dot(vec1, vec2) / (np.linalg.norm(vec1) * np.linalg.norm(vec2))
        return (cosine_sim + 1) / 2  # Normalize to 0-1 range
    
    def authenticate_palm(self, palm_image):
        presented_features = self._extract_palm_features(palm_image)
        if presented_features is None:
            return {"status": "failed", "message": "No hand detected"}
        
        best_match = None
        best_score = 0
        
        for palm_id, data in st.session_state.palm_db.items():
            score = self._match_palm_features(presented_features, data["palm_features"])
            if score > best_score and score > 0.65:  # Adjusted threshold
                best_score = score
                best_match = palm_id
        
        if best_match:
            return {"status": "authenticated", "palm_id": best_match, "score": best_score}
        return {"status": "failed", "message": f"Palm not recognized (Score: {best_score:.2f})"}
    
    def initiate_payment(self, palm_id, amount, merchant_vpa, description=""):
        if palm_id not in st.session_state.palm_db:
            return {"status": "failed", "message": "Invalid palm ID"}
        
        user_data = st.session_state.palm_db[palm_id]
        upi_id = self.cipher_suite.decrypt(user_data["encrypted_upi_id"]).decode()
        transaction_id = f"TXN{int(time.time())}{user_data['user_id'][-4:]}"
        
        return {
            "status": "success",
            "transaction_id": transaction_id,
            "message": "Payment processed successfully"
        }

def main():
    payment_system = PalmUPIPayment()
    
    # Initialize session states for webcam capture
    if 'countdown' not in st.session_state:
        st.session_state.countdown = 10
    if 'registration_image' not in st.session_state:
        st.session_state.registration_image = None
    if 'is_capturing' not in st.session_state:
        st.session_state.is_capturing = False
    
    st.title("Palm UPI Payment System")
    tab1, tab2, tab3 = st.tabs(["Home", "Register", "Make Payment"])
    
    with tab1:
        st.header("Welcome to Palm UPI")
        st.markdown("""
        Secure UPI payments using palm recognition technology.
        
        ### How it works:
        1. **Register**: Link your UPI ID with your palm print
        2. **Pay**: Scan your palm to authenticate transactions
        
        ### Benefits:
        - Biometric security
        - Instant transactions
        - Contactless payments
        """)
        st.image("https://via.placeholder.com/600x400?text=Palm+Auth+Demo", 
                 caption="Palm Authentication Interface",
                 use_container_width=True)
    
    with tab2:
        st.header("Palm Registration")
        with st.form("registration_form"):
            user_name = st.text_input("Full Name")
            user_id = st.text_input("Mobile Number")
            upi_id = st.text_input("UPI ID (e.g., username@bank)")
            
            # Form submit button
            submit_pressed = st.form_submit_button("Start Palm Capture")
        
        # Handle palm capture outside the form
        if submit_pressed:
            if not all([user_name, user_id, upi_id]):
                st.error("Please fill all fields")
            else:
                st.session_state.is_capturing = True
                st.session_state.countdown = 10
        
        # Palm capture process
        if st.session_state.is_capturing:
            col1, col2 = st.columns([3, 1])
            
            with col1:
                camera_placeholder = st.empty()
                captured_image = camera_placeholder.camera_input("Position your palm in frame", key="palm_register")
                
            with col2:
                timer_placeholder = st.empty()
                timer_placeholder.info(f"Time remaining: {st.session_state.countdown} seconds")
                
            if captured_image:
                if st.session_state.countdown > 0:
                    time.sleep(1)
                    st.session_state.countdown -= 1
                    timer_placeholder.info(f"Time remaining: {st.session_state.countdown} seconds")
                    st.experimental_rerun()
                else:
                    st.session_state.registration_image = captured_image
                    st.session_state.is_capturing = False
                    
                    # Process registration
                    image = Image.open(st.session_state.registration_image)
                    result = payment_system.register_new_palm(
                        {"user_id": user_id, "upi_id": upi_id},
                        image
                    )
                    
                    if result["status"] == "success":
                        st.success(f"Registration successful! Palm ID: {result['palm_id'][:8]}...")
                    else:
                        st.error(result.get("message", "Registration failed"))
                    
                    # Reset for next registration
                    st.session_state.registration_image = None
    
    with tab3:
        st.header("Make Payment")
        
        col1, col2 = st.columns([2, 1])
        
        with col1:
            merchant_vpa = st.text_input("Merchant UPI ID")
            amount = st.number_input("Amount (₹)", min_value=1.0, step=1.0)
            description = st.text_input("Payment Note (optional)")
        
        with col2:
            st.info("Scan your palm to authenticate and process payment")
        
        st.write("### Palm Scan")
        captured_image = st.camera_input("Position your palm in frame")
        
        if captured_image and merchant_vpa and amount > 0:
            # Show processing indicator
            with st.spinner("Processing palm authentication..."):
                # Create progress bar
                progress_bar = st.progress(0)
                
                # Simulate processing time
                for percent_complete in range(0, 101, 20):
                    time.sleep(0.1)
                    progress_bar.progress(percent_complete)
                
                image = Image.open(captured_image)
                auth_result = payment_system.authenticate_palm(image)
                
                progress_bar.progress(100)
                time.sleep(0.5)
                
                if auth_result["status"] == "authenticated":
                    st.success(f"Authentication Success (Score: {auth_result['score']:.2f})")
                    
                    # Process payment with progress animation
                    with st.spinner("Processing payment..."):
                        payment_progress = st.progress(0)
                        for percent_complete in range(0, 101, 10):
                            time.sleep(0.1)
                            payment_progress.progress(percent_complete)
                        
                        payment_result = payment_system.initiate_payment(
                            auth_result["palm_id"],
                            amount,
                            merchant_vpa,
                            description
                        )
                        
                        if payment_result["status"] == "success":
                            st.balloons()
                            st.success("Payment Successful!")
                            
                            # Create expandable transaction details
                            with st.expander("Transaction Details", expanded=True):
                                st.markdown(f"""
                                **Transaction Details**
                                - Amount: ₹{amount}
                                - Recipient: {merchant_vpa}
                                - Transaction ID: `{payment_result['transaction_id']}`
                                - Time: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
                                """)
                                
                                # Receipt generation
                                receipt = f"""
                                <html>
                                    <body>
                                        <h1>Payment Receipt</h1>
                                        <p><b>Status:</b> Successful</p>
                                        <p><b>Amount:</b> ₹{amount}</p>
                                        <p><b>To:</b> {merchant_vpa}</p>
                                        <p><b>Transaction ID:</b> {payment_result['transaction_id']}</p>
                                        <p><b>Date:</b> {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
                                    </body>
                                </html>
                                """
                                st.download_button(
                                    "Download Receipt",
                                    data=receipt,
                                    file_name="payment_receipt.html",
                                    mime="text/html"
                                )
                        else:
                            st.error("Payment failed: " + payment_result.get("message", "Unknown error"))
                else:
                    st.error("Authentication failed: " + auth_result.get("message", "Unknown error"))

    if st.session_state.palm_db:
        st.sidebar.header("Registered Users")
        for palm_id, data in st.session_state.palm_db.items():
            st.sidebar.markdown(f"""
            **User:** {data['user_id']}  
            **Palm ID:** `{palm_id[:8]}...`  
            **Registered:** {data['registration_date'][:10]}
            """)

if __name__ == "__main__":
    main()
