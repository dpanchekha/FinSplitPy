import streamlit as st
import pandas as pd
import sqlite3
import io
import plotly.express as px
import re as rgx
import locale
import os

# Set locale for currency parsing
try:
    locale.setlocale(locale.LC_ALL, 'en_US.UTF8')
except locale.Error:
    pass  # Fallback if locale is unavailable

# Path to the SQLite database in the current working directory
DB_FILENAME = 'your_database.sqlite'
DB_PATH = os.path.join(os.getcwd(), DB_FILENAME)

# --- Database Initialization ---
def init_db():
    """
    Initialize the SQLite database file in the working directory.
    """
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    # Create table if it does not exist
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS Transactions (
            amount REAL,
            name TEXT,
            date TEXT,
            memo TEXT,
            "account number" TEXT,
            "account name" TEXT,
            "Transaction ID" TEXT
        )
    """)
    conn.commit()
    conn.close()

# --- Utility Functions ---
def str_curr_to_float(money: str) -> float:
    money = money.strip("$").replace(",", "")
    try:
        return float(money)
    except ValueError:
        return 0.0


def send_sql(query: str, params: tuple = ()): 
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()


def read_sql(query: str, params: tuple = ()) -> list:
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows


def exists_in_transactions(values: tuple) -> bool:
    query = """
        SELECT 1 FROM Transactions
        WHERE amount = ? AND name = ? AND date = ? AND memo = ?
          AND "account number" = ? AND "account name" = ? AND "Transaction ID" = ?
        LIMIT 1
    """
    return len(read_sql(query, values)) > 0


def add_transaction(amount: float, name: str, date: str, memo: str,
                    account_num: str, account_name: str, transaction_id: str):
    values = (amount, name, date, memo, account_num, account_name, transaction_id)
    if not exists_in_transactions(values):
        send_sql(
            """
            INSERT INTO Transactions
            (amount, name, date, memo, "account number", "account name", "Transaction ID")
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            values
        )


def process_sheet(df: pd.DataFrame):
    account_num = ""
    account_name = ""
    for _, row in df.iterrows():
        if pd.isna(row.get("Account Details")) and pd.isna(row.get("Entity Code")):
            continue

        if not pd.isna(row.get("Account Details")):
            acct_det = row["Account Details"]
            if rgx.match(r"^\d{4}-\d{3}-\d{4}$", str(acct_det)[:13]):
                account_num = str(acct_det)[:13]
                account_name = str(acct_det)[13:]
        else:
            amt = str_curr_to_float(
                str(row.get("Credit")) if not pd.isna(row.get("Credit")) else str(row.get("Debit"))
            )
            name = (str(row.get("Original Master Name"))
                    if not pd.isna(row.get("Original Master Name"))
                    else str(row.get("Memo/ Description")))
            date = str(row.get("Transaction Date"))
            memo = str(row.get("Memo/ Description"))
            transaction_id = str(row.get("Transaction ID"))
            add_transaction(amt, name, date, memo, account_num, account_name, transaction_id)


def get_all_transactions_df() -> pd.DataFrame:
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT * FROM Transactions", conn)
    conn.close()
    return df