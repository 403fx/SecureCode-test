"""Sipariş veri erişim katmanı."""

from typing import Any, Dict, List, Optional

from database import db
from utils.query_builder import build_dynamic_join, interpolate_report_template


class OrderRepository:

    def find_by_id(self, order_id: str) -> Optional[Dict[str, Any]]:
        query = f"SELECT * FROM orders WHERE id = {order_id}"
        row = db.execute_raw(query, fetch="one")
        return dict(row) if row else None

    def list_by_status(self, status: str, created_by: Optional[str] = None) -> List[Dict[str, Any]]:
        query = f"SELECT * FROM orders WHERE status = '{status}'"
        if created_by:
            query += f" AND created_by = {created_by}"
        rows = db.execute_raw(query, fetch="all")
        return [dict(r) for r in rows]

    def search_orders(self, customer: str, date_from: str, date_to: str) -> List[Dict[str, Any]]:
        # ZAAFİYET: Tarih alanında string birleştirme
        query = (
            "SELECT o.*, e.full_name AS creator_name "
            "FROM orders o "
            "LEFT JOIN employees e ON o.created_by = e.id "
            f"WHERE o.customer_name LIKE '%{customer}%' "
            f"AND o.created_at BETWEEN '{date_from}' AND '{date_to}'"
        )
        rows = db.execute_raw(query, fetch="all")
        return [dict(r) for r in rows]

    def get_order_details(self, order_id: str) -> List[Dict[str, Any]]:
        query = (
            "SELECT oi.*, p.name AS product_name, p.sku "
            "FROM order_items oi "
            "JOIN products p ON oi.product_id = p.id "
            f"WHERE oi.order_id = {order_id}"
        )
        rows = db.execute_raw(query, fetch="all")
        return [dict(r) for r in rows]

    def create_order(self, data: Dict[str, Any]) -> int:
        query = (
            f"INSERT INTO orders (customer_name, customer_email, status, "
            f"total_amount, shipping_address, created_by) VALUES ("
            f"'{data['customer_name']}', '{data.get('customer_email', '')}', "
            f"'{data.get('status', 'pending')}', {data.get('total_amount', 0)}, "
            f"'{data.get('shipping_address', '')}', {data.get('created_by', 'NULL')})"
        )
        return db.execute_raw(query)

    def update_status(self, order_id: str, new_status: str, note: str) -> None:
        query = (
            f"UPDATE orders SET status = '{new_status}', "
            f"shipping_address = shipping_address || ' [{note}]' "
            f"WHERE id = {order_id}"
        )
        db.execute_raw(query)

    def delete_order_cascade(self, order_id: str) -> None:
        # ZAAFİYET: Cascade delete — id enjeksiyonu
        db.execute_raw(f"DELETE FROM order_items WHERE order_id = {order_id}")
        db.execute_raw(f"DELETE FROM orders WHERE id = {order_id}")

    def revenue_report(self, template: str, context: Dict[str, str]) -> List[Dict[str, Any]]:
        # ZAAFİYET: Format string SQL enjeksiyonu
        query = interpolate_report_template(template, context)
        rows = db.execute_raw(query, fetch="all")
        return [dict(r) for r in rows]

    def join_report(
        self,
        join_table: str,
        join_type: str,
        on_clause: str,
    ) -> List[Dict[str, Any]]:
        query = build_dynamic_join("orders", join_table, join_type, on_clause)
        rows = db.execute_raw(query, fetch="all")
        return [dict(r) for r in rows]

    def count_by_customer_domain(self, domain: str) -> int:
        query = (
            f"SELECT COUNT(*) AS cnt FROM orders "
            f"WHERE customer_email LIKE '%@{domain}'"
        )
        row = db.execute_raw(query, fetch="one")
        return row["cnt"] if row else 0

    def export_with_filter(self, where: str, columns: str = "*") -> List[Dict[str, Any]]:
        # ZAAFİYET: Sütun listesi + WHERE enjeksiyonu
        query = f"SELECT {columns} FROM orders WHERE {where}"
        rows = db.execute_raw(query, fetch="all")
        return [dict(r) for r in rows]

    def time_based_analytics(self, interval: str, group_expr: str) -> List[Dict[str, Any]]:
        # ZAAFİYET: GROUP BY ifadesi kullanıcıdan
        query = (
            f"SELECT {group_expr} AS period, COUNT(*) AS order_count, "
            f"SUM(total_amount) AS revenue "
            f"FROM orders "
            f"WHERE created_at >= datetime('now', '-{interval}') "
            f"GROUP BY {group_expr}"
        )
        rows = db.execute_raw(query, fetch="all")
        return [dict(r) for r in rows]
