import streamlit as st
import pandas as pd
import sqlite3
import firebase_admin
from firebase_admin import credentials, firestore
import openpyxl

import json
import streamlit as st
import firebase_admin
from firebase_admin import credentials, firestore

# Load Firebase credentials from Streamlit Secrets
firebase_config = st.secrets["firebase"]
cred = credentials.Certificate(json.loads(firebase_config))
if not firebase_admin._apps:
    firebase_admin.initialize_app(cred)

# Connect to Firestore
db = firestore.client()


# Connect to Firestore
db = firestore.client()

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
            st.success("Product added successfully!")
            st.rerun()
    
    elif choice == "Manage Categories":
        st.subheader("Manage Categories and Subcategories")
        new_category = st.text_input("Add New Category")
        if st.button("Add Category"):
            cursor.execute("INSERT OR IGNORE INTO categories (category) VALUES (?)", (new_category,))
            conn.commit()
            db.collection("categories").document(new_category).set({"name": new_category})
            st.success("Category added successfully!")
            st.rerun()
        
        df_categories = pd.read_sql_query("SELECT * FROM categories", conn)
        selected_category = st.selectbox("Select Category", ["Select"] + df_categories["category"].tolist())
        
        if selected_category != "Select":
            category_id = df_categories[df_categories["category"] == selected_category]["id"].values[0]
            new_subcategory = st.text_input("Add Subcategory")
            if st.button("Add Subcategory"):
                cursor.execute("INSERT OR IGNORE INTO subcategories (category_id, sub_category) VALUES (?, ?)", (category_id, new_subcategory))
                conn.commit()
                db.collection("categories").document(selected_category).collection("subcategories").document(new_subcategory).set({"name": new_subcategory})
                st.success("Subcategory added successfully!")
                st.rerun()
            
            df_subcategories = pd.read_sql_query("SELECT * FROM subcategories WHERE category_id = ?", conn, params=(category_id,))
            st.write("### Existing Subcategories")
            st.dataframe(df_subcategories)
            
            selected_subcategory = st.selectbox("Select Subcategory to Delete", ["Select"] + df_subcategories["sub_category"].tolist())
            if selected_subcategory != "Select" and st.button("Delete Subcategory"):
                cursor.execute("DELETE FROM subcategories WHERE sub_category = ?", (selected_subcategory,))
                conn.commit()
                db.collection("categories").document(selected_category).collection("subcategories").document(selected_subcategory).delete()
                st.warning("Subcategory deleted!")
                st.rerun()
            
            if st.button("Delete Category"):
                cursor.execute("DELETE FROM categories WHERE category = ?", (selected_category,))
                cursor.execute("DELETE FROM subcategories WHERE category_id = ?", (category_id,))
                conn.commit()
                db.collection("categories").document(selected_category).delete()
                st.warning("Category and associated subcategories deleted!")
                st.rerun()

    elif choice == "View Products":
        st.subheader("All Products")
        df = pd.read_sql_query("SELECT * FROM products", conn)
        st.dataframe(df)
        
        if st.button("Delete All Products"):
            cursor.execute("DELETE FROM products")
            conn.commit()
            db.collection("products").stream()
            st.success("All products deleted successfully!")
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

if __name__ == "__main__":
    main()
