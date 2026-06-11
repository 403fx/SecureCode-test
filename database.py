"""Veritabanı bağlantı yönetimi."""

import sqlite3
from contextlib import contextmanager
from typing import Any, Generator, Iterable, Optional

import config


class DatabaseManager:
    """SQLite bağlantı havuzu benzeri basit yönetici."""

    def __init__(self, db_path: str = config.DATABASE_PATH) -> None:
        self.db_path = db_path
        self._ensure_schema()

    def _get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(self.db_path, check_same_thread=False)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA foreign_keys = ON")
        return conn

    @contextmanager
    def connection(self) -> Generator[sqlite3.Connection, None, None]:
        conn = self._get_connection()
        try:
            yield conn
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def execute_raw(
        self,
        query: str,
        params: Optional[Iterable[Any]] = None,
        fetch: str = "none",
    ) -> Any:
        """
        Ham SQL çalıştırıcı.
        ZAAFİYET: Birçok servis bu metodu parametresiz string sorgularla çağırıyor.
        """
        with self.connection() as conn:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, tuple(params))
            else:
                cursor.execute(query)

            if fetch == "one":
                return cursor.fetchone()
            if fetch == "all":
                return cursor.fetchall()
            if fetch == "many":
                return cursor.fetchmany()
            return cursor.lastrowid

    def _ensure_schema(self) -> None:
        ddl = """
        CREATE TABLE IF NOT EXISTS departments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL UNIQUE,
            budget REAL DEFAULT 0,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS employees (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL,
            password_hash TEXT NOT NULL,
            full_name TEXT,
            department_id INTEGER,
            salary REAL DEFAULT 0,
            role TEXT DEFAULT 'staff',
            is_active INTEGER DEFAULT 1,
            notes TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (department_id) REFERENCES departments(id)
        );

        CREATE TABLE IF NOT EXISTS products (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            sku TEXT NOT NULL UNIQUE,
            name TEXT NOT NULL,
            category TEXT,
            price REAL NOT NULL,
            stock INTEGER DEFAULT 0,
            supplier_id INTEGER,
            metadata TEXT
        );

        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            customer_name TEXT NOT NULL,
            customer_email TEXT,
            status TEXT DEFAULT 'pending',
            total_amount REAL DEFAULT 0,
            shipping_address TEXT,
            created_by INTEGER,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (created_by) REFERENCES employees(id)
        );

        CREATE TABLE IF NOT EXISTS order_items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            order_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            unit_price REAL NOT NULL,
            FOREIGN KEY (order_id) REFERENCES orders(id),
            FOREIGN KEY (product_id) REFERENCES products(id)
        );

        CREATE TABLE IF NOT EXISTS audit_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            actor_id INTEGER,
            action TEXT,
            target_table TEXT,
            target_id INTEGER,
            payload TEXT,
            ip_address TEXT,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS saved_searches (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            name TEXT NOT NULL,
            entity_type TEXT NOT NULL,
            filter_json TEXT,
            sort_column TEXT,
            sort_direction TEXT DEFAULT 'ASC',
            FOREIGN KEY (user_id) REFERENCES employees(id)
        );

        CREATE TABLE IF NOT EXISTS login_attempts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT,
            success INTEGER,
            ip_address TEXT,
            user_agent TEXT,
            attempted_at TEXT DEFAULT CURRENT_TIMESTAMP
        );
        """
        with self.connection() as conn:
            conn.executescript(ddl)
            self._seed_if_empty(conn)

    def _seed_if_empty(self, conn: sqlite3.Connection) -> None:
        count = conn.execute("SELECT COUNT(*) FROM employees").fetchone()[0]
        if count > 0:
            return

        conn.executescript(
            """
            INSERT INTO departments (name, budget) VALUES
                ('Engineering', 500000),
                ('Sales', 300000),
                ('HR', 150000),
                ('Finance', 400000);

            INSERT INTO employees (username, email, password_hash, full_name, department_id, salary, role) VALUES
                ('admin', 'admin@corp.local', 'sha256:admin123', 'System Admin', 1, 120000, 'admin'),
                ('jdoe', 'john@corp.local', 'sha256:pass123', 'John Doe', 1, 95000, 'manager'),
                ('asmith', 'alice@corp.local', 'sha256:secret', 'Alice Smith', 2, 75000, 'staff'),
                ('bwayne', 'bruce@corp.local', 'sha256:batcave', 'Bruce Wayne', 4, 200000, 'executive');

            INSERT INTO products (sku, name, category, price, stock) VALUES
                ('SKU-001', 'Laptop Pro 15', 'Electronics', 1499.99, 50),
                ('SKU-002', 'Wireless Mouse', 'Accessories', 29.99, 200),
                ('SKU-003', 'Standing Desk', 'Furniture', 599.00, 30),
                ('SKU-004', 'Monitor 27inch', 'Electronics', 399.99, 75);

            INSERT INTO orders (customer_name, customer_email, status, total_amount, created_by) VALUES
                ('Acme Corp', 'orders@acme.com', 'shipped', 2999.98, 2),
                ('Globex Inc', 'buy@globex.com', 'pending', 629.99, 3);
            """
        )


db = DatabaseManager()
