"""
nimbus_bridge/api/routes_cases.py

Referenced in the package tree and wired into app.py. Stub — case
management routes were never specified beyond the filename.
"""
from fastapi import APIRouter

router = APIRouter()


@router.get("/")
def list_cases():
    return {"note": "Case management routes not yet implemented."}
