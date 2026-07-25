import os
import git
import shutil
from pathlib import Path
from typing import Optional
from datetime import datetime
import re
from urllib.parse import urlparse

def get_project_root() -> Path:
    """Get the project root directory (trial_git folder)."""
    # Go up two levels from utils/ to reach the project root
    return Path(__file__).parent.parent.resolve()

def extract_git_url(input_str: str) -> str:
    """Extract git URL from a git clone command or return as is."""
    input_str = input_str.strip()
    if input_str.startswith('git clone '):
        # Remove 'git clone ' and any extra spaces, then split by space and get last part
        return input_str.replace('git clone', '').strip().split()[-1]
    return input_str

def get_repo_name_from_url(url: str) -> str:
    """Extract repository name from URL."""
    # Remove .git if present
    if url.endswith('.git'):
        url = url[:-4]
    # Get the last part of the URL
    return url.split('/')[-1]

def clone_repo(url: str, base_folder: str = "cloned_repo", branch: str = None, 
               username: Optional[str] = None, password: Optional[str] = None, 
               token: Optional[str] = None) -> str:
    """
    Clone or update a git repository into a unique subfolder.
    
    Args:
        url: The URL or git clone command of the git repository
        base_folder: The base folder where repositories will be stored
        branch: The branch to clone/checkout (default: None for default branch)
        username: Optional username for authentication
        password: Optional password for authentication
        token: Optional personal access token for authentication
        
    Returns:
        str: Absolute path to the cloned/updated repository
    """
    try:
        # Extract URL if it's a git clone command
        clean_url = extract_git_url(url)
        
        # Get repository name from URL
        repo_name = get_repo_name_from_url(clean_url)
        if not repo_name:
            repo_name = f"repo_{int(datetime.now().timestamp())}"
             
        # Create base directory if it doesn't exist
        project_root = get_project_root()
        print(f"Project root: {project_root}")
        
        base_dir = project_root / base_folder
        print(f"Base directory: {base_dir}")
        
        # Ensure base directory exists
        base_dir.mkdir(parents=True, exist_ok=True)
        print(f"Base directory exists: {base_dir.exists()}")
        
        # Create repo-specific directory
        repo_dir = base_dir / repo_name
        print(f"Repository will be cloned to: {repo_dir}")
        
        print(f"Cloning/updating repository to: {repo_dir}")
        print(f"Using repository URL: {clean_url}")
        if branch:
            print(f"Using branch: {branch}")
        
        # Set up secure authentication env variables
        env_vars = os.environ.copy()
        env_vars["GIT_TERMINAL_PROMPT"] = "0"
        env_vars["GIT_CONFIG_PARAMETERS"] = "'credential.helper='"
        
        utils_dir = Path(__file__).parent
        if os.name == 'nt':
            askpass_path = utils_dir / "git_askpass.bat"
        else:
            askpass_path = utils_dir / "git_askpass.py"
            
        if askpass_path.exists() and (token or username or password):
            env_vars["GIT_ASKPASS"] = str(askpass_path.resolve())
            if token:
                env_vars["GIT_ASKPASS_TOKEN"] = token
            elif password:
                env_vars["GIT_ASKPASS_TOKEN"] = password
            if username:
                env_vars["GIT_ASKPASS_USERNAME"] = username

        # If the directory exists and is a git repo, try to pull updates
        if repo_dir.exists() and (repo_dir / ".git").exists():
            try:
                repo = git.Repo(repo_dir)
                # If branch is specified, fetch and checkout
                if branch:
                    print(f"Fetching all branches...")
                    repo.git.fetch(env=env_vars)
                    print(f"Checking out branch: {branch}")
                    repo.git.checkout(branch)
                # Pull the latest changes
                print("Pulling latest changes...")
                repo.git.pull(env=env_vars)
                print(f"Successfully updated repository")
                return str(repo_dir)
            except git.exc.GitCommandError as e:
                print(f"Error pulling repository: {e}. Attempting fresh clone...")
                shutil.rmtree(repo_dir, ignore_errors=True)
        
        # If we get here, either the directory doesn't exist or we need a fresh clone
        print(f"Cloning repository...")
        # Clone the repository using safe credentials environment
        repo = git.Repo.clone_from(clean_url, repo_dir, env=env_vars)
        
        # If branch is specified, checkout that branch
        if branch:
            print(f"Checking out branch: {branch}")
            repo.git.checkout(branch)
            
        print(f"Successfully cloned repository")
        print(f"Current branch: {repo.active_branch}")
        return str(repo_dir)
        
    except Exception as e:
        print(f"Error during repository cloning: {str(e)}")
        if 'repo_dir' in locals():
            print(f"Repository directory was: {repo_dir}")
            print(f"Directory exists: {repo_dir.exists() if 'repo_dir' in locals() else 'N/A'}")
        # Clean up in case of error
        if 'repo_dir' in locals() and repo_dir.exists():
            shutil.rmtree(repo_dir, ignore_errors=True)
        raise Exception(f"Failed to clone/update repository: {str(e)}")

def generate_output_filename(repo_url: str) -> str:
    """Generate a valid filename from repository URL."""
    try:
        # Parse the URL to get the path
        parsed = urlparse(repo_url)
        # Get the path component and remove leading/trailing slashes
        path = parsed.path.strip('/')
        # Remove .git if present
        if path.endswith('.git'):
            path = path[:-4]
        # Replace special characters with underscores
        clean_name = re.sub(r'[^\w\-_.]', '_', path)
        # Add timestamp
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        # Combine into filename
        return f"review_{timestamp}_{clean_name[:50]}.md"
    except Exception as e:
        # Fallback if URL parsing fails
        return f"review_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"

def save_to_markdown(content: str, repo_url: str = "") -> str:
    """
    Save content to a markdown file in the output directory.
    
    Args:
        content: The content to save
        repo_url: The repository URL (used for generating filename)
        
    Returns:
        str: Path to the saved file
    """
    try:
        # Ensure output directory exists
        output_dir = Path("output")
        output_dir.mkdir(exist_ok=True, parents=True)
        
        # Generate a valid filename
        if repo_url:
            # Extract repo name from URL
            repo_name = re.sub(r'[^\w\-_.]', '_', repo_url.split('/')[-1])
            if repo_name.endswith('.git'):
                repo_name = repo_name[:-4]
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"summary_{timestamp}_{repo_name[:50]}.md"
        else:
            filename = f"summary_{datetime.now().strftime('%Y%m%d_%H%M%S')}.md"
            
        filepath = output_dir / filename
        
        # Write content
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
            
        return str(filepath.absolute())
        
    except Exception as e:
        raise Exception(f"Failed to save markdown file: {str(e)}")

def extract_code_snippets(folder: str) -> str:
    """
    Extract code snippets from files in a directory.
    
    Args:
        folder: The directory to search for code files
        
    Returns:
        str: Concatenated code snippets with file paths
    """
    code_summary = ""
    try:
        for root, _, files in os.walk(folder):
            # Skip .git directory
            if ".git" in root.split(os.path.sep):
                continue
                
            for file in files:
                if file.endswith(('.py', '.js', '.ts', '.java', '.go', '.cpp', '.h', '.hpp', '.c')):
                    path = os.path.join(root, file)
                    try:
                        with open(path, 'r', encoding='utf-8', errors='ignore') as f:
                            code = f.read()
                            code_summary += f"\n### File: {os.path.relpath(path, folder)}\n```{os.path.splitext(file)[1][1:]}\n{code}\n```\n"
                    except Exception as e:
                        print(f"Error reading file {path}: {str(e)}")
                        continue
        return code_summary
    except Exception as e:
        raise Exception(f"Error extracting code snippets: {str(e)}")
