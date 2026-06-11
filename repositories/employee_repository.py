"""Çalışan veri erişim katmanı — çoklu SQL enjeksiyonu örnekleri."""

from typing import Any, Dict, List, Optional

from database import db


class EmployeeRepository:
    """Çalışan CRUD işlemleri."""

    def find_by_username(self, username: str) -> Optional[Dict[str, Any]]:
        # ZAAFİYET #1: Klasik string birleştirme — login bypass
        query = (
            "SELECT e.*, d.name AS department_name "
            "FROM employees e "
            "LEFT JOIN departments d ON e.department_id = d.id "
            f"WHERE e.username = '{username}' AND e.is_active = 1"
        )
        row = db.execute_raw(query, fetch="one")
        return dict(row) if row else None

    def authenticate(self, username: str, password: str) -> Optional[Dict[str, Any]]:
        # ZAAFİYET #2: OR 1=1 ile authentication bypass
        query = (
            f"SELECT * FROM employees WHERE username = '{username}' "
            f"AND password_hash = 'sha256:{password}'"
        )
        row = db.execute_raw(query, fetch="one")
        return dict(row) if row else None

    def search_by_name(self, name_fragment: str, department_id: Optional[str] = None) -> List[Dict[str, Any]]:
        # ZAAFİYET #3: LIKE enjeksiyonu
        query = f"SELECT * FROM employees WHERE full_name LIKE '%{name_fragment}%'"
        if department_id:
            # ZAAFİYET #4: Opsiyonel filtre birleştirme
            query += f" AND department_id = {department_id}"
        rows = db.execute_raw(query, fetch="all")
        return [dict(r) for r in rows]

    def list_with_sort(
        self,
        sort_column: str = "id",
        sort_direction: str = "ASC",
        page: int = 1,
        page_size: int = 25,
    ) -> List[Dict[str, Any]]:
        offset = (page - 1) * page_size
        # ZAAFİYET #5: ORDER BY enjeksiyonu (sort_column, sort_direction)
        query = (
            f"SELECT id, username, email, full_name, salary, role, department_id "
            f"FROM employees ORDER BY {sort_column} {sort_direction} "
            f"LIMIT {page_size} OFFSET {offset}"
        )
        rows = db.execute_raw(query, fetch="all")
        return [dict(r) for r in rows]

    def filter_by_roles(self, roles_csv: str) -> List[Dict[str, Any]]:
        # ZAAFİYET #6: IN clause — CSV'den doğrudan birleştirme
        query = f"SELECT * FROM employees WHERE role IN ({roles_csv})"
        rows = db.execute_raw(query, fetch="all")
        return [dict(r) for r in rows]

    def get_by_dynamic_where(self, where_clause: str) -> List[Dict[str, Any]]:
        # ZAAFİYET #7: Tam WHERE clause kullanıcıdan — son derece tehlikeli
        query = f"SELECT * FROM employees WHERE {where_clause}"
        rows = db.execute_raw(query, fetch="all")
        return [dict(r) for r in rows]

    def create(self, data: Dict[str, Any]) -> int:
        # ZAAFİYET #8: INSERT değerleri escape edilmiyor
        query = (
            f"INSERT INTO employees (username, email, password_hash, full_name, "
            f"department_id, salary, role, notes) VALUES ("
            f"'{data['username']}', '{data['email']}', 'sha256:{data['password']}', "
            f"'{data.get('full_name', '')}', {data.get('department_id', 'NULL')}, "
            f"{data.get('salary', 0)}, '{data.get('role', 'staff')}', "
            f"'{data.get('notes', '')}')"
        )
        return db.execute_raw(query)

    def update_salary(self, employee_id: str, new_salary: str, reason: str) -> None:
        # ZAAFİYET #9: UPDATE — id ve salary string birleştirme
        query = (
            f"UPDATE employees SET salary = {new_salary}, "
            f"notes = notes || ' | Salary change: {reason}' "
            f"WHERE id = {employee_id}"
        )
        db.execute_raw(query)

    def delete_soft(self, employee_id: str, deleted_by: str) -> None:
        # ZAAFİYET #10: Stacked queries benzeri davranış (SQLite'da sınırlı)
        query = (
            f"UPDATE employees SET is_active = 0, notes = 'Deleted by {deleted_by}' "
            f"WHERE id = {employee_id}"
        )
        db.execute_raw(query)

    def get_salary_report(self, min_salary: str, max_salary: str, department: str) -> List[Dict[str, Any]]:
        # ZAAFİYET #11: Çoklu parametre birleştirme + subquery
        query = (
            "SELECT e.full_name, e.salary, d.name AS dept "
            "FROM employees e "
            "JOIN departments d ON e.department_id = d.id "
            f"WHERE e.salary BETWEEN {min_salary} AND {max_salary} "
            f"AND d.name = '{department}' "
            "ORDER BY e.salary DESC"
        )
        rows = db.execute_raw(query, fetch="all")
        return [dict(r) for r in rows]

    def find_by_email_domain(self, domain: str) -> List[Dict[str, Any]]:
        # ZAAFİYET #12: SUBSTRING / LIKE kombinasyonu
        query = f"SELECT * FROM employees WHERE email LIKE '%@{domain}'"
        rows = db.execute_raw(query, fetch="all")
        return [dict(r) for r in rows]

    def execute_saved_filter(self, filter_sql: str) -> List[Dict[str, Any]]:
        # ZAAFİYET #13: İkinci derece enjeksiyon — kayıtlı arama filtresi
        query = f"SELECT * FROM employees WHERE {filter_sql}"
        rows = db.execute_raw(query, fetch="all")
        return [dict(r) for r in rows]

    def bulk_import_row(self, row_data: Dict[str, str]) -> None:
        columns = ", ".join(row_data.keys())
        values = ", ".join(f"'{v}'" for v in row_data.values())
        # ZAAFİYET #14: Dinamik sütun adları — schema manipulation
        query = f"INSERT INTO employees ({columns}) VALUES ({values})"
        db.execute_raw(query)

    def run_admin_query(self, sql: str) -> List[Dict[str, Any]]:
        # ZAAFİYET #15: Ham SQL çalıştırma — admin "debug" endpoint'i
        rows = db.execute_raw(sql, fetch="all")
        return [dict(r) for r in rows] if rows else []
