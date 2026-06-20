import pytest


def pytest_ignore_collect(path, config):
    """Ignore problematic top-level integration tests that perform import-time
    network or sys.exit calls so pytest can collect unit tests safely.
    """
    skip_names = (
        "test_comprehensive_jarvis.py",
        "test_comprehensive_*.py",
        "test_tier3_comprehensive.py",
        "test_tier3_integration.py",
        "test_e2e.py",
    )
    p = str(path).replace("\\", "/")
    for name in skip_names:
        if p.endswith(name) or ("*" in name and p.split("/")[-1].startswith(name.split("*")[0])):
            return True
    return False
