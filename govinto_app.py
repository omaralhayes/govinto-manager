import streamlit as st
import pandas as pd
import sqlite3
import firebase_admin
from firebase_admin import credentials, firestore
import json

# تحميل بيانات Firebase من Streamlit Secrets
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

# الاتصال بقاعدة بيانات SQLite
conn = sqlite3.connect("govinto_products.db", check_same_thread=False)
cursor = conn.cursor()

# إنشاء الجداول إذا لم تكن موجودة
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

    # 🛒 **إضافة منتج جديد**
    if choice == "Add Product":
        st.subheader("Add New Product")
        df_categories = pd.read_sql_query("SELECT * FROM categories", conn)
        category_options = df_categories["category"].tolist()
        selected_category = st.selectbox("Select Product Category", ["Select"] + category_options)
        
        subcategory_options = []
        if selected_category != "Select":
            category_id = df_categories[df_categories["category"] == selected_category]["id"].values[0]
            df_subcategories = pd.read_sql_query("SELECT sub_category FROM subcategories WHERE category_id = ?", conn, params=(category_id,))
            subcategory_options = df_subcategories["sub_category"].tolist()
        
        selected_subcategory = st.selectbox("Select Subcategory", ["Select"] + subcategory_options)
        product_name = st.text_input("Product Name")
        product_link = st.text_input("Product Link")
        likes = st.number_input("Likes", min_value=0, step=1)
        comments = st.number_input("Comments", min_value=0, step=1)
        rating = st.slider("Rating", 0.0, 5.0, 0.0, 0.1)
        supplier_orders = st.number_input("Supplier Orders", min_value=0, step=1)
        supplier_price = st.number_input("Supplier Price (USD)", min_value=0.0, step=0.1)
        store_price = st.number_input("Store Price (USD)", min_value=0.0, step=0.1)
        
        if st.button("Add Product") and selected_category != "Select" and selected_subcategory != "Select":
            cursor.execute("INSERT INTO products (category, sub_category, product_name, product_link, likes, comments, rating, supplier_orders, supplier_price, store_price) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", (selected_category, selected_subcategory, product_name, product_link, likes, comments, rating, supplier_orders, supplier_price, store_price))
            conn.commit()
            st.success("✅ Product added successfully!")
            st.rerun()
    
    # 🗂 **إدارة الفئات والفئات الفرعية**
    elif choice == "Manage Categories":
        st.subheader("Manage Categories and Subcategories")
        new_category = st.text_input("Add New Category")
        if st.button("Add Category"):
            cursor.execute("INSERT OR IGNORE INTO categories (category) VALUES (?)", (new_category,))
            conn.commit()
            st.success("✅ Category added successfully!")
            st.rerun()
        
        categories = [row[0] for row in cursor.execute("SELECT category FROM categories").fetchall()]
        selected_category = st.selectbox("Select Category", ["Select"] + categories)
        
        if selected_category != "Select":
            new_subcategory = st.text_input("Add Subcategory")
            if st.button("Add Subcategory"):
                cursor.execute("INSERT OR IGNORE INTO subcategories (category_id, sub_category) VALUES ((SELECT id FROM categories WHERE category = ?), ?)", (selected_category, new_subcategory))
                conn.commit()
                st.success("✅ Subcategory added successfully!")
                st.rerun()

    # 🔄 **مزامنة البيانات بين Firestore و SQLite**
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
            st.success("✅ Data synced from Firestore to SQLite!")
            st.rerun()

if __name__ == "__main__":
    main()
