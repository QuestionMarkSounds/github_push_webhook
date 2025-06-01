import os
import traceback
from fastapi import FastAPI, Request, HTTPException, Header
from fastapi.responses import JSONResponse
import hmac
import hashlib
import json
import subprocess
from typing import Optional

app = FastAPI()

# GitHub webhook secret - should be set in environment variables in production
GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
TARGET_BRANCH = os.getenv("TARGET_BRANCH")
BATCH_FILE_PATH = os.getenv("BATCH_FILE_PATH")
WEBHOOK_PORT = os.getenv("WEBHOOK_PORT")

def verify_github_signature(payload_body: bytes, signature_header: str) -> bool:
    """Verify that the webhook request came from GitHub."""    
    try:
        if not signature_header:
            raise HTTPException(
                status_code=403, detail="x-hub-signature-256 header is missing!"
            )
        hash_object = hmac.new(
            GITHUB_WEBHOOK_SECRET.encode("utf-8"), msg=payload_body, digestmod=hashlib.sha256
        )
        
        expected_signature = "sha256=" + hash_object.hexdigest()
        
        return hmac.compare_digest(signature_header, expected_signature)
    except Exception:
        return False

@app.post("/webhook")
async def github_webhook(
    request: Request,
    x_hub_signature_256: Optional[str] = Header(None),
    x_github_event: Optional[str] = Header(None)
):
    # Get the raw request body
    payload_body = await request.body()
    
    # Verify GitHub signature
    if not verify_github_signature(payload_body, x_hub_signature_256):
        raise HTTPException(status_code=401, detail="Invalid signature")
    
    # Parse the JSON payload
    try:
        payload = json.loads(payload_body)
    except json.JSONDecodeError:
        raise HTTPException(status_code=400, detail="Invalid JSON payload")
    
    # Process different GitHub events
    if x_github_event == "push":
        # Handle push event
        if payload.get("ref", "").split("/")[-1] == TARGET_BRANCH:
            try:
                # Run the batch file
                os.system(f"/usr/bin/sudo -u ubuntu /usr/bin/bash {BATCH_FILE_PATH} > upgrade.log")
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"Error running batch file: {str(e)}")

        return JSONResponse({
            "message": "Push event received",
            "repository": payload.get("repository", {}).get("name"),
            "branch": payload.get("ref", "").split("/")[-1]
        })
    elif x_github_event == "pull_request":
        # Handle pull request event
        return JSONResponse({
            "message": "Pull request event received",
            "action": payload.get("action"),
            "pr_number": payload.get("number")
        })
    else:
        # Handle other events
        return JSONResponse({
            "message": f"Received {x_github_event} event",
            "event_type": x_github_event
        })

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=WEBHOOK_PORT)
