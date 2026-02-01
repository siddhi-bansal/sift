"""Run stage: cluster summarization, catalysts, daily report."""

def __getattr__(name: str):
    if name == "run_report":
        from .runner import run_report
        return run_report
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")

__all__ = ["run_report"]
