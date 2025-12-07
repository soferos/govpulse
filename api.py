from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import uvicorn
from backend import get_agent_executor, redact_pii
from datetime import datetime

app = FastAPI(
    title="GovPulse API",
    description="Enterprise AI Interface for Scottish Government Data",
    version="1.0.0"
)

agent_executor = get_agent_executor()

class QueryRequest(BaseModel):
    query: str
    user_id: str = "anonymous"

class AgentResponse(BaseModel):
    original_query: str
    redacted_query: str
    response: str
    status: str

class FeedbackRequest(BaseModel):
    query: str
    response: str
    rating: str
    timestamp: str = str(datetime.now())

@app.post("/ask", response_model=AgentResponse)
async def ask_agent(request: QueryRequest):
    clean_query = redact_pii(request.query)
    try:
        result = agent_executor.invoke({"input": clean_query})
        return AgentResponse(
            original_query=request.query,
            redacted_query=clean_query,
            response=result["output"],
            status="success"
        )
    except Exception as e:
        print(f"API Error: {e}")
        raise HTTPException(status_code=500, detail="Internal Server Error")

@app.post("/feedback")
async def log_feedback(feedback: FeedbackRequest):
    try:
        log_entry = f"{feedback.timestamp},{feedback.rating},\"{feedback.query}\"\n"
        with open("feedback_log.csv", "a") as f:
            f.write(log_entry)
        return {"status": "logged"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    uvicorn.run("api:app", host="0.0.0.0", port=8000, reload=True)
