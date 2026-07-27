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


# ---------------------------------------------------------------------------
# Provider registry
# Each entry maps a short provider name (used in the API URL) to the
# dotted module path and function name inside toolmeta_harvester.
# ---------------------------------------------------------------------------
PROVIDER_REGISTRY: dict[str, tuple[str, str]] = {
    "hal":      ("toolmeta_harvester.flows.harvest_hal_apps",               "harvest_hal_using_postgres_backend"),
    "vip":      ("toolmeta_harvester.flows.harvest_vip_apps",               "harvest_vip_using_postgres_backend"),
    "biobb":    ("toolmeta_harvester.flows.harvest_biobb_workflowhub_jupyter", "pipeline_harvest_biobb_jupyter_workflows"),
    "workflowhub": ("toolmeta_harvester.flows.harvest_galaxy_hub_workflows", "pipeline_harvest_workflow_hub"),
    "usegalaxy-org": ("toolmeta_harvester.flows.harvest_usegalaxy_org",     "main"),
}


def _ensure_harvester_on_path():
    """Add the harvester src directory to sys.path if not already there."""
    harvester_src = os.getenv(
        "HARVESTER_SRC",
        app_settings.get("HARVESTER_SRC") if app_settings else None,
    )
    if not harvester_src:
        raise RuntimeError(
            "HARVESTER_SRC is not configured. "
            "Set it in conf/settings.toml or as an environment variable."
        )
    src_path = str(Path(harvester_src).resolve())
    if src_path not in sys.path:
        sys.path.insert(0, src_path)


def _load_provider_fn(provider: str):
    """Return the callable for *provider* from the registry."""
    if provider not in PROVIDER_REGISTRY:
        known = ", ".join(sorted(PROVIDER_REGISTRY))
        raise ValueError(
            f"Unknown harvest provider '{provider}'. Known providers: {known}"
        )

    _ensure_harvester_on_path()
    module_path, fn_name = PROVIDER_REGISTRY[provider]

    try:
        module = import_module(module_path)
    except ModuleNotFoundError as exc:
        raise ModuleNotFoundError(
            f"Could not import '{module_path}'. "
            "Ensure HARVESTER_SRC points to the harvester src/ directory."
        ) from exc

    try:
        return getattr(module, fn_name)
    except AttributeError as exc:
        raise AttributeError(
            f"Module '{module_path}' does not expose '{fn_name}'."
        ) from exc


def run_harvest(provider: str):
    """Generic RQ job entrypoint.  Called by the API for any provider."""
    fn = _load_provider_fn(provider)
    return fn()


# ---------------------------------------------------------------------------
# Legacy alias kept for backwards compatibility with any queued jobs.
# ---------------------------------------------------------------------------
def run_hal_harvest():
    """RQ job entrypoint to execute HAL harvest + DB save (legacy alias)."""
    return run_harvest("hal")
