
from datetime import datetime
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import firebase_admin
from firebase_admin import credentials, firestore

if "menu" not in st.session_state:
    st.session_state["menu"] = "🏠 Home"  # تعيين الصفحة الافتراضية


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

# ✅ هنا يجب إضافة الدالة
def get_user_from_firestore(username):
    """جلب بيانات المستخدم من Firestore"""
    try:
        user_ref = db.collection("users").document(username).get()
        if user_ref.exists:
            user_data = user_ref.to_dict()
            return user_data  # إرجاع البيانات كما هي بدون تعديل
        else:
            return None  # المستخدم غير موجود
    except Exception as e:
        st.error(f"❌ Error fetching user data: {e}")
        return None


def login():
    """نظام تسجيل الدخول، يظهر في الصفحة الرئيسية قبل تسجيل الدخول، وفي القائمة الجانبية بعده."""
    
    if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
        # ✅ عرض نموذج تسجيل الدخول في الصفحة الرئيسية عند عدم تسجيل الدخول
        st.image("govinto_logo.png", use_container_width=True)  # ✅ شعار Govinto
        st.subheader("🔐 Login")

        username = st.text_input("👤 Username", key="username_input_home")
        password = st.text_input("🔑 Password", type="password", key="password_input_home")
        login_button = st.button("🔓 Login")

        if login_button:
            user_data = get_user_from_firestore(username.strip())
            
            if user_data and user_data.get("password") == password:
                st.session_state["authenticated"] = True
                st.session_state["role"] = user_data.get("role", "user")
                st.session_state["username"] = username

                st.success(f"✅ Welcome, {username}!")
                st.session_state["reload"] = True
                st.rerun()
            else:
                st.error("❌ Invalid credentials! Please try again.")

    else:
        # ✅ عرض نموذج تسجيل الدخول فقط في القائمة الجانبية بعد تسجيل الدخول
        st.sidebar.image("govinto_logo.png", use_container_width=True)
        st.sidebar.subheader(f"✅ Logged in as: {st.session_state['username']}")
        
        if st.sidebar.button("🚪 Logout"):
            st.session_state.clear()
            st.rerun()

  



def manage_categories():
    """إدارة الفئات والفئات الفرعية باستخدام Firestore فقط"""

    # ✅ الحماية: السماح فقط للمطور بالوصول إلى هذه الصفحة
    if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
        st.warning("🔐 Please log in to access this page.")
        st.stop()  # ⛔️ يمنع تشغيل الصفحة إذا لم يكن المستخدم مسجلاً للدخول

    if st.session_state["role"] != "developer":
        st.warning("❌ You do not have permission to access this page.")
        st.stop()  # ⛔️ يمنع تشغيل الصفحة إذا لم يكن المستخدم "developer"

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
    """عرض المنتجات من Firestore باستخدام st.dataframe() بنفس التنسيق الداكن"""

    # ✅ الحماية: منع الوصول للمستخدمين غير المسجلين
    if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
        st.warning("🔐 Please log in to access this page.")
        st.stop()  # ⛔️ يمنع تشغيل الصفحة إذا لم يكن المستخدم مسجلاً للدخول

    st.subheader("📦 View Products")

    # ✅ جلب جميع المنتجات من Firestore
    products_ref = db.collection("products").stream()
    products = [{**doc.to_dict(), "id": doc.id} for doc in products_ref]  # إضافة `id` داخليًا للحذف

    if products:
        df_products = pd.DataFrame(products)

        # ✅ ترتيب الأعمدة ليكون متوافقًا مع الجدول المرفق، مع إخفاء `id`
        column_order = ["category", "sub_category", "product_name", "product_link",
                        "rating", "supplier_orders", "likes", "comments",
                        "supplier_price", "store_price", "updated_at"]

        # ✅ إزالة الصفوف التي تحتوي على جميع القيم فارغة
        df_products = df_products.dropna(how="all")

        # ✅ إخفاء `id` ولكن الاحتفاظ به في الخلفية للحذف
        df_display = df_products[column_order]

        # ✅ تنسيق الجدول في الوضع الداكن `Dark Mode`
        styled_df = df_display.style.set_properties(**{
            'background-color': '#1E1E1E',  # لون الخلفية غامق
            'color': 'white',  # لون النص أبيض
            'border': '1px solid #444',  # لون الإطار رمادي غامق
            'text-align': 'center',  # محاذاة النصوص
            'font-size': '14px'  # حجم الخط داخل الخلايا
        })

        # ✅ عرض الجدول مع التمرير الأفقي، وفرز وبحث تلقائي
        st.dataframe(styled_df, width=1400, height=500)

        # ✅ إضافة خيار حذف منتج معين من الجدول باستخدام `id`
        st.write("### 🗑️ Delete a Product")
        product_options = df_products.set_index("product_name")["id"].to_dict()  # ربط الاسم بـ `id`

        selected_product_name = st.selectbox("Select a product to delete", ["Select"] + list(product_options.keys()))

        if st.button("🗑️ Delete Product") and selected_product_name != "Select":
            product_id = product_options[selected_product_name]
            db.collection("products").document(product_id).delete()
            st.warning(f"⚠️ Product '{selected_product_name}' deleted successfully!")
            st.rerun()

        # ✅ زر لحذف جميع المنتجات مع تأكيد قبل الحذف
        st.write("### ⚠ Delete All Products")
        if st.button("⚠ Delete ALL Products"):
            st.warning("⚠ Are you sure you want to delete ALL products? This action cannot be undone!")
            if st.button("✅ Confirm Delete All", key="confirm_delete_all"):
                docs = db.collection("products").stream()
                for doc in docs:
                    doc.reference.delete()
                st.error("⚠ All products have been deleted!")
                st.rerun()

    else:
        st.info("❌ No products available.")






def import_export_data():
    """استيراد وتصدير البيانات إلى Firestore"""

    # ✅ الحماية: منع الوصول للمستخدمين غير المسجلين
    if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
        st.warning("🔐 Please log in to access this page.")
        st.stop()  # ⛔️ يمنع تشغيل الصفحة إذا لم يكن المستخدم مسجلاً للدخول

    st.subheader("📤 Import/Export Data")

    # ✅ تصدير البيانات بتنسيق مطابق لـ View Products
    if st.button("📥 Export Data (CSV)"):
        products_ref = db.collection("products").stream()
        products = [doc.to_dict() for doc in products_ref]
        df_products = pd.DataFrame(products)

        # ✅ ترتيب الأعمدة بنفس ترتيب `view_products()`
        column_order = ["category", "sub_category", "product_name", "product_link",
                        "rating", "supplier_orders", "likes", "comments",
                        "supplier_price", "store_price", "updated_at"]
        
        # ✅ التأكد من أن جميع الأعمدة موجودة وإضافة القيم الافتراضية إذا كانت مفقودة
        for col in column_order:
            if col not in df_products.columns:
                df_products[col] = "N/A"

        # ✅ إعادة ترتيب الأعمدة بنفس ترتيب `View Products`
        df_products = df_products[column_order]

        # ✅ حفظ الملف بصيغة CSV مع ترميز UTF-8 لدعم النصوص العربية
        csv_file = "products_export.csv"
        df_products.to_csv(csv_file, index=False, encoding="utf-8-sig")

        # ✅ توفير رابط تحميل الملف بعد التصدير
        with open(csv_file, "rb") as f:
            st.download_button(
                label="📥 Download Exported CSV",
                data=f,
                file_name="products_export.csv",
                mime="text/csv"
            )

        st.success("✅ Data exported successfully!")

    # ✅ استيراد البيانات من ملف CSV
    uploaded_file = st.file_uploader("📂 Upload CSV File", type=["csv"])
    if uploaded_file is not None:
        df_uploaded = pd.read_csv(uploaded_file)

        # ✅ التحقق من أن جميع الحقول المطلوبة موجودة
        required_fields = {"category", "sub_category", "product_name", "product_link",
                           "rating", "supplier_orders", "likes", "comments",
                           "supplier_price", "store_price", "updated_at"}

        if not required_fields.issubset(set(df_uploaded.columns)):
            st.error("❌ The uploaded file is missing required columns!")
        else:
            # ✅ إدراج البيانات إلى Firestore
            for _, row in df_uploaded.iterrows():
                db.collection("products").document(row["product_name"]).set({
                    "category": row["category"], "sub_category": row["sub_category"],
                    "product_name": row["product_name"], "product_link": row["product_link"],
                    "likes": int(row["likes"]), "comments": int(row["comments"]), 
                    "rating": float(row["rating"]), "supplier_orders": int(row["supplier_orders"]),
                    "supplier_price": float(row["supplier_price"]), "store_price": float(row["store_price"]),
                    "updated_at": row["updated_at"]
                })

            st.success("✅ Data imported successfully!")
            st.rerun()



def add_product():
    """إضافة منتج جديد مباشرة إلى Firestore"""

    # ✅ الحماية: منع الوصول للمستخدمين غير المسجلين
    if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
        st.warning("🔐 Please log in to access this page.")
        st.stop()  # ⛔️ يمنع تشغيل الصفحة إذا لم يكن المستخدم مسجلاً للدخول

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
            "store_price": store_price,
            "updated_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        })
        st.success("✅ Product added successfully!")
        st.rerun()



def home():
    """ الصفحة الرئيسية - لوحة معلومات تفاعلية """

    # ✅ عرض الشعار فقط عند تسجيل الدخول
    if "authenticated" in st.session_state and st.session_state["authenticated"]:
        st.image("govinto_logo.png", use_container_width=True)

    # ✅ التحقق من تسجيل الدخول، إذا لم يكن المستخدم مسجلًا، عرض نموذج تسجيل الدخول
    if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
        login()
        return  # ⛔ منع تحميل باقي الصفحة إذا لم يتم تسجيل الدخول

    st.title("🏠 Welcome to Govinto Manager!")
    st.write("📊 Below is a quick overview of your store's performance.")

    # ✅ جلب بيانات المنتجات والفئات من Firestore
    products_ref = db.collection("products").stream()
    categories_ref = db.collection("categories").stream()

    # ✅ تحويل البيانات إلى DataFrames
    products = [doc.to_dict() for doc in products_ref]
    categories = [doc.id for doc in categories_ref]

    df_products = pd.DataFrame(products)

    # ✅ حساب الإحصائيات
    total_products = len(df_products)
    total_categories = len(categories)
    
    most_liked_product = df_products.loc[df_products["likes"].idxmax()] if not df_products.empty else None
    most_commented_product = df_products.loc[df_products["comments"].idxmax()] if not df_products.empty else None

    # ✅ عرض الإحصائيات الرئيسية
    col1, col2, col3 = st.columns(3)
    col1.metric(label="📦 Total Products", value=total_products)
    col2.metric(label="📂 Total Categories", value=total_categories)
    col3.metric(label="👍 Most Liked", value=most_liked_product["product_name"] if most_liked_product is not None else "N/A")

    st.markdown("---")

    # ✅ عرض المنتجات الأكثر تفاعلًا
    st.subheader("🔥 Top Interacting Products")
    if not df_products.empty:
        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="💬 Most Commented", value=most_commented_product["product_name"] if most_commented_product is not None else "N/A")
        with col2:
            st.metric(label="❤ Most Liked", value=most_liked_product["product_name"] if most_liked_product is not None else "N/A")
    else:
        st.info("❌ No products available yet!")






def main():
    """ الواجهة الرئيسية للتحكم في التنقل بين الصفحات """

    # ✅ التحقق مما إذا كان المستخدم مسجلًا، وإذا لم يكن، تشغيل `login()` فقط
    if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
        login()
        return  # ⛔ منع تشغيل أي شيء آخر حتى يتم تسجيل الدخول

    # ✅ التأكد من أن menu و role معرفان قبل استخدامهما
    if "menu" not in st.session_state:
        st.session_state["menu"] = "🏠 Home"

    if "role" not in st.session_state:
        st.session_state["role"] = "user"  # تعيين الدور الافتراضي للمستخدم العادي

    # ✅ تشغيل الصفحة بناءً على menu
    if st.session_state["menu"] == "🏠 Home":
        home()
    elif st.session_state["menu"] == "➕ Add Product":
        add_product()
    elif st.session_state["menu"] == "📂 Manage Categories":
        manage_categories()
    elif st.session_state["menu"] == "📦 View Products":
        view_products()
    elif st.session_state["menu"] == "📤 Import/Export Data":
        import_export_data()

    # ✅ إضافة القائمة الأفقية أسفل كل الصفحات بعد تسجيل الدخول فقط
    st.markdown("---")
    selected_page = st.selectbox(
        "",  # ✅ إزالة عنوان القائمة لجعلها أكثر أناقة
        ["🏠 Home", "➕ Add Product", "📦 View Products", "📤 Import/Export Data"] + (["📂 Manage Categories"] if st.session_state["role"] == "developer" else [])
    )

    # ✅ تحديث `menu` بناءً على الخيار المحدد
    if selected_page != st.session_state["menu"]:
        st.session_state["menu"] = selected_page
        st.rerun()
        
if __name__ == "__main__":
    main()
