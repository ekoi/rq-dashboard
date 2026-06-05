import os
import sys
import time
from importlib import import_module
from pathlib import Path

try:
  from src.utils.commons import app_settings
except ModuleNotFoundError:
  from utils.commons import app_settings


def long_task(x, y):
  time.sleep(5)
  return x + y


def _ensure_harvester_on_path():
  """Make an optional harvester package importable for HAL harvest jobs."""
  harvester_src = os.getenv(
    "HARVESTER_SRC",
    app_settings.get("HARVESTER_SRC") if app_settings else None,
  )
  if not harvester_src:
    raise RuntimeError(
      "HARVESTER_SRC is not configured. Set it in conf/settings.toml or as an environment variable."
    )
  src_path = str(Path(harvester_src).resolve())
  if src_path not in sys.path:
    sys.path.insert(0, src_path)


def _load_hal_harvester():
  """Load the HAL harvesting entrypoint if the optional package is available."""
  _ensure_harvester_on_path()
  try:
    module = import_module("toolmeta_harvester.flows.harvest_hal_apps")
  except ModuleNotFoundError as exc:
    raise ModuleNotFoundError(
      "Optional dependency 'toolmeta_harvester' is not available. "
      "Set HARVESTER_SRC to the harvester project's src directory or install the package."
    ) from exc
  try:
    return module.harvest_hal_using_postgres_backend
  except AttributeError as exc:
    raise AttributeError(
      "Module 'toolmeta_harvester.flows.harvest_hal_apps' does not expose "
      "'harvest_hal_using_postgres_backend'."
    ) from exc


def run_hal_harvest():
  """RQ job entrypoint to execute HAL harvest + DB save."""
  harvest_hal_using_postgres_backend = _load_hal_harvester()
  return harvest_hal_using_postgres_backend()
