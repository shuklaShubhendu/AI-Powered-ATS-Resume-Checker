import streamlit as st
import pdfplumber
import json
import re
import os
from openai import OpenAI
from dotenv import load_dotenv
#this is sample change done for the appmod ai
# Load environment variables
load_dotenv()
client = OpenAI()

# Function to extract text from PDF using pdfplumber
def extract_text_from_pdf(uploaded_file):
    text = ""
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip() if text else "Unable to extract text."

# Function to get ATS score analysis
import json
import re
import openai


def get_ats_score(resume_text, job_desc):
    prompt = f"""
    Analyze this resume against the job description and provide:
    1. ATS score (0-100)
    2. Top 3 improvements needed
    3. Missing keywords
    4. Extra keywords to add
    
    Resume: {resume_text[:3000]}
    Job Description: {job_desc[:3000]}
    
    Return **only JSON** in the format: {{"score": int, "improvements": list, "missing_keywords": list, "keywords_to_add": list}}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.2
        )

        response_text = response.choices[0].message.content.strip()

        # Debugging: Print response
        print("🔹 OpenAI Response:", response_text)

        # Extract JSON using regex
        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            json_data = match.group(0)
            return json.loads(json_data)
        else:
            raise ValueError("No valid JSON found in OpenAI response.")

    except json.JSONDecodeError:
        print("⚠️ Error parsing OpenAI response. Please check the response format.")
        return None
    except Exception as e:
        print(f"⚠️ Unexpected error: {str(e)}")
        return None



# Function to optimize LaTeX resume
def optimize_latex(latex_code, job_desc):
    prompt = f"""
    Optimize this LaTeX resume for the following job description:
    {job_desc[:3000]}
    
    Rules:
    1. Preserve LaTeX structure
    2. Add relevant keywords naturally
    3. Improve section ordering
    4. Keep content professional
    
    Return ONLY the modified LaTeX code:
    
    {latex_code[:6000]}
    """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo",
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error optimizing LaTeX: {str(e)}")
        return None

# Streamlit UI Configuration
st.set_page_config(page_title="AI Resume Optimizer", layout="wide")

# Sidebar navigation
page = st.sidebar.radio("Navigation", ["ATS Checker", "LaTeX Optimizer"])

# ATS Checker Page
if page == "ATS Checker":
    st.title("🔍 AI-Powered ATS Resume Checker")
    
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📂 Upload Resume")
        resume_file = st.file_uploader("Choose a PDF file", type=["pdf"])
        job_desc = st.text_area("📋 Paste Job Description", height=300)
        
        if st.button("Analyze Resume"):
            if resume_file and job_desc:
                with st.spinner("Analyzing Resume..."):
                    resume_text = extract_text_from_pdf(resume_file)
                    if resume_text == "Unable to extract text.":
                        st.error("Could not extract text from the uploaded PDF.")
                    else:
                        analysis = get_ats_score(resume_text, job_desc)
                        if analysis:
                            st.session_state.analysis = analysis
            else:
                st.error("Please upload a resume and paste a job description.")

    if 'analysis' in st.session_state:
        with col2:
            st.subheader("📊 Analysis Results")
            analysis = st.session_state.analysis
            
            # ATS Score Meter
            st.metric("✅ ATS Score", f"{analysis['score']}/100")
            st.progress(analysis['score'] / 100)
            
            # Improvements Section
            st.subheader("🔧 Top Improvements")
            for imp in analysis['improvements']:
                st.markdown(f"- {imp}")
            
            # Keywords Sections
            col_key1, col_key2 = st.columns(2)
            with col_key1:
                st.subheader("❌ Missing Keywords")
                for kw in analysis['missing_keywords']:
                    st.markdown(f"- {kw}")
            
            with col_key2:
                st.subheader("✅ Keywords to Add")
                for kw in analysis['keywords_to_add']:
                    st.markdown(f"- {kw}")

# LaTeX Optimizer Page
elif page == "LaTeX Optimizer":
    st.title("📄 LaTeX Resume Optimizer")
    
    latex_code = st.text_area("✍️ Paste LaTeX Code", height=400)
    job_desc = st.text_area("📋 Paste Job Description", height=200, key="latex_jd")
    
    if st.button("🚀 Optimize with AI"):
        if latex_code and job_desc:
            with st.spinner("Optimizing Resume..."):
                optimized = optimize_latex(latex_code, job_desc)
                if optimized:
                    st.session_state.optimized = optimized
    
    if 'optimized' in st.session_state:
        st.subheader("✅ Optimized LaTeX Code")
        st.code(st.session_state.optimized, language="latex")
        
        st.download_button(
            label="💾 Download Optimized LaTeX",
            data=st.session_state.optimized,
            file_name="optimized_resume.tex",
            mime="text/plain"
        )
