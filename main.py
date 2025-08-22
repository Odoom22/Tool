import asyncio # Keep asyncio for type hinting if FastAPI/Uvicorn use it
import sys

# Removed explicit event loop policy setting:
# if sys.platform == "win32":
# asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import logging
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
# from engine import audit_site # Deferring import again

# Configure basic logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

logger.info("Starting application setup...")

class AuditRequest(BaseModel):
    domain: str


from contextlib import asynccontextmanager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup logic
    logger.info("Application startup event triggered.")
    yield
    # Shutdown logic
    logger.info("Application shutdown event triggered.")

app = FastAPI(title="Wɔkɔm Professional Compliance Suite", lifespan=lifespan)
logger.info("FastAPI app initialized.")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)
logger.info("CORSMiddleware added.")

@app.post("/audit")
async def run_audit_endpoint(request_data: AuditRequest, request: Request):
    logger.info(f"Received audit request for domain: {request_data.domain} from {request.client.host}")

    # Deferred import to avoid startup issues with webdriver-manager
    from engine import audit_site

    domain = request_data.domain.strip()
    if not domain:
        logger.warning("Domain is required but not provided.")
        raise HTTPException(status_code=400, detail="Domain is required.")
    try:
        logger.info(f"Calling audit_site for domain: {domain}")
        report = await audit_site(domain)
        logger.info(f"Audit_site completed for domain: {domain}")
        return report
    except Exception as e:
        logger.error(f"Audit failed for domain {domain}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Audit failed: {str(e)}")


@app.get("/health")
async def health_check_endpoint(request: Request):
    logger.info(f"Received health check request from {request.client.host}")
    return {"status": "ok"}

logger.info("Application setup complete. Routes defined.")