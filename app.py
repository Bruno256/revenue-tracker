import sqlite3
from datetime import date, datetime, timedelta
from io import BytesIO
from pathlib import Path

import streamlit as st
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas

DB_PATH = "revenue.db"


# ---------------------------
# DATABASE
# ---------------------------

def init_db():
    conn = sqlite3.connect(DB_PATH)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS sales (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sale_date TEXT NOT NULL,
            customer_name TEXT NOT NULL,
            item_description TEXT NOT NULL,
            amount REAL NOT NULL,
            payment_method TEXT NOT NULL
        )
    """)
    conn.commit()
    conn.close()


def add_sale(sale_date, customer, item, amount, payment):
    conn = sqlite3.connect(DB_PATH)
    conn.execute(
        """
        INSERT INTO sales (sale_date, customer_name, item_description, amount, payment_method)
        VALUES (?, ?, ?, ?, ?)
        """,
        (sale_date, customer, item, amount, payment),
    )
    conn.commit()
    conn.close()


def get_sales(limit=12):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    rows = conn.execute(
        """
        SELECT * FROM sales
        ORDER BY sale_date DESC, id DESC
        LIMIT ?
        """,
        (limit,),
    ).fetchall()
    conn.close()
    return [dict(r) for r in rows]


def get_summary():
    today = date.today()
    week_start = today - timedelta(days=today.weekday())
    month_start = today.replace(day=1)

    conn = sqlite3.connect(DB_PATH)

    daily = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM sales WHERE sale_date=?",
        (today.isoformat(),)
    ).fetchone()[0]

    weekly = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM sales WHERE sale_date>=?",
        (week_start.isoformat(),)
    ).fetchone()[0]

    monthly = conn.execute(
        "SELECT COALESCE(SUM(amount),0) FROM sales WHERE sale_date>=?",
        (month_start.isoformat(),)
    ).fetchone()[0]

    conn.close()

    return daily, weekly, monthly


def get_sale_by_id(sale_id):
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    row = conn.execute(
        "SELECT * FROM sales WHERE id=?",
        (sale_id,),
    ).fetchone()
    conn.close()

    return dict(row) if row else None


# ---------------------------
# PDF RECEIPT
# ---------------------------

def generate_receipt(sale):
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4

    c.setFont("Helvetica-Bold", 16)
    c.drawString(50, height - 60, "Sales Receipt")

    c.setFont("Helvetica", 11)

    fields = [
        ("Receipt #", sale["id"]),
        ("Date", sale["sale_date"]),
        ("Customer", sale["customer_name"]),
        ("Description", sale["item_description"]),
        ("Payment", sale["payment_method"]),
        ("Amount", f"${sale['amount']:.2f}")
    ]

    y = height - 120
    for k, v in fields:
        c.drawString(50, y, f"{k}: {v}")
        y -= 25

    c.save()

    buffer.seek(0)
    return buffer


# ---------------------------
# APP UI
# ---------------------------

init_db()

st.title("Revenue Tracker")

# Summary
daily, weekly, monthly = get_summary()

col1, col2, col3 = st.columns(3)

col1.metric("Today's Income", f"${daily:.2f}")
col2.metric("Weekly Income", f"${weekly:.2f}")
col3.metric("Monthly Income", f"${monthly:.2f}")


# ---------------------------
# ADD SALE FORM
# ---------------------------

st.subheader("Add Sale")

with st.form("sales_form"):

    sale_date = st.date_input("Sale Date", value=date.today())
    customer = st.text_input("Customer Name", "Walk-in")
    item = st.text_input("Item Description", "General sale")
    payment = st.selectbox("Payment Method", ["Cash", "Mobile Money", "Card"])
    amount = st.number_input("Amount", min_value=0.0)

    submit = st.form_submit_button("Add Sale")

    if submit and amount > 0:
        add_sale(sale_date.isoformat(), customer, item, amount, payment)
        st.success("Sale recorded")


# ---------------------------
# RECENT SALES
# ---------------------------

st.subheader("Recent Sales")

sales = get_sales()

if sales:
    st.dataframe(sales)

    st.subheader("Download Receipt")

    sale_ids = [s["id"] for s in sales]
    selected = st.selectbox("Select Sale ID", sale_ids)

    if selected:
        sale = get_sale_by_id(selected)
        pdf = generate_receipt(sale)

        st.download_button(
            label="Download Receipt PDF",
            data=pdf,
            file_name=f"receipt-{selected}.pdf",
            mime="application/pdf"
        )
else:
    st.info("No sales recorded yet.")