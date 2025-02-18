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
        selected_category = st.selectbox("Select Category to Modify", ["Select"] + df_categories["category"].tolist())
        
        if selected_category != "Select":
            category_id = df_categories[df_categories["category"] == selected_category]["id"].values[0]
            new_category_name = st.text_input("Rename Category", selected_category)
            if st.button("Update Category"):
                cursor.execute("UPDATE categories SET category = ? WHERE id = ?", (new_category_name, category_id))
                conn.commit()
                db.collection("categories").document(selected_category).delete()
                db.collection("categories").document(new_category_name).set({"name": new_category_name})
                st.success("Category updated successfully!")
                st.rerun()
            
            if st.button("Delete Category"):
                cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
                cursor.execute("DELETE FROM subcategories WHERE category_id = ?", (category_id,))
                conn.commit()
                db.collection("categories").document(selected_category).delete()
                st.warning("Category deleted successfully!")
                st.rerun()
            
            new_subcategory = st.text_input("Add Subcategory")
            if st.button("Add Subcategory"):
                cursor.execute("INSERT OR IGNORE INTO subcategories (category_id, sub_category) VALUES (?, ?)", (category_id, new_subcategory))
                conn.commit()
                db.collection("categories").document(selected_category).collection("subcategories").document(new_subcategory).set({"name": new_subcategory})
                st.success("Subcategory added successfully!")
                st.rerun()
            
            df_subcategories = pd.read_sql_query("SELECT * FROM subcategories WHERE category_id = ?", conn, params=(category_id,))
            selected_subcategory = st.selectbox("Select Subcategory to Modify", ["Select"] + df_subcategories["sub_category"].tolist())
            
            if selected_subcategory != "Select":
                new_subcategory_name = st.text_input("Rename Subcategory", selected_subcategory)
                if st.button("Update Subcategory"):
                    cursor.execute("UPDATE subcategories SET sub_category = ? WHERE sub_category = ?", (new_subcategory_name, selected_subcategory))
                    conn.commit()
                    db.collection("categories").document(selected_category).collection("subcategories").document(selected_subcategory).delete()
                    db.collection("categories").document(selected_category).collection("subcategories").document(new_subcategory_name).set({"name": new_subcategory_name})
                    st.success("Subcategory updated successfully!")
                    st.rerun()
                
                if st.button("Delete Subcategory"):
                    cursor.execute("DELETE FROM subcategories WHERE sub_category = ?", (selected_subcategory,))
                    conn.commit()
                    db.collection("categories").document(selected_category).collection("subcategories").document(selected_subcategory).delete()
                    st.warning("Subcategory deleted successfully!")
                    st.rerun()

if __name__ == "__main__":
    main()
