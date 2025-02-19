
import streamlit as st
import pandas as pd
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


def manage_categories():
    """إدارة الفئات والفئات الفرعية باستخدام Firestore فقط"""
    st.subheader("Manage Categories and Subcategories")
    
    categories_ref = db.collection("categories")

    new_category = st.text_input("Add New Category")
    if st.button("Add Category") and new_category.strip():
        categories_ref.document(new_category).set({"category": new_category})
        st.success("✅ Category added successfully!")
        st.rerun()
    
    categories = [doc.id for doc in categories_ref.stream()]
    selected_category = st.selectbox("Select Category", ["Select"] + categories)

    if selected_category != "Select":
        subcategories_ref = db.collection("categories").document(selected_category).collection("subcategories")

        new_subcategory = st.text_input("Add Subcategory")
        if st.button("Add Subcategory") and new_subcategory.strip():
            subcategories_ref.document(new_subcategory).set({"sub_category": new_subcategory})
            st.success("✅ Subcategory added successfully!")
            st.rerun()

        subcategories = [doc.id for doc in subcategories_ref.stream()]
        st.write("### Subcategories", subcategories)

        if st.button("Delete Category"):
            db.collection("categories").document(selected_category).delete()
            st.warning(f"⚠️ Category '{selected_category}' and its subcategories deleted!")
            st.rerun()




def view_products():
    """عرض المنتجات من Firestore فقط"""
    st.subheader("View Products")

    products_ref = db.collection("products").stream()
    products = [doc.to_dict() for doc in products_ref]

    if products:
        df_products = pd.DataFrame(products)
        st.dataframe(df_products)
    else:
        st.info("لا توجد منتجات متاحة")




def import_export_data():
    """استيراد وتصدير البيانات إلى Firestore"""
    st.subheader("Import/Export Data")

    if st.button("Export Data"):
        products_ref = db.collection("products").stream()
        products = [doc.to_dict() for doc in products_ref]
        df_products = pd.DataFrame(products)
        df_products.to_csv("products_export.csv", index=False)
        st.success("✅ Data exported successfully!")

    uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])
    if uploaded_file is not None:
        df_uploaded = pd.read_csv(uploaded_file)

        for _, row in df_uploaded.iterrows():
            db.collection("products").document(row["product_name"]).set({
                "category": row["category"], "sub_category": row["sub_category"],
                "product_name": row["product_name"], "product_link": row["product_link"],
                "likes": row["likes"], "comments": row["comments"], "rating": row["rating"],
                "supplier_orders": row["supplier_orders"], "supplier_price": row["supplier_price"],
                "store_price": row["store_price"], "updated_at": row["updated_at"]
            })
        
        st.success("✅ Data imported successfully!")
        st.rerun()



def sync_data():
    """مزامنة البيانات بين Firestore فقط"""
    st.subheader("🔄 Sync Data")

    if st.button("⬇ Sync from Firestore"):
        products_ref = db.collection("products").stream()
        products = [doc.to_dict() for doc in products_ref]
        st.write("📥 Firestore Data:", products)
        st.success("✅ Data loaded from Firestore successfully!")

    if st.button("⬆ Sync to Firestore"):
        st.success("⚠️ Syncing is now automatic in Firestore and no longer requires manual syncing!")


def add_product():
    """إضافة منتج جديد مباشرة إلى Firestore"""
    st.subheader("Add New Product")

    categories = [doc.id for doc in db.collection("categories").stream()]
    selected_category = st.selectbox("Select Product Category", ["Select"] + categories)

    subcategories = []
    if selected_category != "Select":
        subcategories = [doc.id for doc in db.collection("categories").document(selected_category).collection("subcategories").stream()]

    selected_subcategory = st.selectbox("Select Subcategory", ["Select"] + subcategories)
    product_name = st.text_input("Product Name")
    product_link = st.text_input("Product Link")
    likes = st.number_input("Likes", min_value=0, step=1)
    comments = st.number_input("Comments", min_value=0, step=1)
    rating = st.slider("Rating", 0.0, 5.0, 0.1)
    supplier_orders = st.number_input("Supplier Orders", min_value=0, step=1)
    supplier_price = st.number_input("Supplier Price (USD)", min_value=0.0, step=0.1)
    store_price = st.number_input("Store Price (USD)", min_value=0.0, step=0.1)

    if st.button("Add Product") and selected_category != "Select" and selected_subcategory != "Select":
        db.collection("products").document(product_name).set({
            "category": selected_category, "sub_category": selected_subcategory,
            "product_name": product_name, "product_link": product_link,
            "likes": likes, "comments": comments, "rating": rating,
            "supplier_orders": supplier_orders, "supplier_price": supplier_price,
            "store_price": store_price, "updated_at": "2024-01-01 00:00:00"
        })
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
