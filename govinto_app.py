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
    """إضافة منتج جديد"""
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
    if st.button("Add Product") and selected_category != "Select" and selected_subcategory != "Select":
        cursor.execute("INSERT INTO products (category, sub_category, product_name, product_link) VALUES (?, ?, ?, ?)", (selected_category, selected_subcategory, product_name, product_link))
        conn.commit()
        st.success("✅ Product added successfully!")
        st.rerun()

def view_products():
    """عرض المنتجات"""
    st.subheader("View Products")
    df_products = pd.read_sql_query("SELECT * FROM products", conn)
    if not df_products.empty:
        st.dataframe(df_products)
    else:
        st.info("لا توجد منتجات متاحة")

def sync_data():
    """مزامنة البيانات بين Firestore و SQLite"""
    st.subheader("Sync Data")
    if st.button("Sync from Firestore"):
        products_ref = db.collection("products").stream()
        cursor.execute("DELETE FROM products")
        for doc in products_ref:
            data = doc.to_dict()
            cursor.execute("INSERT INTO products (category, sub_category, product_name, product_link) VALUES (?, ?, ?, ?)", (data["category"], data["sub_category"], data["product_name"], data["product_link"]))
        conn.commit()
        st.success("✅ Synced from Firestore!")
    
    if st.button("Sync to Firestore"):
        df_products = pd.read_sql_query("SELECT * FROM products", conn)
        for _, row in df_products.iterrows():
            doc_ref = db.collection("products").document(row["product_name"])
            doc_ref.set(row.to_dict())
        st.success("✅ Synced to Firestore!")

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
