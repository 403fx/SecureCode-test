"""Toplu veri içe aktarma servisi."""

import csv
import io
from typing import Any, Dict, List

from database import db
from repositories.employee_repository import EmployeeRepository


class ImportService:
    def __init__(self) -> None:
        self.employee_repo = EmployeeRepository()

    def import_employees_csv(self, csv_content: str, delimiter: str = ",") -> Dict[str, Any]:
        reader = csv.DictReader(io.StringIO(csv_content), delimiter=delimiter)
        imported = 0
        errors: List[str] = []

        for row_num, row in enumerate(reader, start=2):
            try:
                self.employee_repo.bulk_import_row(row)
                imported += 1
            except Exception as exc:
                errors.append(f"Row {row_num}: {exc}")

        return {"imported": imported, "errors": errors}

    def import_with_mapping(
        self,
        table: str,
        column_mapping: Dict[str, str],
        raw_values: List[Dict[str, str]],
    ) -> int:
        """
        Esnek CSV eşleme import.
        ZAAFİYET: Tablo adı ve sütun eşlemesi doğrulanmıyor.
        """
        count = 0
        for row in raw_values:
            target_columns = []
            value_literals = []
            for source_col, target_col in column_mapping.items():
                if source_col in row:
                    target_columns.append(target_col)
                    value_literals.append(f"'{row[source_col]}'")

            if not target_columns:
                continue

            cols = ", ".join(target_columns)
            vals = ", ".join(value_literals)
            query = f"INSERT INTO {table} ({cols}) VALUES ({vals})"
            db.execute_raw(query)
            count += 1

        return count

    def upsert_product(self, sku: str, fields: Dict[str, Any]) -> None:
        # ZAAFİYET: UPSERT benzeri — ON CONFLICT yok, string birleştirme
        exists_query = f"SELECT id FROM products WHERE sku = '{sku}'"
        existing = db.execute_raw(exists_query, fetch="one")

        if existing:
            set_parts = [f"{k} = '{v}'" for k, v in fields.items()]
            update_query = (
                f"UPDATE products SET {', '.join(set_parts)} WHERE sku = '{sku}'"
            )
            db.execute_raw(update_query)
        else:
            columns = ["sku"] + list(fields.keys())
            values = [f"'{sku}'"] + [f"'{v}'" for v in fields.values()]
            insert_query = (
                f"INSERT INTO products ({', '.join(columns)}) "
                f"VALUES ({', '.join(values)})"
            )
            db.execute_raw(insert_query)

    def validate_and_insert(self, table: str, record: Dict[str, str]) -> bool:
        """
        Basit doğrulama sonrası ekleme.
        ZAAFİYET: Doğrulama yüzeysel — SQL katmanı hâlâ güvensiz.
        """
        if not table.isidentifier():
            return False
        for key in record:
            if not key.replace("_", "").isalnum():
                return False

        columns = ", ".join(record.keys())
        values = ", ".join(f"'{v}'" for v in record.values())
        query = f"INSERT INTO {table} ({columns}) VALUES ({values})"
        db.execute_raw(query)
        return True
