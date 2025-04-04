import streamlit as st
import cv2
import numpy as np
import mediapipe as mp
import hashlib
import datetime
import time
from cryptography.fernet import Fernet
from PIL import Image

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
    "capture_duration": 3  # Reduced for testing, you can increase
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

        hand_landmarks = results.multi_hand_landmarks[0]
        features = []
        for landmark in hand_landmarks.landmark:
            features.extend([landmark.x, landmark.y, landmark.z])

        return features

    def register_new_palm(self, user_id, palm_image):
        palm_features = self._extract_palm_features(palm_image)
        if palm_features is None:
            return {"status": "error", "message": "No hand detected"}

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
        if features1 is None or features2 is None:
            return 0

        vec1 = np.array(features1)
        vec2 = np.array(features2)
        min_length = min(len(vec1), len(vec2))
        norm_vec1 = np.linalg.norm(vec1[:min_length])
        norm_vec2 = np.linalg.norm(vec2[:min_length])
        if norm_vec1 == 0 or norm_vec2 == 0:
            return 0
        return np.dot(vec1[:min_length], vec2[:min_length]) / (norm_vec1 * norm_vec2)

    def authenticate_palm(self, palm_image):
        presented_features = self._extract_palm_features(palm_image)
        if presented_features is None:
            return {"status": "failed", "message": "No hand detected"}

        best_match = None
        best_score = 0
        for palm_id, data in st.session_state.palm_db.items():
            score = self._match_palm_features(presented_features, data["palm_features"])
            if score > best_score and score > 0.65:
                best_score = score
                best_match = palm_id

        if best_match:
            return {"status": "authenticated", "palm_id": best_match, "score": best_score}
        else:
            return {"status": "failed", "message": f"Authentication Failed. Score: {best_score:.2f}"}

    def initiate_payment(self, palm_id, amount, merchant_vpa):
        if palm_id not in st.session_state.palm_db:
            return {"status": "failed", "message": "Invalid palm ID"}

        user_data = st.session_state.palm_db[palm_id]
        upi_id = self.cipher_suite.decrypt(user_data["encrypted_upi_id"]).decode()
        return {
            "status": "success",
            "transaction_id": f"TXN{int(time.time())}{user_data['user_id'][-4:]}",
            "message": f"Payment of ₹{amount} to {merchant_vpa} successful"
        }

import streamlit as st
import time
from PIL import Image

def capture_palm(duration, purpose):
    """Webcam capture component with countdown"""
    if f"{purpose}_start" not in st.session_state:
        st.session_state[f"{purpose}_start"] = False

    if st.button(f"Start {purpose.capitalize()} Capture"):
        st.session_state[f"{purpose}_start"] = time.time()

    if st.session_state.get(f"{purpose}_start"):
        elapsed = time.time() - st.session_state[f"{purpose}_start"]
        remaining = duration - elapsed

        if remaining > 0:
            time_placeholder = st.empty()
            while remaining > 0:
                time_placeholder.markdown(f"<h1 style='text-align: center; color: red;'>{int(remaining)}</h1>",
                                         unsafe_allow_html=True)
                time.sleep(1)
                remaining -= 1
            time_placeholder.markdown("<h1 style='text-align: center;'>🎥</h1>", unsafe_allow_html=True)

            # Capture image after countdown
            img_file = st.camera_input(f"Capture palm for {purpose}",
                                         key=f"camera_{purpose}")
            if img_file:
                st.session_state[f"{purpose}_start"] = None
                return Image.open(img_file)
            else:
                st.session_state[f"{purpose}_start"] = None # Reset state if no image captured
        else:
            # Capture image if countdown finished (shouldn't be needed with the above logic)
            img_file = st.camera_input(f"Capture palm for {purpose}",
                                         key=f"camera_{purpose}")
            if img_file:
                st.session_state[f"{purpose}_start"] = None
                return Image.open(img_file)
            else:
                st.session_state[f"{purpose}_start"] = None # Reset state if no image captured
    else:
        # Show the button only when not capturing
        if st.button(f"Start {purpose.capitalize()} Capture"):
            st.session_state[f"{purpose}_start"] = time.time()
            st.rerun() # Rerun to start the countdown

    return None

def main():
    payment_system = PalmUPIPayment()

    st.title("Palm UPI Payment System")
    tab1, tab2, tab3 = st.tabs(["Home", "Register", "Pay"])

    with tab1:
        st.markdown("## Secure Contactless Payments")
        st.image("https://via.placeholder.com/700x300?text=Palm+Auth+System",
                 use_container_width=True)
        st.markdown("""
        - **Biometric Authentication**: Palm recognition technology
        - **Instant Transactions**: UPI-powered payments
        - **Secure Encryption**: Military-grade data protection
        """)

    with tab2:
        st.header("New Registration")
        with st.form("reg_form"):
            name = st.text_input("Full Name")
            mobile = st.text_input("Mobile Number")
            upi_id = st.text_input("UPI ID")

            if st.form_submit_button("Register"):
                if not all([name, mobile, upi_id]):
                    st.error("All fields required!")
                else:
                    palm_img = capture_palm(CONFIG["capture_duration"], "registration")
                    if palm_img:
                        result = payment_system.register_new_palm(
                            {"user_id": mobile, "upi_id": upi_id},
                            palm_img
                        )
                        if result["status"] == "success":
                            st.success("Registration Successful!")
                            st.code(f"Palm ID: {result['palm_id'][:8]}...")
                        else:
                            st.error(result.get("message", "Registration failed"))
                    else:
                        st.error("Palm capture failed")

    with tab3:
        st.header("Make Payment")
        with st.form("pay_form"):
            merchant_id = st.text_input("Merchant UPI ID")
            amount = st.number_input("Amount (₹)", min_value=1.0)

            if st.form_submit_button("Initiate Payment"):
                if not merchant_id or amount <= 0:
                    st.error("Invalid payment details")
                else:
                    palm_img = capture_palm(CONFIG["capture_duration"], "payment")
                    if palm_img:
                        auth_result = payment_system.authenticate_palm(palm_img)
                        if auth_result["status"] == "authenticated":
                            pay_result = payment_system.initiate_payment(
                                auth_result["palm_id"],
                                amount,
                                merchant_id
                            )
                            if pay_result["status"] == "success":
                                st.balloons()
                                st.success(pay_result['message'])
                            else:
                                st.error(pay_result.get("message", "Payment failed"))
                        else:
                            st.error(f"Authentication Failed: {auth_result.get('message')}")
                    else:
                        st.error("Palm capture failed")

    if st.session_state.palm_db:
        st.sidebar.header("Registered Users")
        for pid, data in st.session_state.palm_db.items():
            st.sidebar.markdown(f"""
            **{data['user_id']}**
            `{pid[:8]}...`
            {data['registration_date'][:10]}
            """)

if __name__ == "__main__":
    main()
