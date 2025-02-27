import streamlit as st
import pdfplumber
import json
import re
import os
from openai import OpenAI
from dotenv import load_dotenv
import subprocess
import tempfile

# Load environment variables
load_dotenv()
client = OpenAI()

# --- Helper Functions ---
def extract_text_from_pdf(uploaded_file):
    text = ""
    with pdfplumber.open(uploaded_file) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                text += page_text + "\n"
    return text.strip() if text else "Unable to extract text."

def get_ats_score(resume_text, job_desc):
    prompt = f"""
    Analyze this resume against the job description and provide:
    1. ATS score (0-100)
    2. Top 3 improvements needed
    3. Missing keywords
    4. Keywords to add

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

        match = re.search(r'\{.*\}', response_text, re.DOTALL)
        if match:
            json_data = match.group(0)
            return json.loads(json_data)
        else:
            raise ValueError("No valid JSON found in OpenAI response.")

    except json.JSONDecodeError:
        print("⚠️ Error parsing OpenAI response. JSONDecodeError.")
        return None
    except Exception as e:
        print(f"⚠️ Unexpected error in get_ats_score: {str(e)}")
        return None

def optimize_latex(latex_code, job_desc):
    prompt = f"""
    Optimize this LaTeX resume for the following job description:
    {job_desc[:3000]}

    Rules:
   Instructions:
    1. **ATS and Impact Focus:** Optimize the resume for Applicant Tracking Systems (ATS) and to highlight impact and achievements relevant to the job description.
    2. **Keyword Integration:**  Incorporate keywords from the job description naturally throughout the resume, especially in the summary, skills, experience, and projects sections.
    3. **Quantify Achievements:**  Rewrite bullet points in the Experience and Projects sections to be more results-oriented and quantify achievements with numbers or metrics wherever possible.
    4. **Action Verbs and Impactful Language:** Use strong action verbs and impactful language to describe responsibilities and accomplishments.
    5.  **Section Reordering (If Necessary):** If reordering sections would make the resume more impactful for this specific job description (e.g., prioritizing Projects or Technical Skills over Experience), suggest a reordering. Otherwise, maintain the original section order.
    6.  **LaTeX Structure Preservation:**  Maintain the original LaTeX structure and formatting as much as possible.
    7.  **Professional Tone:** Ensure all changes maintain a professional and concise tone.

    return the full modified latex code as it is professonal grade app so give only latex code but remeber to give full and in same structure

    {latex_code}
    """

    try:
        response = client.chat.completions.create(
            model="gpt-4-turbo", # or gpt-4o
            messages=[{"role": "user", "content": prompt}],
            temperature=0.3
        )
        return response.choices[0].message.content
    except Exception as e:
        st.error(f"Error optimizing LaTeX: {str(e)}")
        return None

def compile_latex_to_pdf(latex_code):
    try:
        with tempfile.NamedTemporaryFile(suffix='.tex', delete=False) as tmp_tex_file:
            tex_filename = tmp_tex_file.name
            tmp_tex_file.write(latex_code.encode('utf-8'))

        with tempfile.TemporaryDirectory() as tmp_dir:
            subprocess.run(['pdflatex', '-output-directory', tmp_dir, tex_filename], check=True, capture_output=True)
            pdf_filename = os.path.join(tmp_dir, os.path.splitext(os.path.basename(tex_filename))[0] + '.pdf')
            with open(pdf_filename, 'rb') as pdf_file:
                pdf_bytes = pdf_file.read()
        return pdf_bytes
    except subprocess.CalledProcessError as e:
        st.error(f"LaTeX compilation failed! Please ensure your LaTeX code is valid. Error details: {e.stderr.decode()}")
        return None
    except FileNotFoundError:
        st.error("pdflatex command not found. Please ensure LaTeX is installed and pdflatex is in your system's PATH.")
        return None
    except Exception as e:
        st.error(f"Error compiling LaTeX to PDF: {str(e)}")
        return None
    finally:
        if 'tex_filename' in locals(): # avoid unbound local var error
            os.remove(tex_filename) # Clean up .tex file


# --- Streamlit UI ---
st.set_page_config(page_title="AI Resume Optimizer", layout="wide")

st.sidebar.title("Navigation")
page = st.sidebar.radio("", ["ATS Checker", "LaTeX Optimizer", "Resume Templates", "About"])

# --- ATS Checker Page ---
if page == "ATS Checker":
    st.title("ATS Resume Checker")
    st.header("Optimize Your Resume for Applicant Tracking Systems")
    st.write("Upload your resume and paste the job description to see how well your resume matches the job requirements.")

    col1, col2 = st.columns(2)

    with col1:
        st.subheader("Upload Resume (PDF)")
        resume_file = st.file_uploader("Choose a PDF file", type=["pdf"])
        job_desc = st.text_area("Paste Job Description", height=300)

        if st.button("Analyze"):
            if resume_file and job_desc:
                with st.spinner("Analyzing..."):
                    resume_text = extract_text_from_pdf(resume_file)
                    if resume_text == "Unable to extract text.":
                        st.error("Text extraction failed. Ensure PDF is text-based.")
                    else:
                        analysis = get_ats_score(resume_text, job_desc)
                        if analysis:
                            st.session_state.analysis = analysis
            else:
                st.warning("Please upload resume and job description.")

    if 'analysis' in st.session_state:
        with col2:
            st.subheader("Analysis Results")
            analysis = st.session_state.analysis

            st.metric("ATS Score", f"{analysis['score']}/100", delta=analysis['score'] - 70 if analysis['score'] else -70) # Example delta
            st.progress(analysis['score'] / 100 if analysis['score'] else 0)

            st.info("💡 Aim for a score of 70 or higher for optimal ATS compatibility.")

            st.subheader("Top Improvements")
            if analysis['improvements']:
                for imp in analysis['improvements']:
                    st.markdown(f"- 🛠️ {imp}")
            else:
                st.success("✅ No major improvements suggested by AI.")

            col_keywords1, col_keywords2 = st.columns(2)
            with col_keywords1:
                st.subheader("Missing Keywords")
                if analysis['missing_keywords']:
                    for kw in analysis['missing_keywords']:
                        st.markdown(f"- ❌ {kw}")
                else:
                    st.success("✅ No missing keywords detected.")

            with col_keywords2:
                st.subheader("Keywords to Add")
                if analysis['keywords_to_add']:
                    for kw in analysis['keywords_to_add']:
                        st.markdown(f"- ✅ {kw}")
                else:
                    st.success("✅ No extra keywords suggested.")


# --- LaTeX Optimizer Page ---
elif page == "LaTeX Optimizer":
    st.title("LaTeX Resume Optimizer")
    st.header("Optimize Your LaTeX Resume with AI")
    st.write("Paste your LaTeX code and the job description to optimize your resume. You can edit and download the optimized LaTeX and compile to PDF.")

    latex_code = st.text_area("Paste LaTeX Code", height=400)
    job_desc = st.text_area("Paste Job Description", height=200, key="latex_jd_optimizer")

    if st.button("Optimize"):
        if latex_code and job_desc:
            with st.spinner("Optimizing LaTeX..."):
                optimized_latex = optimize_latex(latex_code, job_desc)
                if optimized_latex:
                    st.session_state.optimized_latex = optimized_latex # Use different session state key

    if 'optimized_latex' in st.session_state:
        st.subheader("Optimized LaTeX Code (Editable)")
        edited_latex_code = st.text_area("Edit Optimized LaTeX", st.session_state.optimized_latex, height=400)

        col_download_latex, col_download_pdf = st.columns(2)
        with col_download_latex:
            st.download_button(
                label="Download LaTeX (.tex)",
                data=edited_latex_code,
                file_name="optimized_resume.tex",
                mime="text/plain"
            )
        with col_download_pdf:
            if st.button("Download as PDF"):
                with st.spinner("Compiling PDF..."):
                    pdf_bytes = compile_latex_to_pdf(edited_latex_code)
                    if pdf_bytes:
                        st.download_button(
                            label="Download PDF",
                            data=pdf_bytes,
                            file_name="optimized_resume.pdf",
                            mime="application/pdf"
                        )

# --- Resume Templates Page ---
elif page == "Resume Templates":
    st.title("Resume Templates")
    st.header("Choose a Template to Start Building Your Resume")
    st.write("Select a template and customize it to create a professional resume.")

    templates = {
        "Template 1 (Modern)": "template1.tex", # Placeholder filenames - replace with actual template files or URLs
        "Template 2 (Classic)": "template2.tex",
        "Template 3 (Creative)": "template3.tex",
        # Add more templates as needed
    }

    selected_template = st.selectbox("Select a Template", list(templates.keys()))

    st.info("Templates are placeholders. In a future version, you'll be able to load and edit actual templates.")
    st.write(f"You selected: **{selected_template}**. (Template preview/download will be implemented in a future update.)")


# --- About Page ---
elif page == "About":
    st.title("About AI Resume Optimizer")
    st.write("This app helps you optimize your resume using AI. It offers two main features:")
    st.subheader("ATS Checker")
    st.write("Analyzes your resume against a job description to provide an ATS score, identify areas for improvement, and suggest relevant keywords.")
    st.subheader("LaTeX Optimizer")
    st.write("Optimizes your LaTeX resume by incorporating keywords from the job description and improving its structure for ATS and readability.")
    st.write("This app is powered by OpenAI's GPT models and Streamlit.")
    st.markdown("[GitHub Repository (Coming Soon)](#)") # Replace with your actual repo link
    st.write("Created with ❤️ for job seekers.")

# --- Footer ---
