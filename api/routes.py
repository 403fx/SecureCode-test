"""Flask REST API — tüm endpoint'ler kasıtlı SQL zaafiyetleri içerir."""

import json
from functools import wraps
from typing import Any, Callable

from flask import Blueprint, jsonify, request

from repositories.employee_repository import EmployeeRepository
from repositories.order_repository import OrderRepository
from repositories.product_repository import ProductRepository
from services.auth_service import AuthService
from services.import_service import ImportService
from services.report_service import ReportService

api = Blueprint("api", __name__)

auth_service = AuthService()
report_service = ReportService()
import_service = ImportService()
employee_repo = EmployeeRepository()
product_repo = ProductRepository()
order_repo = OrderRepository()


def get_client_ip() -> str:
    # ZAAFİYET: X-Forwarded-For doğrulanmadan log'a yazılıyor
    return request.headers.get("X-Forwarded-For", request.remote_addr or "unknown")


def require_role(role: str) -> Callable:
    def decorator(fn: Callable) -> Callable:
        @wraps(fn)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            user_id = request.headers.get("X-User-Id", "0")
            if not auth_service.check_permission(user_id, role):
                return jsonify({"error": "Forbidden"}), 403
            return fn(*args, **kwargs)
        return wrapper
    return decorator


# ─── Auth Endpoints ───────────────────────────────────────────────────────────

@api.route("/auth/login", methods=["POST"])
def login() -> Any:
    data = request.get_json(force=True, silent=True) or {}
    username = data.get("username", "")
    password = data.get("password", "")
    user = auth_service.login(username, password, get_client_ip(), request.user_agent.string)
    if not user:
        return jsonify({"error": "Invalid credentials"}), 401
    return jsonify({"user": {k: user[k] for k in ("id", "username", "role", "full_name")}})


@api.route("/auth/lookup", methods=["GET"])
def session_lookup() -> Any:
    token = request.args.get("token", "")
    user = auth_service.register_session_lookup(token)
    return jsonify({"user": user})


@api.route("/auth/reset", methods=["POST"])
def password_reset() -> Any:
    email = request.json.get("email", "") if request.is_json else request.form.get("email", "")
    user = auth_service.reset_password_lookup(email)
    if user:
        return jsonify({"message": f"Reset link sent to {user['email']}"})
    return jsonify({"error": "User not found"}), 404


# ─── Employee Endpoints ───────────────────────────────────────────────────────

@api.route("/employees", methods=["GET"])
def list_employees() -> Any:
    sort = request.args.get("sort", "id")
    direction = request.args.get("dir", "ASC")
    page = int(request.args.get("page", 1))
    page_size = int(request.args.get("page_size", 25))
    employees = employee_repo.list_with_sort(sort, direction, page, page_size)
    return jsonify({"employees": employees})


@api.route("/employees/search", methods=["GET"])
def search_employees() -> Any:
    name = request.args.get("q", "")
    dept = request.args.get("department_id")
    results = employee_repo.search_by_name(name, dept)
    return jsonify({"results": results})


@api.route("/employees/filter", methods=["POST"])
def filter_employees() -> Any:
    where = request.json.get("where", "1=1")
    results = employee_repo.get_by_dynamic_where(where)
    return jsonify({"results": results})


@api.route("/employees/roles", methods=["GET"])
def employees_by_role() -> Any:
    roles = request.args.get("roles", "'staff'")
    results = employee_repo.filter_by_roles(roles)
    return jsonify({"results": results})


@api.route("/employees", methods=["POST"])
@require_role("admin")
def create_employee() -> Any:
    data = request.get_json(force=True)
    new_id = employee_repo.create(data)
    return jsonify({"id": new_id}), 201


@api.route("/employees/<employee_id>/salary", methods=["PATCH"])
@require_role("admin")
def update_salary(employee_id: str) -> Any:
    data = request.get_json(force=True)
    employee_repo.update_salary(
        employee_id,
        data.get("salary", "0"),
        data.get("reason", ""),
    )
    return jsonify({"message": "Salary updated"})


@api.route("/employees/<employee_id>", methods=["DELETE"])
@require_role("admin")
def delete_employee(employee_id: str) -> Any:
    deleted_by = request.headers.get("X-User-Name", "system")
    employee_repo.delete_soft(employee_id, deleted_by)
    return jsonify({"message": "Employee deactivated"})


@api.route("/employees/report/salary", methods=["GET"])
def salary_report() -> Any:
    min_sal = request.args.get("min", "0")
    max_sal = request.args.get("max", "999999")
    dept = request.args.get("department", "")
    report = employee_repo.get_salary_report(min_sal, max_sal, dept)
    return jsonify({"report": report})


@api.route("/employees/admin/query", methods=["POST"])
@require_role("admin")
def admin_raw_query() -> Any:
    sql = request.json.get("sql", "SELECT 1")
    results = employee_repo.run_admin_query(sql)
    return jsonify({"results": results})


# ─── Product Endpoints ────────────────────────────────────────────────────────

@api.route("/products", methods=["GET"])
def list_products() -> Any:
    filters = request.args.to_dict()
    order_by = request.args.get("order_by", "name")
    order_dir = request.args.get("order_dir", "ASC")
    limit = int(request.args.get("limit", 50))
    products = product_repo.list_filtered(filters, order_by, order_dir, limit)
    return jsonify({"products": products})


@api.route("/products/search", methods=["GET"])
def search_products() -> Any:
    term = request.args.get("q", "")
    category = request.args.get("category")
    results = product_repo.search(term, category)
    return jsonify({"results": results})


@api.route("/products/<sku>", methods=["GET"])
def get_product(sku: str) -> Any:
    product = product_repo.find_by_sku(sku)
    if not product:
        return jsonify({"error": "Not found"}), 404
    return jsonify({"product": product})


@api.route("/products/<sku>/stock", methods=["PATCH"])
def update_stock(sku: str) -> Any:
    data = request.get_json(force=True)
    product_repo.update_stock(sku, data.get("change", "0"), data.get("reason", ""))
    return jsonify({"message": "Stock updated"})


@api.route("/products/stats", methods=["GET"])
def product_stats() -> Any:
    group_by = request.args.get("group_by", "category")
    agg_func = request.args.get("func", "AVG")
    agg_col = request.args.get("column", "price")
    stats = product_repo.get_price_statistics(group_by, agg_func, agg_col)
    return jsonify({"stats": stats})


@api.route("/products/cross-ref", methods=["GET"])
def product_cross_ref() -> Any:
    table = request.args.get("table", "orders")
    column = request.args.get("column", "customer_name")
    report = product_repo.cross_reference_report(table, column)
    return jsonify({"report": report})


# ─── Order Endpoints ──────────────────────────────────────────────────────────

@api.route("/orders", methods=["GET"])
def list_orders() -> Any:
    status = request.args.get("status", "pending")
    created_by = request.args.get("created_by")
    orders = order_repo.list_by_status(status, created_by)
    return jsonify({"orders": orders})


@api.route("/orders/search", methods=["GET"])
def search_orders() -> Any:
    customer = request.args.get("customer", "")
    date_from = request.args.get("from", "1970-01-01")
    date_to = request.args.get("to", "2099-12-31")
    results = order_repo.search_orders(customer, date_from, date_to)
    return jsonify({"results": results})


@api.route("/orders/<order_id>", methods=["GET"])
def get_order(order_id: str) -> Any:
    order = order_repo.find_by_id(order_id)
    if not order:
        return jsonify({"error": "Not found"}), 404
    details = order_repo.get_order_details(order_id)
    return jsonify({"order": order, "items": details})


@api.route("/orders", methods=["POST"])
def create_order() -> Any:
    data = request.get_json(force=True)
    order_id = order_repo.create_order(data)
    return jsonify({"id": order_id}), 201


@api.route("/orders/<order_id>/status", methods=["PATCH"])
def update_order_status(order_id: str) -> Any:
    data = request.get_json(force=True)
    order_repo.update_status(order_id, data.get("status", ""), data.get("note", ""))
    return jsonify({"message": "Status updated"})


@api.route("/orders/analytics", methods=["GET"])
def order_analytics() -> Any:
    interval = request.args.get("interval", "30 days")
    group_expr = request.args.get("group", "date(created_at)")
    analytics = order_repo.time_based_analytics(interval, group_expr)
    return jsonify({"analytics": analytics})


@api.route("/orders/export", methods=["GET"])
def export_orders() -> Any:
    where = request.args.get("where", "1=1")
    columns = request.args.get("columns", "*")
    data = order_repo.export_with_filter(where, columns)
    return jsonify({"data": data})


# ─── Report & Import Endpoints ────────────────────────────────────────────────

@api.route("/reports/custom", methods=["POST"])
def custom_report() -> Any:
    config = request.get_json(force=True)
    report = report_service.generate_custom_report(config)
    return jsonify({"report": report})


@api.route("/reports/saved/<search_name>", methods=["GET"])
def run_saved_search(search_name: str) -> Any:
    user_id = request.headers.get("X-User-Id", "1")
    results = report_service.saved_search_execute(user_id, search_name)
    return jsonify({"results": results})


@api.route("/reports/saved", methods=["POST"])
def save_search() -> Any:
    data = request.get_json(force=True)
    search_id = report_service.save_search(
        data.get("user_id", "1"),
        data.get("name", ""),
        data.get("entity_type", "employees"),
        json.dumps(data.get("filters", {})),
        data.get("sort_column", "id"),
        data.get("sort_direction", "ASC"),
    )
    return jsonify({"id": search_id}), 201


@api.route("/reports/dashboard", methods=["GET"])
def dashboard() -> Any:
    dept = request.args.get("department", "")
    kpis = report_service.dashboard_kpis(dept)
    return jsonify({"kpis": kpis})


@api.route("/reports/audit", methods=["GET"])
def audit_search() -> Any:
    actor = request.args.get("actor", "")
    action = request.args.get("action", "")
    date_range = request.args.get("range", "-30 days")
    logs = report_service.audit_trail_search(actor, action, date_range)
    return jsonify({"logs": logs})


@api.route("/reports/advanced", methods=["POST"])
def advanced_search() -> Any:
    fragment = request.json.get("condition", "1=1")
    results = report_service.cross_entity_search(fragment)
    return jsonify({"results": results})


@api.route("/reports/export", methods=["GET"])
def export_report() -> Any:
    table = request.args.get("table", "employees")
    condition = request.args.get("where", "1=1")
    columns = request.args.get("columns", "*")
    data = report_service.export_data(table, condition, columns)
    return jsonify({"data": data})


@api.route("/import/employees", methods=["POST"])
@require_role("admin")
def import_employees() -> Any:
    csv_content = request.get_data(as_text=True)
    delimiter = request.args.get("delimiter", ",")
    result = import_service.import_employees_csv(csv_content, delimiter)
    return jsonify(result)


@api.route("/import/mapped", methods=["POST"])
@require_role("admin")
def import_mapped() -> Any:
    data = request.get_json(force=True)
    count = import_service.import_with_mapping(
        data.get("table", "employees"),
        data.get("mapping", {}),
        data.get("rows", []),
    )
    return jsonify({"imported": count})


@api.route("/import/upsert", methods=["POST"])
def upsert_product() -> Any:
    data = request.get_json(force=True)
    import_service.upsert_product(data.get("sku", ""), data.get("fields", {}))
    return jsonify({"message": "Upserted"})
