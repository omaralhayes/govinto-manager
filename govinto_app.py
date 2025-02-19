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
    
    categories = pd.read_sql_query("SELECT * FROM categories", conn)
    selected_category = st.selectbox("Select Category", ["Select"] + categories["category"].tolist())
    
    if selected_category != "Select":
        category_id = categories[categories["category"] == selected_category]["id"].values[0]
        
        new_subcategory = st.text_input("Add Subcategory")
        if st.button("Add Subcategory") and new_subcategory:
            cursor.execute("INSERT INTO subcategories (category_id, sub_category) VALUES (?, ?)", (category_id, new_subcategory))
            conn.commit()
            st.success("✅ Subcategory added successfully!")
            st.rerun()
        
        df_subcategories = pd.read_sql_query("SELECT id, sub_category FROM subcategories WHERE category_id = ?", conn, params=(category_id,))
        st.write("### Subcategories")
        for index, row in df_subcategories.iterrows():
            col1, col2, col3 = st.columns([3, 1, 1])
            new_name = col1.text_input("Edit Subcategory", row["sub_category"], key=f"edit_{row['id']}")
            if col2.button("Save", key=f"save_{row['id']}") and new_name.strip():
                cursor.execute("UPDATE subcategories SET sub_category = ? WHERE id = ?", (new_name, row["id"]))
                conn.commit()
                st.success("✅ Subcategory updated successfully!")
                st.rerun()
            if col3.button("🗑️ Delete", key=f"delete_{row['id']}"):
                cursor.execute("DELETE FROM subcategories WHERE id = ?", (row["id"],))
                conn.commit()
                st.warning("⚠️ Subcategory deleted!")
                st.rerun()
        
        if st.button("Delete Category"):
            cursor.execute("DELETE FROM subcategories WHERE category_id = ?", (category_id,))
            cursor.execute("DELETE FROM products WHERE category = ?", (selected_category,))
            cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
            conn.commit()
            st.warning("⚠️ Category and its subcategories/products deleted!")
            st.rerun()

def view_products():
    """عرض المنتجات"""
    st.subheader("View Products")
    df_products = pd.read_sql_query("SELECT * FROM products", conn)
    if not df_products.empty:
        st.dataframe(df_products)
    else:
        st.info("لا توجد منتجات متاحة")

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
        cursor.execute("INSERT INTO products (category, sub_category, product_name, product_link) VALUES (?, ?, ?, ?)", 
                       (selected_category, selected_subcategory, product_name, product_link))
        conn.commit()
        st.success("✅ Product added successfully!")
        st.rerun()

def main():
    st.sidebar.image("govinto_logo.png", use_container_width=True)
    st.sidebar.title("Menu")
    menu = ["Add Product", "Manage Categories", "View Products", "Import/Export Data", "Sync Data"]
    choice = st.sidebar.radio("Select an option", menu)
if choice == "Add Product":
    add_product()

  
    if choice == "Manage Categories":
        manage_categories()
    elif choice == "View Products":
        view_products()
    elif choice == "Import/Export Data":
        import_export_data()
    elif choice == "Sync Data":
        sync_data()

if __name__ == "__main__":
    main()
