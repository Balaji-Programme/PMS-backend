from fastapi import Request, FastAPI
from fastapi.responses import JSONResponse
from sqlalchemy.exc import SQLAlchemyError
from fastapi.exceptions import RequestValidationError
import logging
from datetime import datetime

logger = logging.getLogger("app.exceptions")

def add_exception_handlers(app: FastAPI):
    @app.exception_handler(SQLAlchemyError)
    def sqlalchemy_exception_handler(request: Request, exc: SQLAlchemyError):
        logger.exception("Database error on %s %s", request.method, request.url.path)
        headers = {
            "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
            "Access-Control-Allow-Credentials": "true",
        }
        return JSONResponse(
            status_code=500,
            content={"detail": "Internal Database Error", "type": str(type(exc).__name__)},
            headers=headers
        )

    @app.exception_handler(RequestValidationError)
    def validation_exception_handler(request: Request, exc: RequestValidationError):
        logger.warning("Validation error on %s %s: %s", request.method, request.url.path, exc.errors())
        headers = {
            "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
            "Access-Control-Allow-Credentials": "true",
        }
        return JSONResponse(
            status_code=422,
            content={"detail": "Validation Error", "errors": exc.errors()},
            headers=headers
        )

    @app.exception_handler(Exception)
    def global_exception_handler(request: Request, exc: Exception):
        logger.exception("Unhandled exception on %s %s", request.method, request.url.path)
        import traceback
        err = "".join(traceback.format_exception(type(exc), exc, exc.__traceback__))
        with open("error_log.txt", "a") as f:
            f.write(f"\n[{datetime.now()}] GLOBAL ERROR on {request.method} {request.url.path}:\n" + err + "\n")
        
        headers = {
            "Access-Control-Allow-Origin": request.headers.get("origin", "*"),
            "Access-Control-Allow-Credentials": "true",
            "Access-Control-Allow-Methods": "*",
            "Access-Control-Allow-Headers": "*",
        }
        
        return JSONResponse(
            status_code=500,
            content={"detail": "An unexpected error occurred", "type": str(type(exc).__name__), "msg": str(exc)},
            headers=headers
        )
