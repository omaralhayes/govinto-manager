import streamlit as st
import pandas as pd
import sqlite3
import firebase_admin
from firebase_admin import credentials, firestore
import openpyxl
import json

# Load Firebase credentials from Streamlit Secrets
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
    st.error(f"❌ خطأ: فشل تحميل بيانات Firebase. تأكد من إدخال القيم الصحيحة في Streamlit Secrets. التفاصيل: {e}")
    st.stop()

# Connect to SQLite
conn = sqlite3.connect("govinto_products.db", check_same_thread=False)
cursor = conn.cursor()

# Create tables if they don't exist
cursor.execute('''CREATE TABLE IF NOT EXISTS categories (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT UNIQUE)''')
cursor.execute('''CREATE TABLE IF NOT EXISTS subcategories (id INTEGER PRIMARY KEY AUTOINCREMENT, category_id INTEGER, sub_category TEXT UNIQUE, FOREIGN KEY(category_id) REFERENCES categories(id))''')
cursor.execute('''CREATE TABLE IF NOT EXISTS products (id INTEGER PRIMARY KEY AUTOINCREMENT, category TEXT, sub_category TEXT, product_name TEXT, product_link TEXT, likes INTEGER, comments INTEGER, rating REAL, supplier_orders INTEGER, supplier_price REAL, store_price REAL)''')
conn.commit()

def main():
    st.sidebar.image("govinto_logo.png", use_container_width=True)
    st.sidebar.title("Menu")
    menu = ["Add Product", "Manage Categories", "View Products", "Import/Export Data", "Sync Data"]
    choice = st.sidebar.radio("Select an option", menu)
    
    st.title("Govinto Product Management")
    
    if choice == "View Products":
        st.subheader("All Products")
        df = pd.read_sql_query("SELECT * FROM products", conn)
        st.dataframe(df)
        
        if st.button("Delete All Products"):
            cursor.execute("DELETE FROM products")
            conn.commit()
            st.success("All products deleted successfully!")
            st.rerun()
    
    elif choice == "Import/Export Data":
        st.subheader("Import & Export Data")
        
        # Export Data
        st.write("### Export Products to CSV")
        df = pd.read_sql_query("SELECT * FROM products", conn)
        file_name = "govinto_products.csv"
        df.to_csv(file_name, index=False)
        st.download_button("Download CSV File", open(file_name, "rb"), file_name=file_name)
        
        # Import Data
        st.write("### Import Products from CSV")
        uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])
        
        if uploaded_file is not None:
            df_uploaded = pd.read_csv(uploaded_file)
            for _, row in df_uploaded.iterrows():
                cursor.execute("INSERT INTO products (category, sub_category, product_name, product_link, likes, comments, rating, supplier_orders, supplier_price, store_price) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                               (row["category"], row["sub_category"], row["product_name"], row["product_link"], row["likes"], row["comments"], row["rating"], row["supplier_orders"], row["supplier_price"], row["store_price"]))
            conn.commit()
            st.success("Products imported successfully!")
            st.rerun()
    
    elif choice == "Sync Data":
        st.subheader("Sync Data Between SQLite and Firestore")
        
        if st.button("Sync from Firestore to SQLite"):
            cursor.execute("DELETE FROM products")
            conn.commit()
            products = db.collection("products").stream()
            for product in products:
                data = product.to_dict()
                cursor.execute("INSERT INTO products (category, sub_category, product_name, product_link, likes, comments, rating, supplier_orders, supplier_price, store_price) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (data["category"], data["sub_category"], data["product_name"], data["product_link"], data["likes"], data["comments"], data["rating"], data["supplier_orders"], data["supplier_price"], data["store_price"]))
            conn.commit()
            st.success("Data synced from Firestore to SQLite!")
            st.rerun()
        
        if st.button("Sync from SQLite to Firestore"):
            products = pd.read_sql_query("SELECT * FROM products", conn)
            for _, row in products.iterrows():
                product_ref = db.collection("products").document()
                product_ref.set(row.to_dict())
            st.success("Data synced from SQLite to Firestore!")
            st.rerun()

if __name__ == "__main__":
    main()
