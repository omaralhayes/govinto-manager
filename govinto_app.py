from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import firebase_admin
from firebase_admin import credentials, firestore

# تحميل بيانات Firebase
try:
    firebase_config = {
        "type": st.secrets["firebase_type"],
        "project_id": st.secrets["firebase_project_id"],
        "private_key_id": st.secrets["firebase_private_key_id"],
        "private_key": st.secrets["firebase_private_key"].replace("\\n", "\n"),
        "client_email": st.secrets["firebase_client_email"],
        "client_id": st.secrets["firebase_client_id"],
        "auth_uri": st.secrets["firebase_auth_uri"],
        "token_uri": st.secrets["firebase_token_uri"],
        "auth_provider_x509_cert_url": st.secrets["firebase_auth_provider_x509_cert_url"],
        "client_x509_cert_url": st.secrets["firebase_client_x509_cert_url"],
        "universe_domain": st.secrets["firebase_universe_domain"]
    }
    if not firebase_admin._apps:
        cred = credentials.Certificate(firebase_config)
        firebase_admin.initialize_app(cred)
    db = firestore.client()
except Exception as e:
    st.error(f"❌ خطأ في تحميل Firebase: {e}")
    st.stop()

# ✅ هنا يجب إضافة الدالة
def get_user_from_firestore(username):
    """جلب بيانات المستخدم من Firestore"""
    try:
        user_ref = db.collection("users").document(username).get()
        if user_ref.exists:
            user_data = user_ref.to_dict()
            return user_data  # إرجاع البيانات كما هي بدون تعديل
        else:
            return None  # المستخدم غير موجود
    except Exception as e:
        st.error(f"❌ Error fetching user data: {e}")
        return None
