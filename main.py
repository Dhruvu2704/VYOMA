from fastapi import FastAPI

from db.database import engine, Base
from db import models

from api.tasks import router as tasks_router
from api.rule_results import router as rule_result_router
from api.permits import router as permit_router
from api.final_verdict import router as final_verdict_router
from api.audit import router as audit_router
from api.auth import router as auth_router
from api.review import router as review_router
from api.deliverables import router as deliverables_router
from api.security import router as security_router

from services.error_handler import global_exception_handler


Base.metadata.create_all(bind=engine)


app = FastAPI(
    title="VYOMA + KAVACH Backend",
    description="Backend and Security API",
    version="1.0.0"
)


app.add_exception_handler(
    Exception,
    global_exception_handler
)


app.include_router(tasks_router)
app.include_router(rule_result_router)
app.include_router(permit_router)
app.include_router(final_verdict_router)
app.include_router(audit_router)
app.include_router(auth_router)
app.include_router(review_router)
app.include_router(deliverables_router)
app.include_router(security_router)


@app.get("/")
def root():
    return {
        "message": "VYOMA + KAVACH Backend is running"
    }