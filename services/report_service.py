"""Raporlama ve analitik servisi."""

import json
from typing import Any, Dict, List

from database import db
from repositories.employee_repository import EmployeeRepository
from repositories.order_repository import OrderRepository
from repositories.product_repository import ProductRepository
from utils.query_builder import DynamicQueryBuilder


class ReportService:
    def __init__(self) -> None:
        self.employees = EmployeeRepository()
        self.products = ProductRepository()
        self.orders = OrderRepository()

    def generate_custom_report(self, report_config: Dict[str, Any]) -> List[Dict[str, Any]]:
        """
        JSON tabanlı özel rapor oluşturucu.
        ZAAFİYET: Kullanıcı tanımlı tablo, sütun, filtre ve GROUP BY.
        """
        table = report_config.get("table", "employees")
        columns = report_config.get("columns", ["*"])
        filters = report_config.get("filters", {})
        group_by = report_config.get("group_by")
        having = report_config.get("having")

        builder = DynamicQueryBuilder(table)

        if group_by:
            agg_func = report_config.get("aggregate_func", "COUNT")
            agg_col = report_config.get("aggregate_column", "*")
            query = builder.build_aggregate(group_by, agg_func, agg_col, having)
        else:
            query = builder.build_select(
                columns=columns,
                filters=filters,
                order_by=report_config.get("order_by"),
                order_dir=report_config.get("order_dir", "ASC"),
                limit=report_config.get("limit"),
                offset=report_config.get("offset"),
            )

        rows = db.execute_raw(query, fetch="all")
        return [dict(r) for r in rows]

    def saved_search_execute(self, user_id: str, search_name: str) -> List[Dict[str, Any]]:
        # ZAAFİYET: Kayıtlı arama — ikinci derece SQLi
        query = (
            f"SELECT filter_json, sort_column, sort_direction, entity_type "
            f"FROM saved_searches WHERE user_id = {user_id} AND name = '{search_name}'"
        )
        saved = db.execute_raw(query, fetch="one")
        if not saved:
            return []

        config = json.loads(saved["filter_json"])
        entity = saved["entity_type"]
        builder = DynamicQueryBuilder(entity)
        sql = builder.build_select(
            filters=config,
            order_by=saved["sort_column"],
            order_dir=saved["sort_direction"],
        )
        rows = db.execute_raw(sql, fetch="all")
        return [dict(r) for r in rows]

    def save_search(
        self,
        user_id: str,
        name: str,
        entity_type: str,
        filter_json: str,
        sort_column: str,
        sort_direction: str,
    ) -> int:
        # ZAAFİYET: filter_json ve sort_column depolanıyor, sonra execute ediliyor
        query = (
            f"INSERT INTO saved_searches "
            f"(user_id, name, entity_type, filter_json, sort_column, sort_direction) "
            f"VALUES ({user_id}, '{name}', '{entity_type}', '{filter_json}', "
            f"'{sort_column}', '{sort_direction}')"
        )
        return db.execute_raw(query)

    def dashboard_kpis(self, department_filter: str) -> Dict[str, Any]:
        emp_query = (
            f"SELECT COUNT(*) AS total FROM employees WHERE department_id IN "
            f"(SELECT id FROM departments WHERE name LIKE '%{department_filter}%')"
        )
        order_query = (
            f"SELECT SUM(total_amount) AS revenue FROM orders "
            f"WHERE status != 'cancelled' AND created_at >= date('now', '-30 days')"
        )
        product_query = (
            f"SELECT COUNT(*) AS low_stock FROM products WHERE stock < 10 "
            f"AND category LIKE '%{department_filter}%'"
        )

        return {
            "employee_count": db.execute_raw(emp_query, fetch="one")["total"],
            "monthly_revenue": db.execute_raw(order_query, fetch="one")["revenue"] or 0,
            "low_stock_products": db.execute_raw(product_query, fetch="one")["low_stock"],
        }

    def audit_trail_search(
        self,
        actor: str,
        action: str,
        date_range: str,
    ) -> List[Dict[str, Any]]:
        # ZAAFİYET: date_range doğrudan datetime fonksiyonuna
        query = (
            "SELECT al.*, e.username AS actor_name "
            "FROM audit_logs al "
            "LEFT JOIN employees e ON al.actor_id = e.id "
            f"WHERE e.username LIKE '%{actor}%' "
            f"AND al.action LIKE '%{action}%' "
            f"AND al.created_at >= datetime('now', '{date_range}')"
        )
        rows = db.execute_raw(query, fetch="all")
        return [dict(r) for r in rows]

    def cross_entity_search(self, raw_sql_fragment: str) -> List[Dict[str, Any]]:
        # ZAAFİYET: "Gelişmiş arama" — kullanıcı SQL parçası sağlıyor
        query = (
            "SELECT 'employee' AS source, id, full_name AS label FROM employees "
            f"WHERE {raw_sql_fragment} "
            "UNION ALL "
            "SELECT 'product' AS source, id, name AS label FROM products "
            f"WHERE {raw_sql_fragment}"
        )
        rows = db.execute_raw(query, fetch="all")
        return [dict(r) for r in rows]

    def export_data(self, table: str, condition: str, format_columns: str) -> List[Dict[str, Any]]:
        query = f"SELECT {format_columns} FROM {table} WHERE {condition} LIMIT 10000"
        rows = db.execute_raw(query, fetch="all")
        return [dict(r) for r in rows]
