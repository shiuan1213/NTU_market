# ==========================================
# NTU Marketplace - Final Server.py (Admin + JSON Fix)
# ==========================================
import socket
import threading
import json
from datetime import datetime
from decimal import Decimal

import psycopg2
from psycopg2.extras import RealDictCursor

from db_config import DB_CONFIG

HOST = "127.0.0.1"
PORT = 5000

# ------------------------------------------
# Utility
# ------------------------------------------
def get_db_connection():
    return psycopg2.connect(**DB_CONFIG)


def serialize_value(v):
    """統一把 datetime / Decimal 轉成 JSON 可序列化型別。"""
    if isinstance(v, datetime):
        return v.isoformat(sep=" ", timespec="seconds")
    if isinstance(v, Decimal):
        return float(v)
    return v


def serialize_rows(rows):
    """
    專門給 analytics / NoSQL 用，因為 RealDictCursor 會回傳 dict-like 物件，
    裡面常常有 Decimal / datetime。
    """
    out = []
    for row in rows:
        # RealDictRow / dict
        if hasattr(row, "items"):
            out.append({k: serialize_value(v) for k, v in row.items()})
        else:
            # tuple 類型就整個 list 化
            out.append([serialize_value(v) for v in row])
    return out


# ============================================================
# Login
# ============================================================
def handle_login(conn, req):
    email = req.get("email")
    password = req.get("password")

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT u.student_no, u.full_name, u.email,
                   CASE
                       WHEN EXISTS (
                           SELECT 1 FROM user_roles ur
                           WHERE ur.student_no = u.student_no AND ur.role='admin'
                       )
                       THEN 'admin'
                       ELSE 'user'
                   END AS role
            FROM users u
            WHERE email=%s AND password_hash=%s AND is_verified=TRUE
        """,
            (email, password),
        )
        row = cur.fetchone()

    if row:
        return {
            "status": "ok",
            "student_no": row["student_no"],
            "full_name": row["full_name"],
            "email": row["email"],
            "role": row["role"],
        }

    return {"status": "fail", "message": "Email 或密碼錯誤，或帳號尚未驗證"}


# =========================================================
# Browsing items
# =========================================================
def handle_list_items(conn, req):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT i.item_id, i.title, i.price, i.condition,
                   i.quantity, c.name AS category_name,
                   u.full_name AS seller_name
            FROM items i
            LEFT JOIN categories c ON i.category_id = c.category_id
            JOIN users u ON i.seller_student_no = u.student_no
            WHERE i.status='Listed' AND i.quantity > 0
            ORDER BY i.item_id
        """
        )
        rows = cur.fetchall()

    items = [
        {
            "item_id": r[0],
            "title": r[1],
            "price": float(r[2]),
            "condition": r[3],
            "quantity": r[4],
            "category_name": r[5],
            "seller_name": r[6],
        }
        for r in rows
    ]

    return {"status": "ok", "items": items}


# =========================================================
# My selling items
# =========================================================
def handle_list_my_selling_items(conn, req):
    student_no = req.get("student_no")

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT item_id, title, price, quantity, status
            FROM items
            WHERE seller_student_no=%s
            ORDER BY item_id
        """,
            (student_no,),
        )
        rows = cur.fetchall()

    items = [
        {
            "item_id": r[0],
            "title": r[1],
            "price": float(r[2]),
            "quantity": r[3],
            "status": r[4],
        }
        for r in rows
    ]

    return {"status": "ok", "items": items}


# =========================================================
# Place order
# =========================================================
def handle_place_order(conn, req):
    buyer_no = req.get("student_no")
    item_id = req.get("item_id")
    qty = req.get("qty")

    if qty is None or qty <= 0:
        return {"status": "fail", "message": "數量需大於 0"}

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT seller_student_no, price, quantity, status
                    FROM items
                    WHERE item_id=%s FOR UPDATE
                """,
                    (item_id,),
                )
                row = cur.fetchone()

                if not row:
                    return {"status": "fail", "message": "找不到商品"}

                seller_no, price, stock, status = row

                if status != "Listed" or stock <= 0:
                    return {"status": "fail", "message": "商品已下架或無庫存"}

                if stock < qty:
                    return {"status": "fail", "message": "庫存不足"}

                total_amount = price * qty

                cur.execute(
                    """
                    INSERT INTO orders (
                        buyer_student_no, seller_student_no,
                        order_type, status, total_amount,
                        consignee_name, consignee_phone, shipping_address,
                        created_at, paid_at
                    )
                    SELECT %s, %s, 'direct', 'Paid', %s,
                           full_name, phone, '校內面交',
                           NOW(), NOW()
                    FROM users WHERE student_no=%s
                    RETURNING order_id
                """,
                    (buyer_no, seller_no, total_amount, buyer_no),
                )
                order_id = cur.fetchone()[0]

                cur.execute(
                    """
                    INSERT INTO order_items (order_id, item_id, qty, price_each, title_snapshot)
                    SELECT %s, item_id, %s, price, title FROM items WHERE item_id=%s
                """,
                    (order_id, qty, item_id),
                )

                cur.execute(
                    """
                    INSERT INTO payments (order_id, method, amount, status, txn_ref, paid_at)
                    VALUES (%s, 'credit_card', %s, 'Success', %s, NOW())
                """,
                    (order_id, total_amount, f"TXN-{order_id:06d}"),
                )

                new_stock = stock - qty
                new_status = "SoldOut" if new_stock == 0 else "Listed"
                cur.execute(
                    """
                    UPDATE items SET quantity=%s, status=%s, updated_at=NOW()
                    WHERE item_id=%s
                """,
                    (new_stock, new_status, item_id),
                )

        return {
            "status": "ok",
            "order_id": order_id,
            "total_amount": float(total_amount),
        }

    except Exception as e:
        return {"status": "fail", "message": f"下單失敗：{e}"}


# =========================================================
# My orders
# =========================================================
def handle_my_orders(conn, req):
    student_no = req.get("student_no")

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT o.order_id, o.status, o.total_amount,
                   u.full_name AS seller_name,
                   o.created_at, o.paid_at, o.shipped_at, o.completed_at
            FROM orders o
            JOIN users u ON u.student_no=o.seller_student_no
            WHERE o.buyer_student_no=%s
            ORDER BY o.created_at DESC
        """,
            (student_no,),
        )
        rows = cur.fetchall()

    orders = []
    for r in rows:
        orders.append(
            {
                "order_id": r[0],
                "status": r[1],
                "total_amount": float(r[2]),
                "seller_name": r[3],
                "created_at": serialize_value(r[4]),
                "paid_at": serialize_value(r[5]) if r[5] else None,
                "shipped_at": serialize_value(r[6]) if r[6] else None,
                "completed_at": serialize_value(r[7]) if r[7] else None,
            }
        )

    return {"status": "ok", "orders": orders}


# =========================================================
# Orders to ship
# =========================================================
def handle_orders_to_ship(conn, req):
    seller_no = req.get("student_no")

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT o.order_id, o.total_amount, o.created_at,
                   u.full_name AS buyer_name
            FROM orders o
            JOIN users u ON u.student_no=o.buyer_student_no
            WHERE o.seller_student_no=%s AND o.status='Paid'
            ORDER BY o.created_at
        """,
            (seller_no,),
        )
        rows = cur.fetchall()

    data = [
        {
            "order_id": r[0],
            "total_amount": float(r[1]),
            "created_at": serialize_value(r[2]),
            "buyer_name": r[3],
        }
        for r in rows
    ]

    return {"status": "ok", "orders": data}


# =========================================================
# Ship order
# =========================================================
def handle_ship_order(conn, req):
    seller_no = req.get("student_no")
    order_id = req.get("order_id")
    carrier = req.get("carrier") or "7-11"
    tracking_no = req.get("tracking_no") or f"PKG-{int(order_id):06d}"

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT status, seller_student_no
                    FROM orders WHERE order_id=%s
                """,
                    (order_id,),
                )
                row = cur.fetchone()

                if not row:
                    return {"status": "fail", "message": "找不到訂單"}

                status, seller_db = row
                if seller_db != seller_no:
                    return {"status": "fail", "message": "此訂單非你的"}

                if status != "Paid":
                    return {"status": "fail", "message": "訂單不是 Paid"}

                cur.execute(
                    """
                    UPDATE orders
                    SET status='Shipped', shipped_at=NOW()
                    WHERE order_id=%s
                """,
                    (order_id,),
                )

                cur.execute(
                    """
                    INSERT INTO shipments (order_id, carrier, tracking_no, shipped_at)
                    VALUES (%s,%s,%s,NOW())
                    ON CONFLICT (order_id)
                    DO UPDATE SET carrier=EXCLUDED.carrier,
                                  tracking_no=EXCLUDED.tracking_no,
                                  shipped_at=EXCLUDED.shipped_at
                """,
                    (order_id, carrier, tracking_no),
                )

        return {"status": "ok", "message": "成功出貨"}

    except Exception as e:
        return {"status": "fail", "message": f"出貨失敗：{e}"}


# =========================================================
# Pending reviews
# =========================================================
def handle_pending_reviews(conn, req):
    buyer_no = req.get("student_no")

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT o.order_id, o.completed_at, u.full_name
            FROM orders o
            JOIN users u ON u.student_no=o.seller_student_no
            WHERE o.buyer_student_no=%s
              AND o.status='Completed'
              AND NOT EXISTS (
                    SELECT 1 FROM reviews r
                    WHERE r.order_id=o.order_id AND r.rater_student_no=o.buyer_student_no
              )
            ORDER BY o.completed_at DESC
        """,
            (buyer_no,),
        )
        rows = cur.fetchall()

    orders = [
        {
            "order_id": r[0],
            "completed_at": serialize_value(r[1]),
            "seller_name": r[2],
        }
        for r in rows
    ]

    return {"status": "ok", "orders": orders}


# =========================================================
# Create review
# =========================================================
def handle_create_review(conn, req):
    buyer_no = req.get("student_no")
    order_id = req.get("order_id")
    rating = req.get("rating")
    comment = req.get("comment") or ""

    try:
        rating = int(rating)
        if not (1 <= rating <= 5):
            return {"status": "fail", "message": "評分需為 1~5"}
    except Exception:
        return {"status": "fail", "message": "評分需為數字"}

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT buyer_student_no, seller_student_no, status
                    FROM orders WHERE order_id=%s
                """,
                    (order_id,),
                )
                row = cur.fetchone()

                if not row:
                    return {"status": "fail", "message": "找不到訂單"}

                buyer_db, seller_db, status = row

                if buyer_db != buyer_no:
                    return {"status": "fail", "message": "不是你的訂單"}

                if status != "Completed":
                    return {"status": "fail", "message": "訂單未完成"}

                cur.execute(
                    """
                    SELECT 1 FROM reviews
                    WHERE order_id=%s AND rater_student_no=%s
                """,
                    (order_id, buyer_no),
                )
                if cur.fetchone():
                    return {"status": "fail", "message": "已評價過"}

                cur.execute(
                    """
                    INSERT INTO reviews (order_id, rater_student_no, ratee_student_no,
                                         rating, comment, created_at)
                    VALUES (%s,%s,%s,%s,%s, NOW())
                """,
                    (order_id, buyer_no, seller_db, rating, comment),
                )

        return {"status": "ok", "message": "評價成功"}

    except Exception as e:
        return {"status": "fail", "message": f"評價失敗：{e}"}


# =========================================================
# Add item
# =========================================================
def handle_add_item(conn, req):
    seller_no = req.get("student_no")
    title = req.get("title")
    description = req.get("description") or ""
    category_id = req.get("category_id")
    condition = req.get("condition")
    quantity = req.get("quantity")
    price = req.get("price")

    try:
        quantity = int(quantity)
        price = float(price)
    except Exception:
        return {"status": "fail", "message": "數量/價格格式錯誤"}

    if quantity <= 0 or price < 0:
        return {"status": "fail", "message": "數量或價格不合法"}

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO items (
                        seller_student_no, category_id, title, description,
                        condition, quantity, price, status,
                        created_at, updated_at
                    )
                    VALUES (%s,%s,%s,%s,%s,%s,%s,
                            'Listed', NOW(), NOW())
                    RETURNING item_id
                """,
                    (
                        seller_no,
                        category_id,
                        title,
                        description,
                        condition,
                        quantity,
                        price,
                    ),
                )
                item_id = cur.fetchone()[0]

        return {"status": "ok", "message": f"成功上架（ID={item_id}）"}

    except Exception as e:
        return {"status": "fail", "message": f"新增商品失敗：{e}"}


# ================================
# Admin SQL / NoSQL Analytics
# ================================
def check_admin(db_conn, req):
    """所有 SQL / NoSQL 分析都會呼叫這裡"""
    student_no = req.get("student_no")

    if not student_no:
        return False

    with db_conn.cursor() as cur:
        cur.execute(
            """
            SELECT 1 FROM user_roles
            WHERE student_no=%s AND role='admin'
        """,
            (student_no,),
        )
        return bool(cur.fetchone())


# -------- SQL Analytics ---------
def analytics_category_revenue(conn):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT c.name AS category,
                   SUM(oi.qty * oi.price_each) AS revenue
            FROM orders o
            JOIN order_items oi ON oi.order_id=o.order_id
            JOIN items i ON i.item_id=oi.item_id
            JOIN categories c ON c.category_id=i.category_id
            WHERE o.status='Completed'
            GROUP BY c.name
            ORDER BY revenue DESC
        """
        )
        rows = cur.fetchall()
    return {"status": "ok", "data": serialize_rows(rows)}


def analytics_monthly_revenue(conn):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT DATE_TRUNC('month', paid_at) AS month,
                   SUM(total_amount) AS revenue
            FROM orders
            WHERE status='Completed'
            GROUP BY month
            ORDER BY month
        """
        )
        rows = cur.fetchall()
    return {"status": "ok", "data": serialize_rows(rows)}


def analytics_seller_rating(conn):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT ratee_student_no AS seller,
                   AVG(rating) AS avg_rating,
                   COUNT(*) AS review_count
            FROM reviews
            GROUP BY ratee_student_no
            ORDER BY avg_rating DESC
        """
        )
        rows = cur.fetchall()
    return {"status": "ok", "data": serialize_rows(rows)}


def analytics_top_items(conn):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT oi.item_id, i.title, SUM(oi.qty) AS total_sold
            FROM order_items oi
            JOIN items i ON i.item_id=oi.item_id
            GROUP BY oi.item_id, i.title
            ORDER BY total_sold DESC
            LIMIT 10
        """
        )
        rows = cur.fetchall()
    return {"status": "ok", "data": serialize_rows(rows)}


# -------- NoSQL analytics ----------
def nosql_mobile_views(conn):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT
                v.student_no,
                i.title,
                v.meta->>'device' AS device,
                v.viewed_at
            FROM view_logs v
            JOIN items i ON i.item_id = v.item_id
            WHERE v.meta->>'device' = 'mobile'
            ORDER BY v.viewed_at DESC
            LIMIT 30
        """
        )
        rows = cur.fetchall()
    return {"status": "ok", "data": serialize_rows(rows)}


def nosql_hot_views(conn):
    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT i.title,
                   COUNT(*) AS views
            FROM view_logs v
            JOIN items i ON i.item_id = v.item_id
            GROUP BY i.title
            ORDER BY views DESC
            LIMIT 10
        """
        )
        rows = cur.fetchall()
    return {"status": "ok", "data": serialize_rows(rows)}


# =========================================================
# Client handler
# =========================================================
def handle_client(socket_conn, addr):
    db_conn = None
    try:
        raw = socket_conn.recv(16384).decode("utf-8")
        if not raw:
            return

        req = json.loads(raw)
        action = req.get("action")

        db_conn = get_db_connection()

        # -----------------------
        # Action Routing
        # -----------------------
        if action == "login":
            res = handle_login(db_conn, req)

        elif action == "list_items":
            res = handle_list_items(db_conn, req)

        elif action == "list_my_selling_items":
            res = handle_list_my_selling_items(db_conn, req)

        elif action == "place_order":
            res = handle_place_order(db_conn, req)

        elif action == "my_orders":
            res = handle_my_orders(db_conn, req)

        elif action == "orders_to_ship":
            res = handle_orders_to_ship(db_conn, req)

        elif action == "ship_order":
            res = handle_ship_order(db_conn, req)

        elif action == "pending_reviews":
            res = handle_pending_reviews(db_conn, req)

        elif action == "create_review":
            res = handle_create_review(db_conn, req)

        elif action == "add_item":
            res = handle_add_item(db_conn, req)

        # ========== Admin SQL / NoSQL ==========
        elif action in [
            "analytics_category_revenue",
            "analytics_monthly_revenue",
            "analytics_seller_rating",
            "analytics_top_items",
            "nosql_mobile_views",
            "nosql_hot_views",
        ]:
            # ★ Admin 身分驗證（伺服端強制）
            if not check_admin(db_conn, req):
                res = {"status": "fail", "message": "此功能僅限管理員使用"}
            else:
                if action == "analytics_category_revenue":
                    res = analytics_category_revenue(db_conn)
                elif action == "analytics_monthly_revenue":
                    res = analytics_monthly_revenue(db_conn)
                elif action == "analytics_seller_rating":
                    res = analytics_seller_rating(db_conn)
                elif action == "analytics_top_items":
                    res = analytics_top_items(db_conn)
                elif action == "nosql_mobile_views":
                    res = nosql_mobile_views(db_conn)
                elif action == "nosql_hot_views":
                    res = nosql_hot_views(db_conn)

        else:
            res = {"status": "fail", "message": f"未知 action: {action}"}

        socket_conn.send(json.dumps(res, ensure_ascii=False).encode("utf-8"))

    except Exception as e:
        try:
            socket_conn.send(
                json.dumps(
                    {"status": "fail", "message": f"Server error: {e}"},
                    ensure_ascii=False,
                ).encode("utf-8")
            )
        except Exception:
            pass
    finally:
        if db_conn:
            db_conn.close()
        socket_conn.close()


# =========================================================
# Main Server
# =========================================================
def main():
    print(f"[SERVER] Running on {HOST}:{PORT}")
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(5)

    try:
        while True:
            client, addr = s.accept()
            print("[SERVER] Client connected:", addr)
            threading.Thread(
                target=handle_client, args=(client, addr), daemon=True
            ).start()
    finally:
        s.close()


if __name__ == "__main__":
    main()
