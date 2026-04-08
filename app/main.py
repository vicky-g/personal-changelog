from fastapi import FastAPI

from app.api.routes.entries import router as entries_router
from app.api.routes.summaries import router as summaries_router
from app.api.routes.tags import router as tags_router

app = FastAPI(
    title="Personal Changelog",
    description="Track what you did. Generate summaries.",
    version="0.1.0",
)

app.include_router(entries_router)
app.include_router(summaries_router)
app.include_router(tags_router)


@app.get("/health", tags=["meta"])
async def health() -> dict:
    return {"status": "ok"}
