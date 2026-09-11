from fastapi import FastAPI

from db.database import engine, Base
from db import models
from api.tasks import router as tasks_router
from api.rule_results import router as rule_result_router
from api.permits import router as permit_router
from api.final_verdict import router as final_verdict_router
from api.audit import router as audit_router
from api.auth import router as auth_router
from api.zero_egress import router as zero_egress_router
from services.error_handler import internal_error_handler

Base.metadata.create_all(bind=engine)

app = FastAPI(
    title="VYOMA + KAVACH Backend",
    description="Backend and Security API",
    version="1.0.0"
)
app.add_exception_handler(
    Exception,
    internal_error_handler
)

app.include_router(tasks_router)
app.include_router(rule_result_router)
app.include_router(permit_router)
app.include_router(final_verdict_router)
app.include_router(audit_router)
app.include_router(auth_router)
app.include_router(zero_egress_router)


@app.get("/")
def root():
    return {
        "message": "VYOMA + KAVACH Backend is running"
    }