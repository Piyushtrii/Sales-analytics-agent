# app.py - COMPLETE DEPLOYMENT READY VERSION
import streamlit as st
import pandas as pd
import plotly.express as px
from groq import Groq
import os

# Streamlit Cloud optimized API key handling
@st.cache_resource
def get_groq_client():
    API_KEY = (
        os.getenv("GROQ_API_KEY") or 
        st.secrets.get("GROQ_API_KEY")
    )
    if not API_KEY:
        st.error("❌ GROQ_API_KEY not found in Streamlit secrets")
        st.stop()
    return Groq(api_key=API_KEY)

st.set_page_config(
    page_title="AI Sales Analytics",
    page_icon="🚀",
    layout="wide"
)

@st.cache_data
def load_data():
    """Load and preprocess all CSV files"""
    accounts = pd.read_csv("accounts.csv")
    opportunities = pd.read_csv("opportunities.csv")
    contacts = pd.read_csv("contacts.csv")
    tasks = pd.read_csv("tasks.csv")
    
    # Standardize accounts
    accounts = accounts.rename(columns={"ID": "account_id", "NAME": "account_name"})
    
    # Standardize opportunities
    opportunities = opportunities.rename(columns={
        "ID": "opportunity_id", "ACCOUNT_ID": "account_id", "AMOUNT": "amount",
        "PROBABILITY": "probability", "STAGE_NAME": "stage", "CLOSE_DATE": "close_date"
    })
    opportunities["close_date"] = pd.to_datetime(opportunities["close_date"])
    opportunities = opportunities.merge(accounts[["account_id", "account_name"]], on="account_id", how="left")
    
    # Standardize contacts
    contacts = contacts.rename(columns={
        "ID": "contact_id", "ACCOUNT_ID": "account_id", "NAME": "contact_name", "EMAIL": "email"
    })
    contacts = contacts.merge(accounts[["account_id", "account_name"]], on="account_id", how="left")
    
    # Standardize tasks
    if "ACCOUNT_ID" in tasks.columns:
        tasks = tasks.rename(columns={"ACCOUNT_ID": "account_id"})
    if "ACTIVITY_DATE" in tasks.columns:
        tasks["activity_date"] = pd.to_datetime(tasks["ACTIVITY_DATE"])
    if "account_id" in tasks.columns:
        tasks = tasks.merge(accounts[["account_id", "account_name"]], on="account_id", how="left")
    
    return accounts, contacts, opportunities, tasks

# Load data
accounts_df, contacts_df, opps_df, tasks_df = load_data()
client = get_groq_client()

def ask_ai(prompt: str) -> str:
    """Query Groq AI with error handling"""
    try:
        response = client.chat.completions.create(
            model="openai/gpt-oss-120b",  
            messages=[{"role": "user", "content": prompt}],
            temperature=0.4,
            max_tokens=1000
        )
        return response.choices[0].message.content
    except Exception as e:
        return f"AI Error: {str(e)}"

# Header
st.markdown("""
#AI Sales Analytics
""")

# Tabs
tabs = st.tabs(["📊 Dashboard", "🤖 AI Assistant", "🤝 Meeting Prep", "📧 Outreach Generator"])

with tabs[0]:
    # Calculate metrics (avoid modifying cached data)
    weighted_df = opps_df.copy()
    weighted_df["weighted_amount"] = weighted_df["amount"] * (weighted_df["probability"] / 100)
    
    col1, col2, col3 = st.columns(3)
    col1.metric("Total Pipeline", f"€{opps_df['amount'].sum():,.0f}")
    col2.metric("Weighted Pipeline", f"€{weighted_df['weighted_amount'].sum():,.0f}")
    col3.metric("Active Deals", len(opps_df))
    
    # Stage chart
    stage_summary = opps_df.groupby("stage")["amount"].sum().reset_index()
    st.plotly_chart(
        px.bar(stage_summary, x="stage", y="amount", 
               title="Pipeline by Stage", color="amount", 
               color_continuous_scale="bluered"),
        use_container_width=True
    )
    
    if st.button("🤖 Generate AI Insights", use_container_width=True):
        with st.spinner("Generating insights..."):
            insight = ask_ai(f"""
            Analyze this sales pipeline data and provide 3 actionable insights:
            {stage_summary.to_string(index=False)}
            Focus on opportunities, risks, and next actions.
            """)
        st.success(insight)

with tabs[1]:
    question = st.text_input("💭 Ask a question about sales activity", 
                           placeholder="e.g., Which accounts have the highest pipeline?")
    
    if st.button("Ask AI", use_container_width=True) and question:
        with st.spinner("AI thinking..."):
            context = opps_df[['account_name', 'stage', 'amount', 'probability']].head(20)
            response = ask_ai(f"""
            Sales Data (top 20 opportunities):
            {context.to_string(index=False)}
            
            Question: {question}
            
            Answer concisely with specific numbers and recommendations.
            """)
        st.markdown(response)

with tabs[2]:
    account = st.selectbox("Select Account", 
                          sorted(opps_df["account_name"].dropna().unique()))
    
    if st.button("Generate Meeting Brief", use_container_width=True):
        with st.spinner("Preparing brief..."):
            account_opps = opps_df[opps_df.account_name == account]
            account_contacts = contacts_df[contacts_df.account_name == account]
            
            prompt = f"""
            MEETING BRIEF for {account}

            Opportunities:
            {account_opps[['stage', 'amount', 'probability', 'close_date']].to_string(index=False)}

            Contacts:
            {account_contacts[['contact_name', 'email']].to_string(index=False) if not account_contacts.empty else "No contacts"}

            Provide:
            1. Account status summary
            2. Key talking points
            3. Next action recommendations
            """
            st.markdown("### 📋 Meeting Brief")
            st.markdown(ask_ai(prompt))

with tabs[3]:
    account = st.selectbox("Account", sorted(contacts_df["account_name"].dropna().unique()))
    contact_df = contacts_df[contacts_df["account_name"] == account]
    
    contact = st.selectbox(
        "Contact", 
        contact_df["contact_name"].tolist() if not contact_df.empty else ["No Contacts"]
    )
    
    tone = st.selectbox("Tone", ["Professional", "Friendly", "Executive"])
    purpose = st.text_area("Email Purpose", 
                          placeholder="e.g., Schedule discovery call, Follow up on proposal")
    
    if st.button("✉️ Generate Email", use_container_width=True) and purpose:
        with st.spinner("Crafting email..."):
            email = ask_ai(f"""
            Write a {tone.lower()} sales email to {contact} at {account}.
            Purpose: {purpose}
            Structure: Subject line + Greeting + Body + Call-to-action + Sign-off
            Keep under 150 words. Conversational tone.
            From: Your Name, Sales Manager at Your Company
            """)
            st.text_area("Generated Email", email, height=300, key="email_output")



