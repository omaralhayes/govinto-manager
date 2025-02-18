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

    # 🛠 **إدارة الفئات والفئات الفرعية**
    if choice == "Manage Categories":
        st.subheader("Manage Categories and Subcategories")
        
        # إضافة فئة جديدة
        new_category = st.text_input("Add New Category")
        if st.button("Add Category"):
            cursor.execute("INSERT OR IGNORE INTO categories (category) VALUES (?)", (new_category,))
            conn.commit()
            st.success("✅ Category added successfully!")
            st.rerun()
        
        # تعديل أو حذف الفئات
        categories = [row[0] for row in cursor.execute("SELECT category FROM categories").fetchall()]
        selected_category = st.selectbox("Select Category", ["Select"] + categories)
        
        if selected_category != "Select":
            new_category_name = st.text_input("Rename Category", selected_category)
            
            if st.button("Update Category"):
                cursor.execute("UPDATE categories SET category = ? WHERE category = ?", (new_category_name, selected_category))
                conn.commit()
                st.success("✅ Category updated successfully!")
                st.rerun()
            
            if st.button("Delete Category"):
                cursor.execute("DELETE FROM categories WHERE category = ?", (selected_category,))
                conn.commit()
                st.warning("⚠️ Category deleted!")
                st.rerun()
            
            # إضافة، تعديل، أو حذف الفئات الفرعية
            new_subcategory = st.text_input("Add Subcategory")
            if st.button("Add Subcategory"):
                cursor.execute("INSERT OR IGNORE INTO subcategories (category_id, sub_category) VALUES ((SELECT id FROM categories WHERE category = ?), ?)", (selected_category, new_subcategory))
                conn.commit()
                st.success("✅ Subcategory added successfully!")
                st.rerun()
            
            subcategories = [row[0] for row in cursor.execute("SELECT sub_category FROM subcategories WHERE category_id = (SELECT id FROM categories WHERE category = ?)", (selected_category,)).fetchall()]
            selected_subcategory = st.selectbox("Select Subcategory", ["Select"] + subcategories)
            
            if selected_subcategory != "Select":
                new_subcategory_name = st.text_input("Rename Subcategory", selected_subcategory)
                
                if st.button("Update Subcategory"):
                    cursor.execute("UPDATE subcategories SET sub_category = ? WHERE sub_category = ?", (new_subcategory_name, selected_subcategory))
                    conn.commit()
                    st.success("✅ Subcategory updated successfully!")
                    st.rerun()
                
                if st.button("Delete Subcategory"):
                    cursor.execute("DELETE FROM subcategories WHERE sub_category = ?", (selected_subcategory,))
                    conn.commit()
                    st.warning("⚠️ Subcategory deleted!")
                    st.rerun()

if __name__ == "__main__":
    main()
