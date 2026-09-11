from db.database import SessionLocal
from db.models import AuditLog
from services.audit_logger import AuditLogger


db = SessionLocal()

logger = AuditLogger()


# =========================
# CHECK ORIGINAL CHAIN
# =========================

print("CHECKING ORIGINAL CHAIN...")

result = logger.verify_chain(db)

print("Chain valid:", result)


# =========================
# TAMPER WITH AN EVENT
# =========================

print("\nTAMPERING WITH AUDIT EVENT...")

first_event = (
    db.query(AuditLog)
    .order_by(AuditLog.id.asc())
    .first()
)

print("Original pipeline:", first_event.pipeline)

# Change the audit data
first_event.pipeline = "HACKED"

db.commit()

print("Changed pipeline to:", first_event.pipeline)


# =========================
# CHECK CHAIN AGAIN
# =========================

print("\nCHECKING CHAIN AFTER TAMPERING...")

result = logger.verify_chain(db)

print("Chain valid:", result)


# =========================
# CLOSE DATABASE
# =========================

db.close()