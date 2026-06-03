import os
import uvicorn

from fastapi import FastAPI

try:
    from src.utils.commons import app_settings, get_project_details
except ModuleNotFoundError:
    from utils.commons import app_settings, get_project_details

try:
    from src.api.v1.task_routes import router as v1_router
except ModuleNotFoundError:
    from api.v1.task_routes import router as v1_router
APP_NAME = os.environ.get("APP_NAME", "RQ + FastAPI Service")

project_details = get_project_details(
    os.environ.get("BASE_DIR", os.getcwd()),
    ["name", "description", "version"],
)
APP_TITLE = project_details.get("name", APP_NAME)
APP_DESCRIPTION = project_details.get("description", "")
APP_VERSION = project_details.get("version", "0.0.0")


def get_expose_port() -> int:
    return int(os.environ.get("EXPOSE_PORT", "12104"))

import logging
from logging.handlers import TimedRotatingFileHandler

build_date = os.environ.get("BUILD_DATE", "unknown")
log_file = app_settings.get("log_file", "rqf.log")
os.makedirs(os.path.dirname(log_file) or ".", exist_ok=True)
handler = TimedRotatingFileHandler(
    log_file,
    when="midnight",  # rotate every second for testing
    interval=1,
    backupCount=7,
    encoding="utf-8",
    utc=True
)
handler.suffix = "%Y-%m-%d"

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s %(levelname)s %(message)s',
    handlers=[handler]
)
app = FastAPI(title=APP_TITLE, description=APP_DESCRIPTION, version=APP_VERSION)
app.include_router(v1_router)


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=get_expose_port())
