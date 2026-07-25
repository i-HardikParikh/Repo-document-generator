from fastapi import FastAPI
from router import reviewer
from dotenv import load_dotenv
import os

load_dotenv()

# Now the OPENAI_API_KEY will be picked up by langchain or OpenAI API

app = FastAPI(
    title="Documentation Assistant",
    description="Upload a Bitbucket repo URL and get a QA-reviewed code summary.",
    version="1.0"
)

app.include_router(reviewer.router)
