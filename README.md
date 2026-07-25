# Documentation Assistant (Repo-document-generator)

An automated tool designed to generate clean, structured, and QA-reviewed technical documentation for codebase repositories (GitHub, GitLab, and Bitbucket) using a collaborative multi-agent AI system.

The application features a responsive **Streamlit Web UI** frontend and a high-performance **FastAPI Backend Router** orchestration engine running **CrewAI** agents.

---

## 🔍 Features
- **Iterative AI Review Loop**: A writer agent (`code_analyzer`) drafts technical documentation, which is then vetted by a reviewer agent (`qa_agent`) over multiple iterations (up to 3 cycles) to ensure completeness.
- **Failover Redundancy**: Automatically falls back to a local Ollama server running `llama3` if OpenAI API calls encounter credentials or rate-limiting errors.
- **VCS Integration**: Seamlessly clones, pulls, and checks out branches for public and private repositories (GitHub, GitLab, and Bitbucket) using secure `GIT_ASKPASS` credential injection.
- **Multi-Format Document Exporters**: Generates and compiles deliverables in Markdown (`.md`), HTML (`.html`), JSON (`.json`), YAML (`.yaml`), and print-ready PDF (`.pdf`) formats.
- **Inline Document Previewer**: Live, formatted previews (including embedded PDF frame rendering) directly on the Streamlit dashboard prior to download.

---

## 🛠️ Tech Stack
- **Backend API**: FastAPI (0.115.9), Uvicorn (0.34.2)
- **Frontend Dashboard**: Streamlit (1.x)
- **AI Agent Framework**: CrewAI (0.121.0), LangChain (0.3.25)
- **Model Services**: OpenAI (`gpt-4o-mini`), Ollama (`llama3` local failover)
- **Git client integration**: GitPython (3.1.44)
- **Exporters**: ReportLab (4.4.1), PyPDF2 (3.0.1), python-markdown (3.8), PyYAML (6.0.2)

---

## 🚀 Getting Started

### Prerequisites
Before running the application, make sure you have:
1. **Python 3.8** or higher installed.
2. **Git CLI** installed and added to your system environment variables.
3. (Optional) **Ollama** running locally on port `11434` with the `llama3` model downloaded (`ollama pull llama3`) for local failover support.

### Setup and Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/i-HardikParikh/Repo-document-generator.git
   cd Repo-document-generator
   ```

2. **Create and activate a virtual environment**
   ```bash
   # On Windows (Command Prompt / PowerShell)
   python -m venv venv
   .\venv\Scripts\activate

   # On macOS / Linux
   python3 -m venv venv
   source venv/bin/activate
   ```

3. **Install project dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure Environment Variables**
   Create a `.env` file in the root directory:
   ```ini
   OPENAI_API_KEY=your-openai-api-key-here
   ```

---

## 💻 Running the Application

To run the full application, start both the FastAPI backend server and the Streamlit frontend dashboard:

### 1. Start the FastAPI Backend
```bash
uvicorn main:app --reload --port 8000
```
- The backend API server will be available at `http://localhost:8000`.
- Access the interactive API docs (Swagger UI) at `http://localhost:8000/docs`.

### 2. Start the Streamlit Frontend
In a separate terminal window (with the virtual environment activated):
```bash
streamlit run app.py
```
- The frontend dashboard will open automatically in your default browser at `http://localhost:8501`.

---

## ⚙️ Configuration & Environment Variables

The application is configured using a `.env` file in the project root:

| Variable Name | Required | Default Value | Description |
|---|---|---|---|
| `OPENAI_API_KEY` | **Yes** (Cloud Mode) | N/A | The API key utilized by CrewAI and LangChain to authenticate with OpenAI model services. |
| `GIT_TERMINAL_PROMPT` | Managed by code | `0` | Inhibits Git from launching interactive prompts on credentials request. |
| `GIT_CONFIG_PARAMETERS` | Managed by code | `'credential.helper='` | Clears local Git configuration helpers. |
| `GIT_ASKPASS` | Managed by code | Path to helper | Points Git to the custom credential injection script. |

---

## 🤝 Contributing
1. Fork the repository.
2. Create a feature branch: `git checkout -b feature/your-feature-name`.
3. Commit your changes: `git commit -m 'Add your feature details'`.
4. Push to your branch: `git push origin feature/your-feature-name`.
5. Open a Pull Request.

---

## 📄 License
This project is licensed under the MIT License - see the LICENSE file for details.
