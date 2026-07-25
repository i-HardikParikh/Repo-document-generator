import streamlit as st
import os
import json
import yaml
import base64
from pathlib import Path
from typing import Optional, Dict, Any
import requests
from datetime import datetime
import getpass
import tempfile
import markdown
import io

# Set page config
st.set_page_config(
    page_title="Documentation Assistant",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS for better styling
st.markdown("""
    <style>
    .main {
        max-width: 1200px;
        padding: 2rem;
    }
    .stButton>button {
        background-color: #4CAF50;
        color: white;
        padding: 0.5rem 1rem;
        border: none;
        border-radius: 4px;
        cursor: pointer;
    }
    .stButton>button:hover {
        background-color: #45a049;
    }
    .stTextInput>div>div>input {
        padding: 0.5rem;
    }
    .success-msg {
        color: #4CAF50;
        font-weight: bold;
    }
    .error-msg {
        color: #f44336;
        font-weight: bold;
    }
    </style>
""", unsafe_allow_html=True)

def get_credentials() -> Dict[str, str]:
    """Get repository credentials from environment variables or user input."""
    creds = {}
    
    if st.session_state.get('use_creds', False):
        creds['username'] = st.session_state.get('username', '')
        creds['password'] = st.session_state.get('password', '')
        creds['token'] = st.session_state.get('token', '')
    return creds

def validate_repo_url(url: str) -> bool:
    """Validate repository URL format."""
    if not url:
        return False
        
    # Basic URL validation
    if not (url.startswith('http://') or url.startswith('https://')):
        return False
        
    # Check for common git hosting domains
    valid_domains = ['github.com', 'bitbucket.org', 'gitlab.com']
    return any(domain in url for domain in valid_domains)

def clean_repo_url(url: str) -> str:
    """Clean repository URL to ensure it's in the correct format."""
    # Remove query parameters and fragments
    url = url.split('?')[0].split('#')[0]
    
    # Remove trailing slashes
    url = url.rstrip('/')
    
    # For Bitbucket URLs, ensure we're using the correct format
    if 'bitbucket.org' in url and '/src/' in url:
        url = url.replace('/src/', '/')
        
    return url

def main():
    st.title("🔍 Documentation Assistant")
    st.markdown("Upload a GitHub/Bitbucket repository URL to get a comprehensive code review and documentation.")
    
    # Show example URLs
    with st.expander("📝 Example Repository URLs"):
        st.markdown("""
        **GitHub Examples:**
        - https://github.com/username/repo
        - https://github.com/tensorflow/tensorflow
        
        **Bitbucket Examples:**
        - https://bitbucket.org/username/repo
        - https://bitbucket.org/atlassian/python-bitbucket
        
        **Note:** For Bitbucket repositories, make sure to use the main repository URL, not a specific branch or file URL.
        """)
    
    # Authentication section
    with st.expander("🔑 Repository Authentication (for private repos)"):
        use_creds = st.checkbox("Use authentication", key='use_creds')
        
        if use_creds:
            auth_method = st.radio(
                "Authentication Method",
                ["Username/Password", "Personal Access Token"],
                horizontal=True
            )
            
            if auth_method == "Username/Password":
                st.session_state['username'] = st.text_input("Username")
                st.session_state['password'] = st.text_input("Password", type="password")
                st.session_state['token'] = ""
            else:
                st.session_state['token'] = st.text_input("Personal Access Token", type="password")
                st.session_state['username'] = ""
                st.session_state['password'] = ""
    
    with st.form("repo_form"):
        col1, col2 = st.columns([3, 1])
        
        with col1:
            repo_url = st.text_input(
                "Repository URL",
                placeholder="https://github.com/username/repo or https://bitbucket.org/workspace/repo"
            )
        
        with col2:
            branch = st.text_input("Branch (optional)", placeholder="main")
        
        output_format = st.selectbox(
            "Output Format",
            ["Markdown", "HTML", "JSON", "YAML", "PDF"],
            index=0
        )
        
        submit_button = st.form_submit_button("Analyze Repository")
    
    if submit_button:
        if not repo_url:
            st.error("Please enter a repository URL")
            return
            
        if not validate_repo_url(repo_url):
            st.error("Invalid repository URL. Please enter a valid GitHub, Bitbucket, or GitLab URL.")
            return
            
        # Clean the URL
        cleaned_url = clean_repo_url(repo_url)
        if cleaned_url != repo_url:
            st.info(f"URL cleaned for better compatibility: {cleaned_url}")
            repo_url = cleaned_url
            
        with st.spinner("Analyzing repository. This may take a few minutes..."):
            try:
                # Prepare the request data
                request_data = {
                    "bitbucket_url": repo_url,
                    "branch": branch if branch else None,
                    "format": output_format.lower()
                }
                
                # Add authentication if provided
                creds = get_credentials()
                if st.session_state.get('use_creds', False):
                    if creds.get('token'):
                        request_data['token'] = creds['token']
                    elif creds.get('username') and creds.get('password'):
                        request_data['username'] = creds['username']
                        request_data['password'] = creds['password']
                
                # Call the FastAPI endpoint
                response = requests.post(
                    "http://localhost:8000/review/",
                    json=request_data
                )
                
                if response.status_code == 200:
                    st.success("Analysis completed successfully!")
                    
                    # Display the results in a content window with appropriate format
                    content_type = response.headers.get('content-type', '')
                    
                    # Create a container for the content with some styling
                    st.markdown("""
                    <style>
                    .content-container {
                        border: 1px solid #e0e0e0;
                        border-radius: 5px;
                        padding: 20px;
                        margin: 10px 0;
                        background-color: #f9f9f9;
                        max-height: 600px;
                        overflow-y: auto;
                    }
                    </style>
                    """, unsafe_allow_html=True)
                    
                    st.markdown("<h3>Document Preview</h3>", unsafe_allow_html=True)
                    
                    content_container = st.container()
                    
                    with content_container:
                        if output_format.lower() == 'json':
                            # Display JSON in a formatted way
                            try:
                                json_data = response.json()
                                st.json(json_data)
                            except Exception:
                                st.text(response.text)  # Fallback to text if JSON parsing fails
                                
                        elif output_format.lower() == 'yaml':
                            # Display YAML in a code block
                            st.code(response.text, language="yaml")
                            
                        elif output_format.lower() == 'html':
                            # Display HTML content directly
                            st.components.v1.html(response.text, height=600, scrolling=True)
                            
                        elif output_format.lower() == 'pdf':
                            # For PDF, create an embedded PDF viewer
                            # First save the PDF content to a temporary file
                            with tempfile.NamedTemporaryFile(delete=False, suffix='.pdf') as tmp_file:
                                tmp_file.write(response.content)
                                pdf_path = tmp_file.name
                            
                            # Create an iframe to display the PDF
                            pdf_display = f'''
                            <iframe src="data:application/pdf;base64,{base64.b64encode(response.content).decode('utf-8')}" 
                                width="100%" height="600" type="application/pdf" frameborder="0" 
                                style="border: 1px solid #ddd; border-radius: 5px;">
                            </iframe>
                            '''
                            st.markdown(pdf_display, unsafe_allow_html=True)
                            
                        else:  # Markdown is the default
                            # Display markdown with proper rendering
                            st.markdown(response.text)
                    
                    # Add download button
                    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                    filename = f"code_review_{timestamp}.{output_format.lower()}"
                    
                    # Create a styled pink download button
                    if output_format.lower() == 'html':
                        b64 = base64.b64encode(response.content).decode()
                        mime_type = 'file/html'
                        content = response.content
                    elif output_format.lower() == 'pdf':
                        b64 = base64.b64encode(response.content).decode()
                        mime_type = 'application/pdf'
                        content = response.content
                    else:
                        b64 = base64.b64encode(response.text.encode()).decode()
                        mime_type = 'text/plain'
                        content = response.text.encode()
                    
                    # Create a styled pink download button using HTML/CSS
                    download_button_str = f'''
                    <a href="data:{mime_type};base64,{b64}" download="{filename}">
                        <button style="
                            background-color: #FF69B4; 
                            color: white; 
                            padding: 10px 20px; 
                            border: none; 
                            border-radius: 4px; 
                            cursor: pointer; 
                            font-weight: bold; 
                            margin: 10px 0px;
                            display: inline-block;
                            text-decoration: none;
                            box-shadow: 0px 2px 5px rgba(0,0,0,0.2);
                            transition: all 0.3s ease;
                        ">
                            📥 Download {output_format.upper()} Report
                        </button>
                    </a>
                    '''
                    
                    st.markdown(download_button_str, unsafe_allow_html=True)
                    
                else:
                    error_msg = response.text
                    st.error(f"Error analyzing repository: {error_msg}")
                    
                    # Provide helpful suggestions based on common errors
                    if "not found" in error_msg.lower() or "404" in error_msg:
                        st.warning("Repository not found. Please check if the URL is correct and the repository exists.")
                    elif "permission denied" in error_msg.lower() or "unauthorized" in error_msg.lower() or "authentication" in error_msg.lower():
                        st.warning("Authentication failed. Make sure you've provided correct credentials for private repositories.")
                    elif "timeout" in error_msg.lower():
                        st.warning("Request timed out. The repository might be too large or the server is busy.")
            
            except requests.exceptions.ConnectionError:
                st.error("Connection error. Make sure the FastAPI server is running at http://localhost:8000")
                st.info("Start the server with: uvicorn main:app --reload")
            except Exception as e:
                st.error(f"An error occurred: {str(e)}")
    
    # Add some information about the tool
    st.markdown("---")
    st.markdown("### About")
    st.markdown("""
    This tool analyzes your codebase and generates comprehensive documentation including:
    - Code structure and architecture
    - Function and class documentation
    - Usage examples
    - Quality assurance checks
    
    Simply provide a public repository URL and let the AI do the rest!
    """)

if __name__ == "__main__":
    main()