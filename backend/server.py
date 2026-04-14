from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
from dotenv import load_dotenv
from typing import Optional, List, Dict
import json
import uuid
from datetime import datetime
import boto3
from botocore.exceptions import ClientError
from context import prompt, session_summary_prompt
from pushover_client import send_pushover
from calendar_client import get_available_slots
from bedrock_tools import converse_with_tools

# Load environment variables
load_dotenv()

app = FastAPI()

# Configure CORS
origins = os.getenv("CORS_ORIGINS", "http://localhost:3000").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["*"],
)

# Initialize Bedrock client - see Q42 on https://edwarddonner.com/faq if the Region gives you problems
bedrock_client = boto3.client(
    service_name="bedrock-runtime", 
    region_name=os.getenv("DEFAULT_AWS_REGION", "us-east-1")
)

# Bedrock model selection - see Q42 on https://edwarddonner.com/faq for more
BEDROCK_MODEL_ID = os.getenv("BEDROCK_MODEL_ID", "openai.gpt-oss-120b-1:0")

# Memory storage configuration
USE_S3 = os.getenv("USE_S3", "false").lower() == "true"
S3_BUCKET = os.getenv("S3_BUCKET", "")
MEMORY_DIR = os.getenv("MEMORY_DIR", "../memory")

# Initialize S3 client if needed
if USE_S3:
    s3_client = boto3.client("s3")


# Request/Response models
class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    session_id: str


class SessionEndRequest(BaseModel):
    session_id: str


class Message(BaseModel):
    role: str
    content: str
    timestamp: str


# Memory management functions
def get_memory_path(session_id: str) -> str:
    return f"{session_id}.json"


def load_conversation(session_id: str) -> List[Dict]:
    """Load conversation history from storage"""
    if USE_S3:
        try:
            response = s3_client.get_object(Bucket=S3_BUCKET, Key=get_memory_path(session_id))
            return json.loads(response["Body"].read().decode("utf-8"))
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return []
            raise
    else:
        # Local file storage
        file_path = os.path.join(MEMORY_DIR, get_memory_path(session_id))
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return json.load(f)
        return []


def save_conversation(session_id: str, messages: List[Dict]):
    """Save conversation history to storage"""
    if USE_S3:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=get_memory_path(session_id),
            Body=json.dumps(messages, indent=2),
            ContentType="application/json",
        )
    else:
        # Local file storage
        os.makedirs(MEMORY_DIR, exist_ok=True)
        file_path = os.path.join(MEMORY_DIR, get_memory_path(session_id))
        with open(file_path, "w") as f:
            json.dump(messages, f, indent=2)


def get_meta_path(session_id: str) -> str:
    return f"meta/{session_id}.json"


def load_session_meta(session_id: str) -> Dict:
    if USE_S3:
        try:
            response = s3_client.get_object(Bucket=S3_BUCKET, Key=get_meta_path(session_id))
            return json.loads(response["Body"].read().decode("utf-8"))
        except ClientError as e:
            if e.response["Error"]["Code"] == "NoSuchKey":
                return {}
            raise
    else:
        file_path = os.path.join(MEMORY_DIR, get_meta_path(session_id))
        if os.path.exists(file_path):
            with open(file_path, "r") as f:
                return json.load(f)
        return {}


def save_session_meta(session_id: str, meta: Dict):
    if USE_S3:
        s3_client.put_object(
            Bucket=S3_BUCKET,
            Key=get_meta_path(session_id),
            Body=json.dumps(meta, indent=2),
            ContentType="application/json",
        )
    else:
        meta_dir = os.path.join(MEMORY_DIR, "meta")
        os.makedirs(meta_dir, exist_ok=True)
        file_path = os.path.join(MEMORY_DIR, get_meta_path(session_id))
        with open(file_path, "w") as f:
            json.dump(meta, f, indent=2)


def _first_text_block(response: dict) -> str:
    """First text block from a Converse response (no HTTPException)."""
    for block in response.get("output", {}).get("message", {}).get("content") or []:
        if isinstance(block, dict) and "text" in block:
            return block["text"]
    return ""


def summarize_conversation_for_push(conversation: List[Dict]) -> str:
    """Short bullet summary for end-of-session Pushover. Falls back to transcript clip on failure."""
    transcript = "\n".join(
        f"{msg['role'].upper()}: {msg['content']}" for msg in conversation
    )
    if not transcript.strip():
        return "(empty chat)"

    try:
        response = bedrock_client.converse(
            modelId=BEDROCK_MODEL_ID,
            system=[{"text": session_summary_prompt()}],
            messages=[
                {
                    "role": "user",
                    "content": [{"text": f"Transcript:\n\n{transcript}"}],
                }
            ],
            inferenceConfig={"maxTokens": 600, "temperature": 0.2, "topP": 0.9},
        )
        text = _first_text_block(response).strip()
        return text if text else transcript[:1200]
    except Exception as e:
        print(f"Session summary Bedrock call failed: {e}")
        return transcript[:1200]


def call_bedrock(conversation: List[Dict], user_message: str) -> str:
    """Call Bedrock with tool-capable multi-turn loop (calendar, Pushover, etc.)."""
    try:
        return converse_with_tools(
            bedrock_client,
            BEDROCK_MODEL_ID,
            prompt(),
            conversation,
            user_message,
        )
    except ClientError as e:
        error_code = e.response["Error"]["Code"]
        error_message = e.response["Error"].get("Message", str(e))
        if error_code == "ValidationException":
            print(f"Bedrock validation error: {e}")
            raise HTTPException(status_code=400, detail=error_message)
        elif error_code == "AccessDeniedException":
            print(f"Bedrock access denied: {e}")
            raise HTTPException(status_code=403, detail=error_message)
        else:
            print(f"Bedrock error: {e}")
            raise HTTPException(status_code=500, detail=error_message)


@app.get("/")
async def root():
    return {
        "message": "AI Digital Twin API (Powered by AWS Bedrock)",
        "memory_enabled": True,
        "storage": "S3" if USE_S3 else "local",
        "ai_model": BEDROCK_MODEL_ID
    }


@app.get("/health")
async def health_check():
    return {
        "status": "healthy", 
        "use_s3": USE_S3,
        "bedrock_model": BEDROCK_MODEL_ID
    }


@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    try:
        # Generate session ID if not provided
        session_id = request.session_id or str(uuid.uuid4())

        # Load conversation history
        conversation = load_conversation(session_id)

        # Call Bedrock for response
        assistant_response = call_bedrock(conversation, request.message)

        # Update conversation history
        conversation.append(
            {"role": "user", "content": request.message, "timestamp": datetime.now().isoformat()}
        )
        conversation.append(
            {
                "role": "assistant",
                "content": assistant_response,
                "timestamp": datetime.now().isoformat(),
            }
        )

        # Save conversation
        save_conversation(session_id, conversation)

        return ChatResponse(response=assistant_response, session_id=session_id)

    except HTTPException:
        raise
    except Exception as e:
        print(f"Error in chat endpoint: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/conversation/{session_id}")
async def get_conversation(session_id: str):
    """Retrieve conversation history"""
    try:
        conversation = load_conversation(session_id)
        return {"session_id": session_id, "messages": conversation}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/sessions/end")
async def end_session(request: SessionEndRequest):
    """Mark session ended; send one Pushover with a short chat summary (idempotent)."""
    session_id = request.session_id

    meta = load_session_meta(session_id)
    if meta.get("ended_at"):
        return {"status": "already_ended", "session_id": session_id}

    conversation = load_conversation(session_id)
    if not conversation:
        return {"status": "empty", "session_id": session_id}

    summary = summarize_conversation_for_push(conversation)
    body = f"Session: {session_id}\n\n{summary}"
    send_pushover(title="Career Twin: chat ended", message=body)

    meta["ended_at"] = datetime.now().isoformat()
    save_session_meta(session_id, meta)

    return {"status": "ended", "session_id": session_id}


@app.get("/availability")
async def availability():
    """Return the next available interview slots (12-3 PM ET, weekdays)."""
    slots = get_available_slots(num_slots=3)
    return {"slots": slots}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run(app, host="0.0.0.0", port=8000)