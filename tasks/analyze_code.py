from crewai import Task
from agents.analyzer_agent import code_analyzer


def create_analyze_task(agent, code_text: str, feedback: str = None, 
                       previous_summary: str = None, iteration: int = 1, repo_url: str = None):
    """Create a task for analyzing code and generating documentation."""
    context = """You are an expert technical writer and software engineer. 
    Your task is to create comprehensive documentation for the provided code.
    
    IMPORTANT RULES:
    1. DO NOT include the complete code in the documentation
    2. Only include small, relevant code snippets when absolutely necessary
    3. Focus on explaining concepts, architecture, and usage, not the code itself
    4. Never include a 'Changes Made' section in the final output
    
    """
    
    # Add repository URL to the context if provided
    if repo_url:
        context += f"\n## Repository Information\nRepository URL: {repo_url}\n\n"
        context += "IMPORTANT: When creating installation instructions, use the EXACT repository URL provided above.\n\n"
    
    context += "## Documentation Structure (MUST INCLUDE ALL SECTIONS BELOW)\n"
    context += "1. **Project Title** - Clear, descriptive title with badges (version, license, build status)\n"
    context += "2. **📋 Description** - What the project does and why it's useful\n"
    context += "3. **✨ Features** - Key features and functionality\n"
    context += "4. **📂 Tech Stack** - Technologies and tools used\n"
    context += "5. **🚀 Getting Started** - Prerequisites and installation\n"
    context += "6. **🛠️ Usage** - How to use with examples\n"
    context += "7. **🔧 Configuration** - Environment variables and configuration options\n"
    context += "8. **🌐 API Endpoints** - If applicable, document available endpoints\n"
    context += "9. **🧪 Testing** - How to run tests\n"
    context += "10. **🤝 Contributing** - Guidelines for contributors\n"
    context += "11. **📄 License** - License information\n"
    context += "12. **🔗 Related** - Related projects or resources\n"
    context += "13. **📝 Changelog** - Version history (if applicable)\n\n"
    
    if previous_summary:
        context += "## Previous Documentation Version\n"
        context += f"{previous_summary}\n\n"
        
        if feedback:
            context += "## Feedback to Address\n"
            # Process feedback to remove any code blocks
            feedback = '\n'.join(line for line in feedback.split('\n') 
                               if not line.strip().startswith('```'))
            
            feedback_items = [f.strip() for f in feedback.split('\n\n') if f.strip()]
            
            context += "Please address the following feedback points in your documentation. "
            context += "IMPORTANT: Do not list these feedback items in your final output. "
            context += "Instead, incorporate the improvements directly into the documentation.\n\n"
            
            for i, item in enumerate(feedback_items, 1):
                # Remove any code blocks from feedback items
                item = '\n'.join(line for line in item.split('\n') 
                               if not line.strip().startswith('```'))
                context += f"### Feedback Item {i}\n"
                context += f"{item}\n\n"
    
    context += "## API Documentation Guidelines\n"
    context += "If the project includes API endpoints, document them like this:\n"
    context += "### Endpoint: `/api/items/{item_id}`\n"
    context += "- **Method**: `GET`\n"
    context += "- **Description**: Retrieve a specific item by ID\n"
    context += "- **Parameters**:\n"
    context += "  - `item_id` (required): The ID of the item to retrieve\n"
    context += "- **Response**: `200 OK` with item data\n\n"
    
    context += "## Output Instructions\n"
    context += "1. Create clean, professional documentation in markdown format\n"
    context += "2. Follow the structure outlined above exactly\n"
    context += "3. Include all sections even if some are brief\n"
    context += "4. Use emojis in section headers for better readability\n"
    context += "5. Include code examples where helpful, but keep them concise\n"
    context += "6. Never include a 'Changes Made' section\n"
    context += "7. Focus on the user's perspective - what they need to know to use the project\n"
    context += "8. Keep explanations clear and concise\n"
    context += "9. Use proper markdown formatting with headers, lists, and code blocks where appropriate\n\n"
    
    context += "## License Section Example\n"
    context += "```markdown\n"
    context += "## 📄 License\n"
    context += "This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.\n\n"
    context += "## 🔗 Related\n"
    context += "- [LangChain](https://www.langchain.com/)\n"
    context += "- [Related Project](https://example.com)\n"
    context += "```\n\n"
    context += "## Installation Section Guidelines\n"
    context += "When creating the installation instructions, use the EXACT repository URL.\n"
    context += "For example, if the repository URL is 'https://github.com/example/repo.git', the clone command should be:\n"
    context += "```bash\ngit clone https://github.com/example/repo.git\n```\n\n"
    
    if repo_url:
        context += f"For this documentation, the clone command should be:\n"
        context += f"```bash\ngit clone {repo_url}\n```\n\n"
    
    return Task(
        description=context,
        expected_output="""A clean, well-structured markdown document that:
        1. Provides comprehensive documentation without including the actual code
        2. Addresses all feedback from previous iterations
        3. Is written for the end-user, not developers
        4. Does not include any 'Changes Made' section
        5. Uses proper markdown formatting""",
        agent=code_analyzer
    )
