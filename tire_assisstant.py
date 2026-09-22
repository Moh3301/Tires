import json
import os
import re
import tkinter as tk
from tkinter import filedialog, messagebox
import pandas as pd

CONFIG_FILE = "app_config.json"
CACHE_FILE = "cache_data.pkl"


class TireApp:

    def __init__(self, root):
        self.root = root
        self.root.title("مساعد الرد على العملاء - إطارات")
        self.root.geometry("690x810")
        self.root.configure(bg="#f4f6f9")

        self.df = None
        self.file_path = ""

        # --- ترويسة البرنامج ---
        header_frame = tk.Frame(root, bg="#2c3e50", pady=12)
        header_frame.pack(fill="x")
        title_label = tk.Label(
            header_frame,
            text="نظام توليد عروض أسعار الإطارات",
            font=("Segoe UI", 14, "bold"),
            fg="white",
            bg="#2c3e50",
        )
        title_label.pack()

        # --- قسم اختيار وتحديث الملف ---
        file_frame = tk.Frame(root, bg="#f4f6f9", pady=6)
        file_frame.pack(fill="x", padx=20)

        self.btn_load = tk.Button(
            file_frame,
            text="📂 تغيير الملف",
            command=self.choose_file,
            font=("Segoe UI", 9, "bold"),
            bg="#3498db",
            fg="white",
            padx=8,
            pady=3,
            relief="flat",
        )
        self.btn_load.pack(side="right")

        self.btn_reload = tk.Button(
            file_frame,
            text="🔄 تحديث البيانات",
            command=lambda: (
                self.load_data(self.file_path, force_reload=True)
                if self.file_path
                else None
            ),
            font=("Segoe UI", 9, "bold"),
            bg="#95a5a6",
            fg="white",
            padx=8,
            pady=3,
            relief="flat",
        )
        self.btn_reload.pack(side="right", padx=5)

        self.lbl_file = tk.Label(
            file_frame,
            text="جاري التحقق من الملف...",
            font=("Segoe UI", 9),
            bg="#f4f6f9",
            fg="#7f8c8d",
            anchor="e",
        )
        self.lbl_file.pack(side="right", padx=10, fill="x", expand=True)

        # --- شريط حالة التحميل ---
        self.lbl_status = tk.Label(
            root,
            text="",
            font=("Segoe UI", 9, "bold"),
            bg="#f4f6f9",
            fg="#e67e22",
        )
        self.lbl_status.pack(fill="x", padx=20)

        # --- قسم خيارات البحث والحساب ---
        options_frame = tk.LabelFrame(
            root,
            text=" بيانات الطلب والتسعير ",
            font=("Segoe UI", 11, "bold"),
            bg="#f4f6f9",
            padx=15,
            pady=8,
        )
        options_frame.pack(fill="x", padx=20, pady=5)

        # السطر 1: إدخال القياس وأزرار العمليات
        search_line = tk.Frame(options_frame, bg="#f4f6f9")
        search_line.pack(fill="x", pady=(0, 8))

        lbl_size = tk.Label(
            search_line,
            text="القياس:",
            font=("Segoe UI", 10, "bold"),
            bg="#f4f6f9",
        )
        lbl_size.pack(side="right", padx=(5, 5))

        self.entry_size = tk.Entry(
            search_line,
            font=("Segoe UI", 12),
            justify="center",
            relief="solid",
            bd=1,
            width=18,
        )
        self.entry_size.pack(side="right", fill="x", expand=True, padx=(5, 10))
        self.entry_size.bind("<Return>", lambda event: self.generate_response())

        self.btn_clear = tk.Button(
            search_line,
            text="🧹 مسح (C)",
            command=self.clear_all,
            font=("Segoe UI", 10, "bold"),
            bg="#c0392b",
            fg="white",
            padx=12,
            pady=3,
            relief="flat",
        )
        self.btn_clear.pack(side="left", padx=(5, 0))

        self.btn_search = tk.Button(
            search_line,
            text="🔍 توليد الرد ونسخه",
            command=self.generate_response,
            font=("Segoe UI", 10, "bold"),
            bg="#27ae60",
            fg="white",
            padx=15,
            pady=3,
            relief="flat",
        )
        self.btn_search.pack(side="left")

        # السطر 2: خيارات الكمية والخصم
        calc_line = tk.Frame(options_frame, bg="#f4f6f9")
        calc_line.pack(fill="x", pady=(0, 6))

        lbl_qty = tk.Label(
            calc_line,
            text="الكمية المطلوبة:",
            font=("Segoe UI", 10, "bold"),
            bg="#f4f6f9",
        )
        lbl_qty.pack(side="right", padx=(0, 10))

        self.qty_var = tk.StringVar(value="single")

        rb_set = tk.Radiobutton(
            calc_line,
            text="طقم (4 فردات)",
            variable=self.qty_var,
            value="set",
            bg="#f4f6f9",
            font=("Segoe UI", 9, "bold"),
        )
        rb_set.pack(side="right", padx=5)

        rb_pair = tk.Radiobutton(
            calc_line,
            text="زوج (فردتين)",
            variable=self.qty_var,
            value="pair",
            bg="#f4f6f9",
            font=("Segoe UI", 9, "bold"),
        )
        rb_pair.pack(side="right", padx=5)

        rb_single = tk.Radiobutton(
            calc_line,
            text="فردة (افتراضي)",
            variable=self.qty_var,
            value="single",
            bg="#f4f6f9",
            font=("Segoe UI", 9, "bold"),
        )
        rb_single.pack(side="right", padx=5)

        self.entry_discount = tk.Entry(
            calc_line,
            font=("Segoe UI", 10, "bold"),
            justify="center",
            width=5,
            relief="solid",
            bd=1,
        )
        self.entry_discount.insert(0, "0")
        self.entry_discount.pack(side="left", padx=(2, 10))

        lbl_discount = tk.Label(
            calc_line,
            text="خصم (%):",
            font=("Segoe UI", 10, "bold"),
            bg="#f4f6f9",
        )
        lbl_discount.pack(side="left", padx=(10, 2))

        # السطر 3: خيار سنوات الصنع القديمة (2024 وما قبل)
        filter_line = tk.Frame(options_frame, bg="#f4f6f9")
        filter_line.pack(fill="x")

        self.chk_older_var = tk.BooleanVar(value=False)
        self.chk_older = tk.Checkbutton(
            filter_line,
            text="تضمين وإظهار أصناف 2024 وما قبل في القائمة",
            variable=self.chk_older_var,
            font=("Segoe UI", 9, "bold"),
            bg="#f4f6f9",
            fg="#8e44ad",
            activebackground="#f4f6f9",
        )
        self.chk_older.pack(side="right")

        # --- منطقة عرض النص المولد ---
        result_frame = tk.Frame(root, bg="#f4f6f9", padx=20, pady=5)
        result_frame.pack(fill="both", expand=True)

        lbl_result = tk.Label(
            result_frame,
            text="الرسالة الناتجة (تُنسخ تلقائياً إلى الحافظة):",
            font=("Segoe UI", 10, "bold"),
            bg="#f4f6f9",
            anchor="e",
        )
        lbl_result.pack(fill="x", pady=(5, 5))

        self.txt_output = tk.Text(
            result_frame,
            font=("Segoe UI", 11),
            wrap="word",
            padx=10,
            pady=10,
            relief="solid",
            bd=1,
        )
        self.txt_output.pack(fill="both", expand=True)

        # --- زر نسخ يدوي إضافي ---
        self.btn_copy = tk.Button(
            root,
            text="📋 نسخ النص يدوياً",
            command=self.copy_to_clipboard,
            font=("Segoe UI", 11, "bold"),
            bg="#e67e22",
            fg="white",
            pady=6,
            relief="flat",
        )
        self.btn_copy.pack(fill="x", padx=20, pady=(5, 12))

        self.root.bind("<Escape>", lambda event: self.clear_all())
        self.root.after(100, self.auto_load_saved_file)

    def clean_text(self, val):
        if pd.isna(val):
            return ""
        s = str(val).strip()
        if s.endswith(".0"):
            s = s[:-2]
        return s

    def normalize_size(self, size_str):
        return str(size_str).strip().lower().replace(" ", "").replace("-", "")

    def parse_numeric_price(self, price_str):
        cleaned = re.sub(r"[^\d.]", "", str(price_str))
        try:
            val = float(cleaned)
            return val if val > 0 else None
        except ValueError:
            return None

    def extract_year(self, year_val):
        """استخراج سنة الصنع كرقم للتحقق منها بدقة"""
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

    def clear_all(self):
        """مسح الحقول وإعادتها للوضع الافتراضي"""
        self.entry_size.delete(0, tk.END)
        self.txt_output.delete("1.0", tk.END)
        self.entry_discount.delete(0, tk.END)
        self.entry_discount.insert(0, "0")
        self.qty_var.set("single")
        self.chk_older_var.set(False)
        self.entry_size.focus_set()

    def save_config(self, path):
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump({"last_file": path}, f, ensure_ascii=False)
        except Exception:
            pass

    def load_config(self):
        if os.path.exists(CONFIG_FILE):
            try:
                with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                    return json.load(f).get("last_file", "")
            except Exception:
                return ""
        return ""

    def auto_load_saved_file(self):
        saved_path = self.load_config()
        if saved_path and os.path.exists(saved_path):
            self.load_data(saved_path)
        else:
            self.lbl_file.config(
                text="لم يتم تحديد ملف بعد، يرجى اختيار ملف الإكسل",
                fg="#e74c3c",
            )

    def choose_file(self):
        file_path = filedialog.askopenfilename(
            title="اختر ملف الإكسل",
            filetypes=[("Excel Files", "*.xlsx *.xls")],
        )
        if file_path:
            self.load_data(file_path, force_reload=True)

    def load_data(self, file_path, force_reload=False):
        try:
            self.file_path = file_path
            excel_mtime = os.path.getmtime(file_path)

            cache_valid = (
                os.path.exists(CACHE_FILE)
                and (os.path.getmtime(CACHE_FILE) >= excel_mtime)
                and not force_reload
            )

            if cache_valid:
                self.lbl_status.config(
                    text="⚡ جاري الفتح الفوري من الذاكرة المؤقتة...",
                    fg="#2980b9",
                )
                self.root.update_idletasks()
                self.df = pd.read_pickle(CACHE_FILE)
                self.lbl_file.config(
                    text=f"{os.path.basename(file_path)} (جاهز)", fg="#27ae60"
                )
                self.lbl_status.config(text="")
            else:
                self.lbl_status.config(
                    text="⏳ جاري معالجة وتجهيز ملف الإكسل (يرجى الانتظار)...",
                    fg="#d35400",
                )
                self.lbl_file.config(
                    text=os.path.basename(file_path), fg="#e67e22"
                )
                self.root.update_idletasks()

                df = pd.read_excel(file_path)
                df.columns = [str(c).strip() for c in df.columns]

                required_cols = [
                    "القياس",
                    "الماركة",
                    "المنشأ",
                    "الصنع",
                    "السعر",
                ]
                missing = [c for c in required_cols if c not in df.columns]
                if missing:
                    messagebox.showerror(
                        "خطأ في الأعمدة",
                        f"الملف لا يحتوي على الأعمدة التالية:\n{', '.join(missing)}",
                    )
                    self.lbl_status.config(text="")
                    return

                self.df = df
                self.df.to_pickle(CACHE_FILE)
                self.save_config(file_path)

                self.lbl_file.config(
                    text=f"{os.path.basename(file_path)} (تم التحديث والجاهزية)",
                    fg="#27ae60",
                )
                self.lbl_status.config(text="")

        except Exception as e:
            self.lbl_status.config(text="")
            messagebox.showerror("خطأ", f"حدث خطأ أثناء تحميل الملف:\n{str(e)}")

    def generate_response(self):
        if self.df is None:
            messagebox.showwarning("تنبيه", "يرجى اختيار ملف الإكسل أولاً.")
            return

        search_input = self.entry_size.get().strip()
        if not search_input:
            messagebox.showwarning("تنبيه", "يرجى إدخال القياس المطلوب.")
            return

        discount_str = self.entry_discount.get().strip()
        try:
            discount_percent = (
                float(discount_str) if discount_str else 0.0
            )
            if discount_percent < 0 or discount_percent > 100:
                raise ValueError
        except ValueError:
            messagebox.showwarning(
                "خطأ في الخصم",
                "يرجى إدخال نسبة خصم صحيحة بين 0 و 100 (مثال: 5 أو 10).",
            )
            return

        qty_choice = self.qty_var.get()
        if qty_choice == "pair":
            multiplier = 2
            qty_label = "للزوج"
        elif qty_choice == "set":
            multiplier = 4
            qty_label = "للطقم (4 فردات)"
        else:
            multiplier = 1
            qty_label = "للفردة"

        target_clean = self.normalize_size(search_input)

        matches = self.df[
            self.df["القياس"].apply(
                lambda x: self.normalize_size(x) == target_clean
            )
        ]

        recent_items = []  # 2025 و 2026
        older_items = []  # 2024 وما قبل
        has_older_available = False

        for _, row in matches.iterrows():
            price_raw = self.clean_text(row.get("السعر", ""))

            # تجاهل الإطارات غير المسعرة
            if not price_raw or price_raw.lower() in ["0", "-", "nan", "none"]:
                continue

            unit_price = self.parse_numeric_price(price_raw)
            if unit_price is None:
                continue

            total_price = unit_price * multiplier
            if discount_percent > 0:
                total_price = total_price * (1 - (discount_percent / 100.0))

            if total_price.is_integer():
                formatted_price = f"{int(total_price)}$"
            else:
                formatted_price = f"{total_price:.2f}$"

            # صياغة سطر السعر مع توضيح "سعر الفردة" بشكل صريح
            disc_label = (
                int(discount_percent)
                if discount_percent.is_integer()
                else discount_percent
            )
            if discount_percent > 0:
                if qty_choice == "single":
                    price_line = (
                        f"سعر الفردة (بعد خصم {disc_label}%): {formatted_price}"
                    )
                else:
                    price_line = f"السعر ({qty_label} بعد خصم {disc_label}%): {formatted_price}"
            else:
                if qty_choice == "single":
                    price_line = f"سعر الفردة: {formatted_price}"
                else:
                    price_line = f"السعر ({qty_label}): {formatted_price}"

            brand = self.clean_text(row.get("الماركة", ""))
            origin = self.clean_text(row.get("المنشأ", ""))
            year = self.clean_text(row.get("الصنع", ""))

            item_text = (
                f"الماركة: {brand}\n"
                f"المنشأ: {origin}\n"
                f"الصنع: {year}\n"
                f"{price_line}"
            )

            # فرز الصنف حسب تاريخ الصنع
            year_num = self.extract_year(year)
            if year_num is not None and year_num <= 2024:
                has_older_available = True
                older_items.append(item_text)
            else:
                recent_items.append(item_text)

        # تحديد الأصناف المعروضة بناءً على خيار المستخدم
        include_older = self.chk_older_var.get()
        if include_older:
            items_to_display = recent_items + older_items
        else:
            items_to_display = recent_items

        # الحالة 1: لا يوجد أي صنف مسعر إطلاقاً
        if not recent_items and not older_items:
            self.txt_output.delete("1.0", tk.END)
            msg = f"مرحباً بك، القياس المطلوب ({search_input}) غير متوفر حالياً في المستودع."
            self.txt_output.insert(tk.END, msg)
            return

        # الحالة 2: لا يوجد أصناف 2025/2026 ولكن يوجد 2024 وما قبل (ولم يفعّل خيار إظهار القديم)
        if not recent_items and older_items and not include_older:
            lines = [
                "مرحباً بك في شركة تاير ون للإطارات، نعتذر منك فالقياس المطلوب غير متوفر حالياً بتاريخ صنع حديث (2025 - 2026).",
                f"القياس: {search_input}\n",
                "📌 ملاحظة: تتوفر أصناف أخرى من تاريخ صنع 2024 وما قبل للقياس نفسه (يرجى إعلامنا في حال رغبتك بالاطلاع على أسعارها وتفاصيلها).\n",
                "للتواصل والطلب:\n"
                "العنوان: دمشق، البرامكة، دوار الفحامة باتجاه سانا مقابل الباب الخلفي للكراجات. (يتوفر خريطة دقيقة للموقع).\n"
                "هاتف: 0949111341",
            ]
            final_message = "\n".join(lines)
            self.txt_output.delete("1.0", tk.END)
            self.txt_output.insert(tk.END, final_message)
            self.root.clipboard_clear()
            self.root.clipboard_append(final_message)
            return

        # الحالة 3: بناء الرسالة الطبيعية للأصناف المتوفرة
        lines = []
        lines.append(
            "مرحباً بك في شركة تاير ون للإطارات، إليك قائمة الإطارات المتوفرة وفقاً للقياس المطلوب:"
        )
        lines.append(f"القياس: {search_input}\n")
        lines.append("\n----------------------------\n".join(items_to_display))

        # إضافة ملاحظة وجود 2024 وما قبل في حال لم تكن معروضة ولكنها موجودة بالمستودع
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

        self.txt_output.delete("1.0", tk.END)
        self.txt_output.insert(tk.END, final_message)

        self.root.clipboard_clear()
        self.root.clipboard_append(final_message)

    def copy_to_clipboard(self):
        content = self.txt_output.get("1.0", tk.END).strip()
        if content:
            self.root.clipboard_clear()
            self.root.clipboard_append(content)
            messagebox.showinfo("تم النسخ", "تم نسخ الرسالة إلى الحافظة بنجاح!")


if __name__ == "__main__":
    root = tk.Tk()
    app = TireApp(root)
    root.mainloop()