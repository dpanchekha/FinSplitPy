import streamlit as st
import pandas as pd
import sqlite3
import io
import plotly.express as px
import re as rgx
import locale
import os
from streamlit_navigation_bar import st_navbar
import file_processor as fp

# --- Streamlit App ---
def main():
    st.set_page_config(page_title="FinSplit Dashboard", page_icon="./assets/finsplit_icon.ico", layout="wide")
    
    # Create tab-based navigation
    tab1, tab2, tab3, tab4, tab5 = st.tabs(["Home", "Library", "Tutorials", "Development", "Download"])
    
    # Home tab content
    with tab1:
        st.title("Dashboard")
        fp.init_db()

        uploaded_files = st.file_uploader(
            "Upload Excel files",
            type=["xlsx", "xls"],
            accept_multiple_files=True
        )

        if uploaded_files:
            for uploaded in uploaded_files:
                try:
                    temp_df = pd.read_excel(uploaded)
                    df = temp_df.iloc[11:].reset_index(drop=True)
                    df.columns = df.iloc[0]
                    df = df[1:].reset_index(drop=True)
                    df.columns.values[0] = "Account Details"
                    fp.process_sheet(df)
                    st.success(f"Processed {uploaded.name}")
                except Exception as e:
                    st.error(f"Error processing {uploaded.name}: {e}")

            df_all = fp.get_all_transactions_df()
            if not df_all.empty:
                fig = px.pie(df_all, names='name', values='amount', hole=0.4)
                fig.update_traces(textposition='inside', textinfo='percent+label')
                fig.update_layout(
                    height=600,
                    margin=dict(t=50, b=100, l=50, r=50),
                    legend=dict(orientation='h', yanchor='bottom', y=-0.2, xanchor='center', x=0.5)
                )
                st.plotly_chart(fig, use_container_width=True)
                st.subheader("Transaction Details")
                st.dataframe(df_all)
            else:
                st.info("No data to display yet.")

    # Library tab content
    with tab2:
        st.title("Library")
        st.info("Library page coming soon.")

    # Tutorials tab content
    with tab3:
        st.title("Tutorials")
        st.info("Tutorials page coming soon.")

    # Development tab content
    with tab4:
        st.title("Development")
        st.info("Development page coming soon.")

    # Download tab content
    with tab5:
        st.title("Download")
        st.info("Download page coming soon.")

if __name__ == '__main__':
    main()