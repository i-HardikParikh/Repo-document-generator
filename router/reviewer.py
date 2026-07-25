from fastapi import APIRouter, HTTPException, Query
from fastapi.responses import FileResponse, Response
from typing import Dict, Any, Optional, List
import os
import json
import yaml
from datetime import datetime
from pathlib import Path
from difflib import unified_diff
import markdown
from markdown.extensions.toc import TocExtension
import shutil
import logging
import uuid
from agents.analyzer_agent import code_analyzer
from agents.qa_agent import qa_agent
from utils.repo_utils import clone_repo, extract_code_snippets
from tasks.analyze_code import create_analyze_task
from tasks.qa_check import create_qa_task
from crewai import Crew
from utils.formatters import DocumentFormatter, get_formatter, get_content_type, get_file_extension

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

router = APIRouter()
MAX_ITERATIONS = 3

def get_documentation_changes(old_doc, new_doc) -> str:
    """Generate a human-readable summary of changes between document versions."""
    old_doc_str = str(old_doc) if old_doc is not None else ""
    new_doc_str = str(new_doc) if new_doc is not None else ""
    
    old_lines = old_doc_str.splitlines(keepends=True)
    new_lines = new_doc_str.splitlines(keepends=True)
    
    diff = list(unified_diff(
        old_lines, 
        new_lines,
        fromfile='previous_version',
        tofile='current_version',
        n=3
    ))
    
    if not diff:
        return "No significant changes detected."
    
    return "Changes from previous version:\n```diff\n" + "".join(diff[3:]) + "\n```"

def extract_feedback(qa_result_str: str) -> str:
    """Extract feedback from QA result string."""
    if not qa_result_str:
        return "The documentation needs improvement. Please review and enhance the content."
    
    feedback_markers = ["### Feedback", "## Feedback", "# Feedback", "Feedback:"]
    for marker in feedback_markers:
        if marker in qa_result_str:
            feedback_part = qa_result_str.split(marker, 1)[1]
            if "### Status" in feedback_part:
                feedback_part = feedback_part.split("### Status")[0]
            return feedback_part.strip()
    
    lines = [line.strip() for line in qa_result_str.split('\n') if line.strip()]
    if lines and len(lines) > 1:
        return '\n'.join(lines[:-1])
    return "The documentation needs improvement. Please review and enhance the content."

def analyze_codebase(repo_path: str) -> str:
    """Extract and analyze code from the repository."""
    try:
        code_snippets = extract_code_snippets(repo_path)
        if not code_snippets:
            raise ValueError("No code snippets could be extracted from the repository")
        return code_snippets
    except Exception as e:
        raise Exception(f"Failed to analyze codebase: {str(e)}")

def generate_review_summary(final_summary: str, repo_url: str, branch: str = None) -> str:
    """Generate a formatted markdown summary of the review."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    branch_info = f"**Branch:** {branch}\n" if branch else ""
    
    return f"""# Code Review Summary

**Repository:** {repo_url}  
**Review Date:** {timestamp}  
{branch_info}**Review ID:** {str(uuid.uuid4())[:8]}

## Review Results

{final_summary}

---
"""

# Import formatters from utils.formatters instead of defining them here
from utils.formatters import DocumentFormatter, get_formatter, get_content_type, get_file_extension
from pydantic import BaseModel, Field

class ReviewRequest(BaseModel):
    repository_url: str = Field(..., alias="bitbucket_url")
    branch: Optional[str] = None
    format: str = "md"
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None

    class Config:
        populate_by_name = True

@router.post("/review/")
async def review_repo(request: ReviewRequest) -> Response:
    """
    Review a repository by cloning it and running analysis and QA tasks.
    Supports multiple output formats: markdown (default), html, json, yaml, and pdf.
    """
    bitbucket_url = request.repository_url
    branch = request.branch
    format = request.format

    # Reset agents to standard LLM for each review run
    from crewai import LLM
    ai_model = os.getenv("AI_MODEL", "gpt-4o-mini")
    code_analyzer.llm = LLM(model=ai_model)
    qa_agent.llm = LLM(model=ai_model)
    code_analyzer._using_fallback = False
    qa_agent._using_fallback = False

    # Initialize tracking variables
    documentation_versions = []
    changes_history = []
    feedback_history = []
    qa_result = None
    iteration = 0
    
    try:
        # Create timestamp for this execution
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        execution_folder = f"summary_{timestamp}_langgraph"
        base_output_dir = Path("output") / execution_folder
        base_output_dir.mkdir(parents=True, exist_ok=True)
        
        # Clone the repository with authentication
        repo_path = clone_repo(
            bitbucket_url, 
            branch=branch,
            username=request.username,
            password=request.password,
            token=request.token
        )
        
        # Analyze the codebase
        code_context = analyze_codebase(repo_path)
        
        summary = None
        feedback = None
        
        while iteration < MAX_ITERATIONS:
            iteration += 1
            logger.info(f"\n{'='*50}\nIteration {iteration} of {MAX_ITERATIONS}\n{'='*50}")
            
            try:
                # Create and run analysis task
                logger.info("\nGenerating documentation...")
                analyze_task = create_analyze_task(
                    agent=code_analyzer,
                    code_text=code_context[:15000],
                    feedback=feedback,
                    previous_summary=summary,
                    iteration=iteration,
                    repo_url=bitbucket_url  # Pass the actual repository URL
                )
                
                # Run analysis
                crew = Crew(agents=[code_analyzer], tasks=[analyze_task])
                new_summary = crew.kickoff()
                
                # Save the current summary for debugging
                summary_path = base_output_dir / f"iteration_{iteration}_summary.md"
                with open(summary_path, "w", encoding="utf-8") as f:
                    f.write(f"# Iteration {iteration} Summary\n\n{new_summary}")
                
                logger.info(f"\n📝 Saved summary to: {summary_path}")
                
                # Track documentation versions
                if new_summary:
                    documentation_versions.append({
                        'iteration': iteration,
                        'content': new_summary,
                        'timestamp': datetime.now().isoformat()
                    })
                    
                    # Calculate changes from previous version
                    changes = ""
                    if len(documentation_versions) > 1:
                        changes = get_documentation_changes(
                            documentation_versions[-2]['content'],
                            documentation_versions[-1]['content']
                        )
                        changes_history.append(changes)
                
                summary = new_summary
                
                logger.info("\nRunning QA check...")
                # Create and run QA task with full context
                qa_task = create_qa_task(
                    agent=qa_agent,
                    summary=summary,
                    previous_summary=documentation_versions[-2]['content'] if len(documentation_versions) > 1 else None,
                    changes=changes if 'changes' in locals() else None,
                    feedback_history=feedback_history,
                    original_code_context=code_context[:2000]
                )
                
                crew = Crew(agents=[qa_agent], tasks=[qa_task])
                qa_result = crew.kickoff()
                qa_result_str = str(qa_result)
                
                # Save QA result for debugging
                qa_path = base_output_dir / f"iteration_{iteration}_qa.md"
                with open(qa_path, "w", encoding="utf-8") as f:
                    f.write(f"# Iteration {iteration} QA\n\n{qa_result_str}")
                
                logger.info(f"📝 Saved QA feedback to: {qa_path}")

                # Check if documentation is approved
                if "### Status\nAPPROVED" in qa_result_str:
                    logger.info("\n✅ Documentation approved by QA!")
                    break

                # Extract feedback for next iteration
                if "### Feedback" in qa_result_str:
                    feedback = qa_result_str.split("### Feedback")[1].split("### Status")[0].strip()
                    feedback_history.append(feedback)
                    logger.info("\n📝 Feedback received for improvement:")
                    logger.info(feedback)
                else:
                    feedback = "The documentation needs improvement. Please review and enhance the content."
                    logger.info("\n⚠️ No specific feedback found, using generic feedback.")
                
                if iteration == MAX_ITERATIONS:
                    logger.warning(f"\n⚠️ Reached maximum iterations ({MAX_ITERATIONS}) without approval")
                    break
                    
            except Exception as e:
                error_msg = str(e).lower()
                is_llm_error = any(term in error_msg for term in ["openai", "authentication", "api_key", "apikey", "rate_limit", "connection", "litellm"])
                
                if is_llm_error and not getattr(code_analyzer, "_using_fallback", False):
                    logger.warning(f"\n⚠️ OpenAI API call failed: {str(e)}")
                    logger.warning("Attempting fallback to local Ollama (llama3)...")
                    from crewai import LLM
                    fallback_model = os.getenv("FALLBACK_MODEL", "ollama/llama3")
                    ollama_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
                    fallback_llm = LLM(model=fallback_model, base_url=ollama_base_url)
                    
                    # Switch agents to Ollama
                    code_analyzer.llm = fallback_llm
                    qa_agent.llm = fallback_llm
                    
                    code_analyzer._using_fallback = True
                    qa_agent._using_fallback = True
                    
                    # Decrement iteration to retry the same iteration with Ollama
                    iteration -= 1
                    logger.info("Retrying current iteration with Ollama...")
                    continue
                else:
                    logger.error(f"\n❌ Error during iteration {iteration}: {str(e)}")
                    if iteration == MAX_ITERATIONS:
                        logger.warning(f"⚠️ Reached maximum iterations ({MAX_ITERATIONS}) with errors")
                    else:
                        logger.info("Retrying with next iteration...")
                    continue
        
        # Generate final documentation
        final_summary = generate_review_summary(
            summary or "No documentation was generated.",
            bitbucket_url,
            branch
        )
        
        # Save final documentation in the execution folder
        final_doc_path = base_output_dir / "final_documentation.md"
        with open(final_doc_path, "w", encoding="utf-8") as f:
            f.write(final_summary)
            
        # Create a README for the execution
        readme_path = base_output_dir / "README.md"
        with open(readme_path, "w", encoding="utf-8") as f:
            f.write(f"# Documentation Generation - {execution_folder}\n\n")
            f.write(f"- **Repository**: {bitbucket_url}\n")
            f.write(f"- **Branch**: {branch or 'main'}\n")
            f.write(f"- **Generated on**: {datetime.now().isoformat()}\n")
            f.write(f"- **Total iterations**: {iteration}\n")
            f.write("\n## Files in this directory\n")
            f.write("- `iteration_X_summary.md`: Documentation from each iteration\n")
            f.write("- `iteration_X_qa.md`: QA feedback for each iteration\n")
            f.write("- `final_documentation.md`: Final approved documentation\n")
            f.write("- `execution_info.txt`: Details about this execution\n")
            
        logger.info(f"\n✅ All files saved to: {base_output_dir}")
        logger.info(f"📄 Final documentation: {final_doc_path}")
        logger.info(f"📋 Execution details: {readme_path}")

        # Prepare the documentation data for formatting
        documentation_data = {
            "content": final_summary,
            "metadata": {
                "repository": bitbucket_url,
                "branch": branch or "main",
                "generated_at": datetime.utcnow().isoformat(),
                "iterations": iteration,
                "status": "completed" if qa_result and "### Status\nAPPROVED" in str(qa_result) else "max_iterations_reached",
                "feedback_history": feedback_history
            }
        }

        try:
            # Get the appropriate formatter and format the content
            formatter_func = get_formatter(format)
            formatted_content = formatter_func(documentation_data)
            content_type = get_content_type(format)
            file_extension = get_file_extension(format)
        except ValueError as e:
            # Handle format-related errors with a 400 status code
            raise HTTPException(
                status_code=400,
                detail=str(e)
            ) from e
        
        # Generate a filename with the correct extension
        filename = f"documentation_{timestamp}.{file_extension}"
        filepath = base_output_dir / filename
        
        # Handle binary content for PDF
        if format == 'pdf':
            with open(filepath, 'wb') as f:
                f.write(formatted_content)
        else:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(formatted_content)
        
        # Update README with the new format
        with open(readme_path, 'a', encoding='utf-8') as f:
            f.write(f"- `{filename}`: Documentation in {format.upper()} format\n")

        # Return the formatted response
        return Response(
            content=formatted_content,
            media_type=content_type,
            headers={
                "Content-Disposition": f"attachment; filename={filename}",
                "X-Repository": bitbucket_url,
                "X-Branch": branch or "main",
                "X-Format": format
            }
        )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in review_repo: {str(e)}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"Error generating documentation: {str(e)}"
        )