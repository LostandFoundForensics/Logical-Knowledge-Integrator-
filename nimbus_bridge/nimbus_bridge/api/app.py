from fastapi import FastAPI
from .routes_nimbus import router as nimbus_router
from .routes_meta import router as meta_router
from .routes_cases import router as cases_router

app = FastAPI(title="Nimbus Bridge API", version="0.2.0")
app.include_router(nimbus_router, prefix="/nimbus", tags=["nimbus"])
app.include_router(meta_router, prefix="/nimbus", tags=["nimbus-meta"])
app.include_router(cases_router, prefix="/cases", tags=["cases"])
