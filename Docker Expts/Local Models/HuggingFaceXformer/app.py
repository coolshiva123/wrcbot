from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from transformers import pipeline
import torch

app = FastAPI()

class SummarizeRequest(BaseModel):
    text: str
    max_length: int = 60
    min_length: int = 10
    do_sample: bool = False

# Load model at startup
summarizer = pipeline(
    "summarization",
    model="t5-large",
    device=0 if torch.cuda.is_available() else -1
)

@app.post("/summarize")
def summarize(req: SummarizeRequest):
    if not req.text or len(req.text.strip()) == 0:
        raise HTTPException(status_code=400, detail="Text is required.")
    try:
        summary = summarizer(
            req.text,
            max_length=req.max_length,
            min_length=req.min_length,
            do_sample=req.do_sample
        )
        return {"summary": summary[0]["summary_text"]}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e)) from e
