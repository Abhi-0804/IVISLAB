import os
from typing import List
from fastapi import FastAPI, Request, Form, HTTPException, UploadFile, File
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse
import httpx
from pydantic import BaseModel
import json
from prompt_templates import BLOG_IDEA_PROMPT

app = FastAPI(title="Product Catalog Generator")

# Set up templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Configuration for Llama 3.2 Vision API
LLAMA_VISION_API_URL = "http://localhost:11434/api/generate"  # Update if using a different host
DEFAULT_MODEL = "llama3.2-vision-latest"

class GenerationRequest(BaseModel):
    files: List[UploadFile]
    include_specs: bool = True

@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/generate")
async def generate_ideas(
    files: List[UploadFile] = File(...),
    include_specs: bool = Form(True),
    model: str = Form(DEFAULT_MODEL)
):
    try:
        file_names = [file.filename for file in files]
        if not file_names:
            raise HTTPException(status_code=400, detail="No files uploaded.")
        
        prompt = BLOG_IDEA_PROMPT.format(
            files=", ".join(file_names),
            include_specs="with specifications" if include_specs else "without specifications",
        )
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                LLAMA_VISION_API_URL,
                json={"model": model, "prompt": prompt, "stream": False},
                timeout=60.0
            )
            
            if response.status_code != 200:
                raise HTTPException(status_code=500, detail="Failed to generate content from Llama 3.2 Vision API")
            
            result = response.json()
            generated_text = result.get("response", "")
            return {"generated_ideas": generated_text}
    
    except Exception as e:
        print(f"Error generating blog ideas: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating blog ideas: {str(e)}")

@app.get("/models")
async def get_models():
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(f"http://localhost:11434/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [model.get("name") for model in models]
                return {"models": model_names}
    except Exception as e:
        print(f"Error fetching models: {str(e)}")
    
    return {"models": [DEFAULT_MODEL]}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8008, reload=True)
