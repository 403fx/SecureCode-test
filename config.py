"""Uygulama yapılandırması."""

import os

DATABASE_PATH = os.environ.get("ERP_DB_PATH", "erp_system.db")
SECRET_KEY = os.environ.get("SECRET_KEY", "dev-secret-change-me")
DEBUG = os.environ.get("DEBUG", "true").lower() == "true"
DEFAULT_PAGE_SIZE = 25
MAX_EXPORT_ROWS = 10_000
