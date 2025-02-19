import streamlit as st
import pandas as pd
import sqlite3
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

# الاتصال بقاعدة بيانات SQLite
conn = sqlite3.connect("govinto_products.db", check_same_thread=False)
cursor = conn.cursor()

def manage_categories():
    """إدارة الفئات والفئات الفرعية"""
    st.subheader("Manage Categories and Subcategories")
    new_category = st.text_input("Add New Category")
    if st.button("Add Category") and new_category:
        cursor.execute("INSERT OR IGNORE INTO categories (category) VALUES (?)", (new_category,))
        conn.commit()
        st.success("✅ Category added successfully!")
        st.rerun()

def import_export_data():
    """استيراد وتصدير البيانات"""
    st.subheader("Import/Export Data")
    if st.button("Export Data"):
        df_products = pd.read_sql_query("SELECT * FROM products", conn)
        df_products.to_csv("products_export.csv", index=False)
        st.success("✅ Data exported successfully!")
    
    uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])
    if uploaded_file is not None:
        df_uploaded = pd.read_csv(uploaded_file)
        df_uploaded.to_sql("products", conn, if_exists="append", index=False)
        st.success("✅ Data imported successfully!")
        st.rerun()

def main():
    st.sidebar.image("govinto_logo.png", use_container_width=True)
    st.sidebar.title("Menu")
    menu = ["Add Product", "Manage Categories", "View Products", "Import/Export Data", "Sync Data"]
    choice = st.sidebar.radio("Select an option", menu)
    
    if choice == "Add Product":
        add_product()
    elif choice == "Manage Categories":
        manage_categories()
    elif choice == "View Products":
        view_products()
    elif choice == "Import/Export Data":
        import_export_data()
    elif choice == "Sync Data":
        sync_data()

if __name__ == "__main__":
    main()
