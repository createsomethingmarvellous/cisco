import streamlit as st
import pandas as pd
import plotly.express as px
import os

st.set_page_config(page_title="NetSage AI Dashboard", layout="wide")

st.title("NetSage AI - Responsible AI & Analytics Dashboard")

# Load datasets
def load_data():
    cases_df = pd.DataFrame()
    logs_df = pd.DataFrame()
    
    if os.path.exists("../data/cases.csv"):
        try:
            cases_df = pd.read_csv("../data/cases.csv")
        except:
            pass
    
    if os.path.exists("../logs/responsible_ai_log.csv"):
        try:
            logs_df = pd.read_csv("../logs/responsible_ai_log.csv")
        except:
            pass
            
    return cases_df, logs_df

cases_df, logs_df = load_data()

if cases_df.empty and logs_df.empty:
    st.warning("No data found. Ensure cases.csv and responsible_ai_log.csv exist.")
else:
    st.header("1. Dataset Overview (Module 1)")
    
    col1, col2, col3 = st.columns(3)
    num_cases = len(cases_df) if not cases_df.empty else 0
    col1.metric("Total Cases", num_cases)
    
    if not cases_df.empty:
        # Cases by Issue Type
        issue_counts = cases_df['concept_tag'].value_counts().reset_index()
        issue_counts.columns = ['Issue Type', 'Count']
        fig1 = px.pie(issue_counts, values='Count', names='Issue Type', title="Cases by Issue Type")
        
        # Cases by Severity
        severity_counts = cases_df['severity'].value_counts().reset_index()
        severity_counts.columns = ['Severity', 'Count']
        fig2 = px.bar(severity_counts, x='Severity', y='Count', title="Cases by Severity", color='Severity')
        
        c1, c2 = st.columns(2)
        c1.plotly_chart(fig1, use_container_width=True)
        c2.plotly_chart(fig2, use_container_width=True)
        
    st.divider()
    
    st.header("2. Responsible AI Logging & Human Review (Modules 6, 8, 9)")
    
    if not logs_df.empty:
        total_reviews = len(logs_df)
        accepted = len(logs_df[logs_df['human_decision'] == 'ACCEPTED'])
        edited = len(logs_df[logs_df['human_decision'] == 'EDITED'])
        rejected = len(logs_df[logs_df['human_decision'] == 'REJECTED'])
        
        accept_rate = (accepted / total_reviews) * 100 if total_reviews > 0 else 0
        edit_rate = (edited / total_reviews) * 100 if total_reviews > 0 else 0
        reject_rate = (rejected / total_reviews) * 100 if total_reviews > 0 else 0
        
        rc1, rc2, rc3, rc4 = st.columns(4)
        rc1.metric("Total Human Reviews", total_reviews)
        rc2.metric("AI Accepted Rate", f"{accept_rate:.1f}%")
        rc3.metric("AI Edited Rate", f"{edit_rate:.1f}%")
        rc4.metric("AI Rejected Rate", f"{reject_rate:.1f}%")
        
        st.subheader("Human-AI Agreement & Corrections")
        agreement = (accepted / total_reviews) * 100 if total_reviews > 0 else 0
        st.progress(int(agreement))
        st.write(f"**AI-Human Agreement Rate:** {agreement:.1f}%")
        
        st.write(f"**Number of AI Corrections Documented:** {edited + rejected}")
        
        st.subheader("Recent Human Corrections")
        corrections = logs_df[logs_df['human_decision'].isin(['EDITED', 'REJECTED'])]
        st.dataframe(corrections[['case_id', 'timestamp', 'ai_root_cause', 'human_decision', 'human_correction']], use_container_width=True)
    else:
        st.info("No human review logs available yet. Complete a review in the main portal to see metrics.")
