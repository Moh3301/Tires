import os
import re
import pandas as pd
import streamlit as st

# --- إعدادات الصفحة ---
st.set_page_config(
    page_title="نظام توليد عروض أسعار الإطارات",
    page_icon="🛞",
    layout="centered",
)

st.title("🛞 نظام توليد عروض أسعار الإطارات")


# --- دالات المعالجة والمنطق البرمجي ---
def clean_text(val):
    if pd.isna(val):
        return ""
    s = str(val).strip()
    if s.endswith(".0"):
        s = s[:-2]
    return s


def normalize_size(size_str):
    return str(size_str).strip().lower().replace(" ", "").replace("-", "")


def parse_numeric_price(price_str):
    cleaned = re.sub(r"[^\d.]", "", str(price_str))
    try:
        val = float(cleaned)
        return val if val > 0 else None
    except ValueError:
        return None


def extract_year(year_val):
    if pd.isna(year_val):
        return None
    match = re.search(r"\b(19\d\d|20\d\d)\b", str(year_val).strip())
    if match:
        return int(match.group(1))
    try:
        val = int(float(str(year_val).strip()))
        if 1990 <= val <= 2040:
            return val
    except ValueError:
        pass
    return None


@st.cache_data(ttl=3600)
def load_data_from_file(file_source):
    df = pd.read_excel(file_source)
    df.columns = [str(c).strip() for c in df.columns]

    required_cols = ["القياس", "الماركة", "المنشأ", "الصنع", "السعر"]
    missing = [c for c in required_cols if c not in df.columns]
    if missing:
        st.error(f"الملف لا يحتوي على الأعمدة التالية: {', '.join(missing)}")
        return None
    return df


# --- خيار اختيار/تحديث الملف ---
uploaded_file = st.file_uploader(
    "📂 تغيير ملف الإكسل (اختياري - افتراضياً يتم استخدام ملف المستودع المرفوع)",
    type=["xlsx", "xls"],
)

default_excel_name = "جرد المستودعات العام.xlsx"

if uploaded_file is not None:
    df = load_data_from_file(uploaded_file)
elif os.path.exists(default_excel_name):
    df = load_data_from_file(default_excel_name)
else:
    # محاولة العثور على ملف إكسل بلاحقة xlx أو xlsx إذا اختلف الاسم
    found_files = [
        f
        for f in os.listdir(".")
        if f.endswith(".xlsx") or f.endswith(".xls") or f.endswith(".xlx")
    ]
    if found_files:
        df = load_data_from_file(found_files[0])
    else:
        df = None

if df is None:
    st.warning("⚠️ يرجى رفع ملف الإكسل للبدء.")
    st.stop()

st.success("✅ تم تحميل البيانات بنجاح وجاهزة للبحث.")

# --- قسم خيارات البحث والحساب ---
st.subheader("بيانات الطلب والتسعير")

col_size, col_disc = st.columns([2, 1])

with col_size:
    search_input = st.text_input(
        "القياس المطلوب (مثال: 205/55R16):", key="search_size"
    )

with col_disc:
    discount_percent = st.number_input(
        "خصم (%):", min_value=0.0, max_value=100.0, value=0.0, step=1.0
    )

qty_option = st.radio(
    "الكمية المطلوبة:",
    options=["فردة (افتراضي)", "زوج (فردتين)", "طقم (4 فردات)"],
    horizontal=True,
)

include_older = st.checkbox("تضمين وإظهار أصناف 2024 وما قبل في القائمة")

# --- منطق الاستعلام والبحث ---
if st.button("🔍 توليد الرد", type="primary"):
    if not search_input.strip():
        st.warning("يرجى إدخال القياس المطلوب أولاً.")
    else:
        if qty_option == "زوج (فردتين)":
            multiplier = 2
            qty_label = "للزوج"
            qty_choice = "pair"
        elif qty_option == "طقم (4 فردات)":
            multiplier = 4
            qty_label = "للطقم (4 فردات)"
            qty_choice = "set"
        else:
            multiplier = 1
            qty_label = "للفردة"
            qty_choice = "single"

        target_clean = normalize_size(search_input)
        matches = df[
            df["القياس"].apply(lambda x: normalize_size(x) == target_clean)
        ]

        recent_items = []
        older_items = []
        has_older_available = False

        for _, row in matches.iterrows():
            price_raw = clean_text(row.get("السعر", ""))

            if not price_raw or price_raw.lower() in ["0", "-", "nan", "none"]:
                continue

            unit_price = parse_numeric_price(price_raw)
            if unit_price is None:
                continue

            total_price = unit_price * multiplier
            if discount_percent > 0:
                total_price = total_price * (1 - (discount_percent / 100.0))

            if total_price.is_integer():
                formatted_price = f"{int(total_price)}$"
            else:
                formatted_price = f"{total_price:.2f}$"

            disc_label = (
                int(discount_percent)
                if discount_percent.is_integer()
                else discount_percent
            )
            if discount_percent > 0:
                if qty_choice == "single":
                    price_line = f"سعر الفردة (بعد خصم {disc_label}%): {formatted_price}"
                else:
                    price_line = f"السعر ({qty_label} بعد خصم {disc_label}%): {formatted_price}"
            else:
                if qty_choice == "single":
                    price_line = f"سعر الفردة: {formatted_price}"
                else:
                    price_line = f"السعر ({qty_label}): {formatted_price}"

            brand = clean_text(row.get("الماركة", ""))
            origin = clean_text(row.get("المنشأ", ""))
            year = clean_text(row.get("الصنع", ""))

            item_text = (
                f"الماركة: {brand}\n"
                f"المنشأ: {origin}\n"
                f"الصنع: {year}\n"
                f"{price_line}"
            )

            year_num = extract_year(year)
            if year_num is not None and year_num <= 2024:
                has_older_available = True
                older_items.append(item_text)
            else:
                recent_items.append(item_text)

        if include_older:
            items_to_display = recent_items + older_items
        else:
            items_to_display = recent_items

        # صياغة النص النهائي
        if not recent_items and not older_items:
            final_message = f"مرحباً بك، القياس المطلوب ({search_input}) غير متوفر حالياً في المستودع."
        elif not recent_items and older_items and not include_older:
            lines = [
                "مرحباً بك في شركة تاير ون للإطارات، نعتذر منك فالقياس المطلوب غير متوفر حالياً بتاريخ صنع حديث (2025 - 2026).",
                f"القياس: {search_input}\n",
                "📌 ملاحظة: تتوفر أصناف أخرى من تاريخ صنع 2024 وما قبل للقياس نفسه (يرجى إعلامنا في حال رغبتك بالاطلاع على أسعارها وتفاصيلها).\n",
                "للتواصل والطلب:\n"
                "العنوان: دمشق، البرامكة، دوار الفحامة باتجاه سانا مقابل الباب الخلفي للكراجات. (يتوفر خريطة دقيقة للموقع).\n"
                "هاتف: 0949111341",
            ]
            final_message = "\n".join(lines)
        else:
            lines = [
                "مرحباً بك في شركة تاير ون للإطارات، إليك قائمة الإطارات المتوفرة وفقاً للقياس المطلوب:",
                f"القياس: {search_input}\n",
                "\n----------------------------\n".join(items_to_display),
            ]

            if has_older_available and not include_older:
                lines.append(
                    "\n📌 ملاحظة: تتوفر أيضاً أصناف أخرى من تاريخ صنع 2024 وما قبل للقياس نفسه."
                )

            footer = (
                "\n\nللتواصل والطلب:\n"
                "العنوان: دمشق، البرامكة، دوار الفحامة باتجاه سانا مقابل الباب الخلفي للكراجات. (يتوفر خريطة دقيقة للموقع).\n"
                "هاتف: 0949111341"
            )
            lines.append(footer)

            final_message = "\n".join(lines)

        # عرض النتيجة بداخل مربع نص جاهز للنسخ
        st.subheader("📋 الرسالة الناتجة")
        st.code(final_message, language=None)
