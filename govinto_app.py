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
    if st.button("Add Category") and new_category.strip():
        cursor.execute("INSERT OR IGNORE INTO categories (category) VALUES (?)", (new_category,))
        conn.commit()
        st.success("✅ Category added successfully!")
        st.rerun()
    
    categories = pd.read_sql_query("SELECT * FROM categories", conn)
    selected_category = st.selectbox("Select Category", ["Select"] + categories["category"].tolist())
    
    if selected_category != "Select":
        category_id = categories[categories["category"] == selected_category]["id"].values[0]

        new_subcategory = st.text_input("Add Subcategory")
        if st.button("Add Subcategory") and new_subcategory.strip():
            cursor.execute("INSERT INTO subcategories (category_id, sub_category) VALUES (?, ?)", (category_id, new_subcategory))
            conn.commit()
            st.success("✅ Subcategory added successfully!")
            st.rerun()

        df_subcategories = pd.read_sql_query("SELECT id, sub_category FROM subcategories WHERE category_id = ?", conn, params=(category_id,))
        st.write("### Subcategories")

        for index, row in df_subcategories.iterrows():
            col1, col2, col3 = st.columns([3, 1, 1])
            new_name = col1.text_input("Edit Subcategory", row["sub_category"], key=f"edit_{row['id']}")

            # ✅ عرض زر "Save" فقط عند تغيير اسم الفئة الفرعية
            if new_name.strip() and new_name != row["sub_category"]:
                if col2.button("Save", key=f"save_{row['id']}"):
                    cursor.execute("UPDATE subcategories SET sub_category = ? WHERE id = ?", (new_name, row["id"]))
                    conn.commit()
                    st.success("✅ Subcategory updated successfully!")
                    st.rerun()

            # ✅ إضافة رسالة تأكيد عند حذف الفئات الفرعية
            if col3.button("🗑️ Delete", key=f"delete_{row['id']}"):
                if st.button(f"Confirm Delete {row['sub_category']}", key=f"confirm_delete_{row['id']}"):
                    cursor.execute("DELETE FROM subcategories WHERE id = ?", (row["id"],))
                    conn.commit()
                    st.warning("⚠️ Subcategory deleted!")
                    st.rerun()

        # ✅ إضافة رسالة تأكيد عند حذف الفئات
        if st.button("Delete Category"):
            if st.button(f"Confirm Delete {selected_category}", key=f"confirm_delete_category_{category_id}"):
                cursor.execute("DELETE FROM subcategories WHERE category_id = ?", (category_id,))
                cursor.execute("DELETE FROM products WHERE category = ?", (selected_category,))
                cursor.execute("DELETE FROM categories WHERE id = ?", (category_id,))
                conn.commit()
                st.warning(f"⚠️ Category '{selected_category}' and its subcategories/products deleted!")
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

        for _, row in df_uploaded.iterrows():
            cursor.execute("""
                INSERT INTO products (category, sub_category, product_name, product_link, likes, comments, rating, supplier_orders, supplier_price, store_price)
                SELECT ?, ?, ?, ?, ?, ?, ?, ?, ?, ? 
                WHERE NOT EXISTS (SELECT 1 FROM products WHERE product_name = ?)
            """, (row["category"], row["sub_category"], row["product_name"], row["product_link"], 
                  row["likes"], row["comments"], row["rating"], row["supplier_orders"], 
                  row["supplier_price"], row["store_price"], row["product_name"]))

        conn.commit()
        st.success("✅ Data imported successfully without duplicates!")
        st.rerun()


def sync_data():
    """مزامنة البيانات بين Firestore و SQLite بطريقة أكثر استقرارًا"""
    st.subheader("🔄 Sync Data")

    # ✅ 1️⃣ التحقق من وجود الأعمدة المطلوبة في SQLite
    cursor.execute("PRAGMA table_info(products)")
    columns_info = cursor.fetchall()
    column_names = [column[1] for column in columns_info]
    st.write("🔍 SQLite Table Structure:", column_names)

    # ✅ إضافة عمود `updated_at` إذا كان مفقودًا
    if "updated_at" not in column_names:
        cursor.execute("ALTER TABLE products ADD COLUMN updated_at TEXT DEFAULT '2000-01-01 00:00:00'")
        conn.commit()
        st.warning("⚠️ Column 'updated_at' was missing and has been added automatically!")

    # ✅ 2️⃣ مزامنة البيانات من Firestore إلى SQLite
    if st.button("⬇ Sync from Firestore"):
        products_ref = db.collection("products").stream()
        for doc in products_ref:
            data = doc.to_dict()
            product_name = data["product_name"]
            updated_at_firestore = data.get("updated_at", "2000-01-01 00:00:00")

            # 🔍 التحقق مما إذا كان المنتج موجودًا بالفعل في SQLite
            cursor.execute("SELECT updated_at FROM products WHERE product_name = ?", (product_name,))
            row = cursor.fetchone()
            updated_at_sqlite = row[0] if row else "2000-01-01 00:00:00"

            if updated_at_firestore > updated_at_sqlite:
                cursor.execute("""
                    INSERT INTO products (category, sub_category, product_name, product_link, 
                    likes, comments, rating, supplier_orders, supplier_price, store_price, updated_at)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    ON CONFLICT(product_name) DO UPDATE SET 
                    category=excluded.category, sub_category=excluded.sub_category, 
                    product_link=excluded.product_link, likes=excluded.likes, 
                    comments=excluded.comments, rating=excluded.rating, 
                    supplier_orders=excluded.supplier_orders, supplier_price=excluded.supplier_price, 
                    store_price=excluded.store_price, updated_at=excluded.updated_at;
                """, (
                    data["category"], data["sub_category"], data["product_name"], data["product_link"],
                    data.get("likes", 0), data.get("comments", 0), data.get("rating", 0.0),
                    data.get("supplier_orders", 0), data.get("supplier_price", 0.0),
                    data.get("store_price", 0.0), updated_at_firestore
                ))

        conn.commit()
        st.success("✅ Synced from Firestore successfully!")

    # ✅ 3️⃣ مزامنة البيانات من SQLite إلى Firestore
    if st.button("⬆ Sync to Firestore"):
        batch = db.batch()
        df_products = pd.read_sql_query("SELECT * FROM products", conn)
        for _, row in df_products.iterrows():
            doc_ref = db.collection("products").document(row["product_name"])
            batch.set(doc_ref, {
                "category": row["category"], "sub_category": row["sub_category"],
                "product_name": row["product_name"], "product_link": row["product_link"],
                "likes": row["likes"], "comments": row["comments"], "rating": row["rating"],
                "supplier_orders": row["supplier_orders"], "supplier_price": row["supplier_price"],
                "store_price": row["store_price"], "updated_at": row["updated_at"]
            })
        batch.commit()
        st.success("✅ Synced to Firestore successfully!")


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
    likes = st.number_input("Likes", min_value=0, step=1)
    comments = st.number_input("Comments", min_value=0, step=1)
    rating = st.slider("Rating", 0.0, 5.0, 0.1)
    supplier_orders = st.number_input("Supplier Orders", min_value=0, step=1)
    supplier_price = st.number_input("Supplier Price (USD)", min_value=0.0, step=0.1)
    store_price = st.number_input("Store Price (USD)", min_value=0.0, step=0.1)

    if st.button("Add Product") and selected_category != "Select" and selected_subcategory != "Select":
        cursor.execute("INSERT INTO products (category, sub_category, product_name, product_link, likes, comments, rating, supplier_orders, supplier_price, store_price) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", 
                       (selected_category, selected_subcategory, product_name, product_link, likes, comments, rating, supplier_orders, supplier_price, store_price))
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
