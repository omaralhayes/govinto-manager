def view_products():
    """عرض المنتجات من Firestore باستخدام st.dataframe() بتنسيق مطابق للجدول المرفق"""
    st.subheader("📦 View Products")

    # جلب جميع المنتجات من Firestore
    products_ref = db.collection("products").stream()
    products = [doc.to_dict() for doc in products_ref]

    if products:
        df_products = pd.DataFrame(products)

        # ✅ ترتيب الأعمدة ليطابق الجدول المرفق
        column_order = ["category", "sub_category", "product_name", "product_link",
                        "rating", "supplier_orders", "likes", "comments",
                        "supplier_price", "store_price", "updated_at"]

        # ✅ التأكد من أن جميع الأعمدة موجودة وإضافة القيم الافتراضية إذا كانت مفقودة
        for col in column_order:
            if col not in df_products.columns:
                df_products[col] = "N/A"

        # ✅ إعادة ترتيب الأعمدة
        df_products = df_products[column_order]

        # ✅ عرض الجدول باستخدام st.dataframe() مع تمرير أفقي افتراضي
        st.dataframe(df_products, width=1600, height=600)

    else:
        st.info("❌ No products available.")
