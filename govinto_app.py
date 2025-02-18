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
    
    if choice == "Manage Categories":
        st.subheader("Manage Categories and Subcategories")
        new_category = st.text_input("Add New Category")
        if st.button("Add Category"):
            cursor.execute("INSERT OR IGNORE INTO categories (category) VALUES (?)", (new_category,))
            conn.commit()
            db.collection("categories").document(new_category).set({"name": new_category})
            st.success("Category added successfully!")
            st.rerun()
        
        df_categories = pd.read_sql_query("SELECT * FROM categories", conn)
        if not df_categories.empty:
            st.dataframe(df_categories)
        
    elif choice == "View Products":
        st.subheader("All Products")
        df = pd.read_sql_query("SELECT * FROM products", conn)
        if not df.empty:
            st.dataframe(df)
        else:
            st.warning("No products available.")
        
    elif choice == "Import/Export Data":
        st.subheader("Import & Export Data")
        df = pd.read_sql_query("SELECT * FROM products", conn)
        file_name = "govinto_products.csv"
        df.to_csv(file_name, index=False)
        st.download_button("Download CSV File", open(file_name, "rb"), file_name=file_name)
        
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

if __name__ == "__main__":
    main()
