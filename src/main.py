import uvicorn
from fastapi import FastAPI
from config.rate_limiter import RateLimitMiddleware, RateLimitExceeded, rate_limit_exceeded_handler, limiter
from slowapi.middleware import SlowAPIMiddleware
from routes import (
    movie_router,
    accounts_router,
    payments_router,
    order_router,
    carts_router,
    profiles_router,
)


app = FastAPI(
    title="Online Cinema",
    description="A digital platform that allows users to select, watch, and "
    "purchase access to movies and other video materials via the internet.",
)

api_version_prefix = "/api/v1"

app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_middleware(RateLimitMiddleware)
app.add_exception_handler(RateLimitExceeded, rate_limit_exceeded_handler)


app.include_router(accounts_router, prefix=f"{api_version_prefix}/accounts", tags=["accounts"])
app.include_router(profiles_router, prefix=f"{api_version_prefix}/profiles", tags=["profiles"])
app.include_router(movie_router, prefix=f"{api_version_prefix}/cinema", tags=["cinema"])
app.include_router(order_router, prefix=f"{api_version_prefix}/orders", tags=["orders"])
app.include_router(carts_router, prefix=f"{api_version_prefix}/carts", tags=["carts"])
app.include_router(payments_router, prefix=f"{api_version_prefix}/payments", tags=["payments"])


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=8000, reload=True)
