# tasks/qa_check.py
from crewai import Task
from agents.qa_agent import qa_agent

def create_qa_task(agent, summary: str, previous_summary: str = None, 
                  changes: str = None, feedback_history: list = None,
                  original_code_context: str = ""):
    """Create a QA task with full context."""
    context = "## Documentation Review\n\n"
    
    # Add changes from previous version if available
    if changes:
        context += f"### Changes Made in This Iteration:\n{changes}\n\n"
    
    # Add feedback history if available
    if feedback_history:
        context += "### Feedback History:\n"
        for i, fb in enumerate(feedback_history, 1):
            context += f"#### Iteration {i} Feedback:\n{fb}\n\n"
    
    # Add the current documentation
    context += f"## Current Documentation:\n{summary}\n\n"
    
    # Review guidelines
    context += """
    **Review Guidelines:**
    1. **For Beginners:**
       - Is the purpose clear and explained simply?
       - Are there clear setup instructions?
       - Are basic usage examples provided?
       - Is technical jargon explained?

    2. **For Developers:**
       - Is the technical architecture explained?
       - Are key components and their interactions documented?
       - Are there examples of common tasks?
       - Is the API reference complete and accurate?

    3. **Overall Quality:**
       - Is the documentation well-organized?
       - Are there any inconsistencies or inaccuracies?
       - Is the tone professional yet approachable?

    **Your Response:**
    1. Start with "### Feedback" and provide specific, actionable feedback.
    2. For each issue:
       - The exact section that needs improvement
       - Clear description of what's missing or incorrect
       - Specific suggestions for improvement
       - Priority level (High/Medium/Low)
    3. If the documentation is perfect:
       - A brief summary of why it meets all criteria
       - Confirmation that no improvements are needed
    4. End with "### Status" followed by either "APPROVED" or "NEEDS_REVISION"
    """
    
    return Task(
        description=context,
        expected_output="Structured feedback on the documentation quality with an APPROVED or NEEDS_REVISION status",
        agent=qa_agent
    )