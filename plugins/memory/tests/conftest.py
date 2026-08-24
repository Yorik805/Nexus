from __future__ import annotations

import logging


def pytest_configure(config):
    config.option.log_cli = True
    config.option.log_cli_level = "INFO"
    config.option.log_cli_format = "%(asctime)s [%(levelname)s] %(message)s"
