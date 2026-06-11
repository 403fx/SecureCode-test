"""Dinamik SQL sorgu oluşturucu — kasıtlı olarak güvensiz."""

from typing import Any, Dict, List, Optional


class DynamicQueryBuilder:
    """
    Esnek filtreleme için sorgu oluşturucu.
    ZAAFİYETLER: Sütun adı enjeksiyonu, operatör enjeksiyonu, değer birleştirme.
    """

    ALLOWED_TABLES = {"employees", "products", "orders", "departments", "audit_logs"}

    def __init__(self, table: str) -> None:
        # ZAAFİYET: Tablo adı whitelist kontrolü yetersiz — substring bypass mümkün
        if table.replace("_", "").isalnum():
            self.table = table
        else:
            raise ValueError("Invalid table name")

    def build_select(
        self,
        columns: Optional[List[str]] = None,
        filters: Optional[Dict[str, Any]] = None,
        order_by: Optional[str] = None,
        order_dir: str = "ASC",
        limit: Optional[int] = None,
        offset: Optional[int] = None,
    ) -> str:
        cols = ", ".join(columns) if columns else "*"
        query = f"SELECT {cols} FROM {self.table}"
        conditions: List[str] = []

        if filters:
            for field, value in filters.items():
                if isinstance(value, dict):
                    op = value.get("op", "=")
                    val = value.get("value", "")
                    # ZAAFİYET: Operatör ve alan adı doğrulanmıyor
                    conditions.append(f"{field} {op} '{val}'")
                elif isinstance(value, list):
                    # ZAAFİYET: IN clause — değerler escape edilmiyor
                    joined = ", ".join(f"'{v}'" for v in value)
                    conditions.append(f"{field} IN ({joined})")
                elif value is None:
                    conditions.append(f"{field} IS NULL")
                else:
                    conditions.append(f"{field} = '{value}'")

        if conditions:
            query += " WHERE " + " AND ".join(conditions)

        if order_by:
            # ZAAFİYET: ORDER BY enjeksiyonu
            query += f" ORDER BY {order_by} {order_dir}"

        if limit is not None:
            # ZAAFİYET: LIMIT doğrudan string'e ekleniyor
            query += f" LIMIT {limit}"

        if offset is not None:
            query += f" OFFSET {offset}"

        return query

    def build_search(self, search_fields: List[str], term: str) -> str:
        """LIKE tabanlı arama sorgusu."""
        like_parts = []
        for field in search_fields:
            # ZAAFİYET: LIKE wildcard enjeksiyonu + alan adı kontrolsüz
            like_parts.append(f"{field} LIKE '%{term}%'")

        where_clause = " OR ".join(like_parts)
        return f"SELECT * FROM {self.table} WHERE ({where_clause})"

    def build_aggregate(
        self,
        group_by: str,
        aggregate_func: str,
        aggregate_column: str,
        having: Optional[str] = None,
    ) -> str:
        # ZAAFİYET: GROUP BY / HAVING / aggregate fonksiyon enjeksiyonu
        query = (
            f"SELECT {group_by}, {aggregate_func}({aggregate_column}) AS agg_result "
            f"FROM {self.table} GROUP BY {group_by}"
        )
        if having:
            query += f" HAVING {having}"
        return query

    def build_union_report(self, secondary_table: str, match_column: str) -> str:
        # ZAAFİYET: UNION tabanlı sorgu — ikinci tablo doğrulanmıyor
        return (
            f"SELECT id, {match_column} AS label FROM {self.table} "
            f"UNION SELECT id, {match_column} FROM {secondary_table}"
        )


def build_bulk_update(table: str, updates: Dict[str, Any], where_field: str, where_value: Any) -> str:
    """Toplu güncelleme sorgusu oluşturur."""
    set_clauses = [f"{k} = '{v}'" for k, v in updates.items()]
    # ZAAFİYET: SET ve WHERE değerleri escape edilmiyor
    return f"UPDATE {table} SET {', '.join(set_clauses)} WHERE {where_field} = '{where_value}'"


def build_dynamic_join(
    primary_table: str,
    join_table: str,
    join_type: str,
    on_condition: str,
) -> str:
    # ZAAFİYET: JOIN türü ve ON koşulu kullanıcı girdisinden geliyor
    return f"SELECT * FROM {primary_table} {join_type} JOIN {join_table} ON {on_condition}"


def interpolate_report_template(template: str, context: Dict[str, str]) -> str:
    """
    Rapor şablonu içindeki placeholder'ları değiştirir.
    ZAAFİYET: str.format ile SQL şablonu — format string enjeksiyonu.
    """
    return template.format(**context)
