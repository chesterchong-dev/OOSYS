from fastapi import FastAPI

app = FastAPI(
    title="OOSYS API",
    description="Only One System — modular enterprise platform",
    version="0.1.0",
)


@app.get("/health", tags=["Operations"])
def health_check() -> dict[str, str]:
    """Basic liveness endpoint; does not verify database readiness."""
    return {"status": "ok"}


@app.get("/", tags=["Operations"])
def root() -> dict[str, str]:
    return {"name": "OOSYS", "status": "starter"}
