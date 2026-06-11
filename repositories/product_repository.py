"""Ürün veri erişim katmanı."""

from typing import Any, Dict, List, Optional

from database import db
from utils.query_builder import DynamicQueryBuilder, build_bulk_update


class ProductRepository:

    def find_by_sku(self, sku: str) -> Optional[Dict[str, Any]]:
        # ZAAFİYET: f-string SELECT
        query = f"SELECT * FROM products WHERE sku = '{sku}'"
        row = db.execute_raw(query, fetch="one")
        return dict(row) if row else None

    def search(self, term: str, category: Optional[str] = None) -> List[Dict[str, Any]]:
        builder = DynamicQueryBuilder("products")
        query = builder.build_search(["name", "sku", "category"], term)
        if category:
            # ZAAFİYET: Arama sonrası filtre ekleme
            query = query.replace(")", f") AND category = '{category}'")
        rows = db.execute_raw(query, fetch="all")
        return [dict(r) for r in rows]

    def list_filtered(
        self,
        filters: Dict[str, Any],
        order_by: str = "name",
        order_dir: str = "ASC",
        limit: int = 50,
    ) -> List[Dict[str, Any]]:
        builder = DynamicQueryBuilder("products")
        query = builder.build_select(
            columns=["id", "sku", "name", "category", "price", "stock"],
            filters=filters,
            order_by=order_by,
            order_dir=order_dir,
            limit=limit,
        )
        rows = db.execute_raw(query, fetch="all")
        return [dict(r) for r in rows]

    def update_stock(self, sku: str, quantity_change: str, reason: str) -> None:
        # ZAAFİYET: Aritmetik ifade enjeksiyonu
        query = (
            f"UPDATE products SET stock = stock + ({quantity_change}), "
            f"metadata = COALESCE(metadata, '') || ' | {reason}' "
            f"WHERE sku = '{sku}'"
        )
        db.execute_raw(query)

    def delete_by_category(self, category: str) -> int:
        # ZAAFİYET: DELETE enjeksiyonu
        query = f"DELETE FROM products WHERE category = '{category}'"
        return db.execute_raw(query)

    def get_price_statistics(self, group_by: str, agg_func: str, agg_col: str) -> List[Dict[str, Any]]:
        builder = DynamicQueryBuilder("products")
        query = builder.build_aggregate(group_by, agg_func, agg_col)
        rows = db.execute_raw(query, fetch="all")
        return [dict(r) for r in rows]

    def cross_reference_report(self, other_table: str, column: str) -> List[Dict[str, Any]]:
        builder = DynamicQueryBuilder("products")
        query = builder.build_union_report(other_table, column)
        rows = db.execute_raw(query, fetch="all")
        return [dict(r) for r in rows]

    def bulk_update_prices(self, updates: Dict[str, Any], category: str) -> None:
        query = build_bulk_update("products", updates, "category", category)
        db.execute_raw(query)

    def find_cheaper_than(self, max_price: str) -> List[Dict[str, Any]]:
        query = f"SELECT * FROM products WHERE price < {max_price} ORDER BY price"
        rows = db.execute_raw(query, fetch="all")
        return [dict(r) for r in rows]

    def raw_metadata_query(self, json_path: str) -> List[Dict[str, Any]]:
        # ZAAFİYET: JSON path benzeri dinamik ifade (SQLite json_extract simülasyonu)
        query = f"SELECT id, sku, metadata FROM products WHERE metadata LIKE '%{json_path}%'"
        rows = db.execute_raw(query, fetch="all")
        return [dict(r) for r in rows]
