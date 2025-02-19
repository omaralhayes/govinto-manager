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

def add_product():
    """ إضافة منتج جديد """
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
    rating = st.slider("Rating", 0.0, 5.0, 0.1)
    supplier_orders = st.number_input("Supplier Orders", min_value=0, step=1)
    supplier_price = st.number_input("Supplier Price (USD)", min_value=0.0, step=0.1)
    store_price = st.number_input("Store Price (USD)", min_value=0.0, step=0.1)
    
    if st.button("Add Product") and selected_category != "Select" and selected_subcategory != "Select":
        cursor.execute("""
            INSERT INTO products (category, sub_category, product_name, product_link, likes, comments, rating, supplier_orders, supplier_price, store_price)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (selected_category, selected_subcategory, product_name, product_link, likes, comments, rating, supplier_orders, supplier_price, store_price))
        conn.commit()
        st.success("✅ Product added successfully!")
        st.rerun()

def manage_categories():
    """ إدارة الفئات والفئات الفرعية """
    st.subheader("Manage Categories and Subcategories")
    new_category = st.text_input("Add New Category")
    if st.button("Add Category") and new_category:
        cursor.execute("INSERT OR IGNORE INTO categories (category) VALUES (?)", (new_category,))
        conn.commit()
        st.success("✅ Category added successfully!")
        st.rerun()
    
    categories = pd.read_sql_query("SELECT * FROM categories", conn)
    selected_category = st.selectbox("Select Category", ["Select"] + categories["category"].tolist())
    
    if selected_category != "Select":
        category_id = categories[categories["category"] == selected_category]["id"].values[0]
        
        df_subcategories = pd.read_sql_query("SELECT id, sub_category FROM subcategories WHERE category_id = ?", conn, params=(category_id,))
        st.write("### Subcategories")
        for index, row in df_subcategories.iterrows():
            col1, col2, col3 = st.columns([3, 1, 1])
            col1.text(row["sub_category"])
            if col2.button("📝 Edit", key=f"edit_{row['id']}"):
                new_name = st.text_input("Edit Subcategory Name", row["sub_category"], key=f"input_{row['id']}")
                if st.button("Save", key=f"save_{row['id']}"):
                    cursor.execute("UPDATE subcategories SET sub_category = ? WHERE id = ?", (new_name, row["id"]))
                    conn.commit()
                    st.success("✅ Subcategory updated successfully!")
                    st.rerun()
            if col3.button("🗑️ Delete", key=f"delete_{row['id']}"):
                cursor.execute("DELETE FROM subcategories WHERE id = ?", (row["id"],))
                conn.commit()
                st.warning("⚠️ Subcategory deleted!")
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
    elif choice == "Sync Data":
        st.subheader("Sync Data between Firestore and SQLite")
        if st.button("Sync from Firestore to SQLite"):
            sync_from_firestore()
        if st.button("Sync from SQLite to Firestore"):
            sync_to_firestore()

if __name__ == "__main__":
    main()
