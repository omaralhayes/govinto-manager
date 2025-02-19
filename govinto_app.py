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
        
        # عرض الفئات الفرعية
        df_subcategories = pd.read_sql_query("SELECT id, sub_category FROM subcategories WHERE category_id = ?", conn, params=(category_id,))
        st.write("### Subcategories")
        for index, row in df_subcategories.iterrows():
            col1, col2, col3 = st.columns([3, 1, 1])
            col1.text(row["sub_category"])
            if col2.button("✏️ Edit", key=f"edit_{row['id']}"):
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
        
        if st.button("Delete Category"):
            cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
            conn.commit()
            st.warning("⚠️ Category and its subcategories deleted!")
            st.rerun()
        
        new_subcategory = st.text_input("Add Subcategory")
        if st.button("Add Subcategory") and new_subcategory:
            cursor.execute("INSERT OR IGNORE INTO subcategories (category_id, sub_category) VALUES (?, ?)", (category_id, new_subcategory))
            conn.commit()
            st.success("✅ Subcategory added successfully!")
            st.rerun()

def main():
    st.sidebar.image("govinto_logo.png", use_container_width=True)
    st.sidebar.title("Menu")
    menu = ["Manage Categories", "Sync Data"]
    choice = st.sidebar.radio("Select an option", menu)
    
    if choice == "Manage Categories":
        manage_categories()
    elif choice == "Sync Data":
        st.subheader("Sync Data between Firestore and SQLite")
        if st.button("Sync from Firestore to SQLite"):
            sync_from_firestore()
        if st.button("Sync from SQLite to Firestore"):
            sync_to_firestore()

if __name__ == "__main__":
    main()
