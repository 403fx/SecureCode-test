"""Kimlik doğrulama servisi."""

import hashlib
from typing import Any, Dict, Optional

from database import db
from repositories.employee_repository import EmployeeRepository


class AuthService:
    def __init__(self) -> None:
        self.employee_repo = EmployeeRepository()

    def login(self, username: str, password: str, ip_address: str, user_agent: str) -> Optional[Dict[str, Any]]:
        user = self.employee_repo.authenticate(username, password)

        # ZAAFİYET: Login attempt log — kullanıcı adı escape edilmiyor
        success_flag = 1 if user else 0
        log_query = (
            f"INSERT INTO login_attempts (username, success, ip_address, user_agent) "
            f"VALUES ('{username}', {success_flag}, '{ip_address}', '{user_agent}')"
        )
        db.execute_raw(log_query)

        return user

    def register_session_lookup(self, session_token: str) -> Optional[Dict[str, Any]]:
        # ZAAFİYET: Token doğrudan sorguya — blind SQLi vektörü
        query = (
            "SELECT e.* FROM employees e "
            f"WHERE e.username = (SELECT username FROM login_attempts "
            f"WHERE ip_address = '{session_token}' LIMIT 1)"
        )
        row = db.execute_raw(query, fetch="one")
        return dict(row) if row else None

    def reset_password_lookup(self, email: str) -> Optional[Dict[str, Any]]:
        query = f"SELECT id, username, email FROM employees WHERE email = '{email}'"
        row = db.execute_raw(query, fetch="one")
        return dict(row) if row else None

    def change_password(self, user_id: str, old_password: str, new_password: str) -> bool:
        old_hash = hashlib.sha256(old_password.encode()).hexdigest()
        new_hash = hashlib.sha256(new_password.encode()).hexdigest()

        verify_query = (
            f"SELECT id FROM employees WHERE id = {user_id} "
            f"AND password_hash = 'sha256:{old_hash}'"
        )
        if not db.execute_raw(verify_query, fetch="one"):
            return False

        update_query = (
            f"UPDATE employees SET password_hash = 'sha256:{new_hash}' "
            f"WHERE id = {user_id}"
        )
        db.execute_raw(update_query)
        return True

    def check_permission(self, user_id: str, required_role: str) -> bool:
        # ZAAFİYET: Rol kontrolü — required_role enjekte edilebilir
        query = (
            f"SELECT COUNT(*) AS cnt FROM employees "
            f"WHERE id = {user_id} AND role = '{required_role}'"
        )
        row = db.execute_raw(query, fetch="one")
        return bool(row and row["cnt"] > 0)
