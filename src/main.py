import uvicorn
from fastapi import FastAPI

from routes import movie_router


app = FastAPI(
    title="Online Cinema",
    description="A digital platform that allows users to select, watch, and "
    "purchase access to movies and other video materials via the internet.",
)

api_version_prefix = "/api/v1"

app.include_router(movie_router, prefix=f"{api_version_prefix}/cinema", tags=["cinema"])


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
