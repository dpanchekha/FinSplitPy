import dash
from dash import dcc, html, Input, Output, State
import pandas as pd
import sqlite3
import base64
import io
import plotly.express as px
import re as rgx
import locale
import os

# Ensure locale for currency parsing
locale.setlocale(locale.LC_ALL, 'en_US.UTF8')

# Path to the SQLite database in the current working directory
db_filename = 'your_database.sqlite'
db_path = os.path.join(os.getcwd(), db_filename)

# --- Database Initialization ---
def init_db():
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(
        '''
        CREATE TABLE IF NOT EXISTS Transactions (
            amount REAL,
            name TEXT,
            date TEXT,
            memo TEXT,
            "account number" TEXT,
            "account name" TEXT,
            "Transaction ID" TEXT
        )
        '''
    )
    conn.commit()
    conn.close()

# --- Shared Logic ---
def str_curr_to_float(money: str):
    money = money.strip("$").replace(",", "")
    try:
        return float(money)
    except ValueError:
        return 0.0

def send_sql(query: str, params: tuple = ()):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(query, params)
    conn.commit()
    conn.close()

def read_sql(query: str, params: tuple = ()):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    cursor.execute(query, params)
    rows = cursor.fetchall()
    conn.close()
    return rows

def exists_in_transactions(values: tuple):
    sql = '''
        SELECT 1 FROM Transactions
        WHERE amount = ? AND name = ? AND date = ? AND memo = ?
          AND "account number" = ? AND "account name" = ? AND "Transaction ID" = ?
        LIMIT 1
    '''
    return len(read_sql(sql, values)) > 0

def add_transaction(amount, name, date, memo, account_num, account_name, transaction_id):
    values = (amount, name, date, memo, account_num, account_name, transaction_id)
    if not exists_in_transactions(values):
        sql = '''
            INSERT INTO Transactions
            (amount, name, date, memo, "account number", "account name", "Transaction ID")
            VALUES (?, ?, ?, ?, ?, ?, ?)
        '''
        send_sql(sql, values)

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
            amt = str_curr_to_float(str(row.get("Credit")) if not pd.isna(row.get("Credit")) else str(row.get("Debit")))
            name = str(row.get("Original Master Name")) if not pd.isna(row.get("Original Master Name")) else str(row.get("Memo/ Description"))
            date = str(row.get("Transaction Date"))
            memo = str(row.get("Memo/ Description"))
            transaction_id = str(row.get("Transaction ID"))
            add_transaction(amt, name, date, memo, account_num, account_name, transaction_id)

def get_transactions_df():
    conn = sqlite3.connect(db_path)
    df = pd.read_sql_query("SELECT * FROM Transactions", conn)
    conn.close()
    return df

# --- Dash App ---
app = dash.Dash(__name__)

app.layout = html.Div([
    html.H1("Financial Dashboard"),
    dcc.Upload(id='upload-data', children=html.Button('Upload Excel File'), multiple=True),
    html.Div(id='upload-status'),
    dcc.Graph(id='transaction-chart'),
    html.Hr(),
    html.Div(id='table-container')
])

@app.callback(
    [Output('upload-status', 'children'),
     Output('transaction-chart', 'figure'),
     Output('table-container', 'children')],
    Input('upload-data', 'contents'),
    State('upload-data', 'filename')
)
def handle_upload(contents, filenames):
    if not contents:
        return "", {}, None

    # normalize
    if isinstance(contents, str):
        contents = [contents]
        filenames = [filenames]

    # process files
    for content, fname in zip(contents, filenames):
        try:
            _, enc = content.split(',', 1)
            data = base64.b64decode(enc)
            df_raw = pd.read_excel(io.BytesIO(data))
            df = df_raw.iloc[11:].reset_index(drop=True)
            df.columns = df.iloc[0]
            df = df[1:].reset_index(drop=True)
            df.columns.values[0] = "Account Details"
            process_sheet(df)
        except Exception as e:
            return f"Error processing {fname}: {e}", {}, None

    # load all
    df_all = get_transactions_df()
    if df_all.empty:
        return "Upload completed but no data.", {}, None

    # build pie chart
    fig = px.pie(df_all, names='name', values='amount', hole=0.4)
    fig.update_traces(textposition='inside', textinfo='percent+label')
    fig.update_layout(
        height=600,
        margin=dict(t=50, b=100, l=50, r=50),
        legend=dict(orientation='h', x=0.5, xanchor='center', y=-0.2, yanchor='bottom')
    )

    # build table
    table = dash.dash_table.DataTable(
        data=df_all.to_dict('records'),
        columns=[{'name': c, 'id': c} for c in df_all.columns],
        page_size=10,
        style_table={'overflowX': 'auto'}
    )

    return "Upload successful", fig, table

if __name__ == '__main__':
    app.run(debug=True)
