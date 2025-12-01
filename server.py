# server.py
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


def get_db_connection():
    """每個連線開一個新的 DB connection。"""
    conn = psycopg2.connect(**DB_CONFIG)
    return conn


def serialize_value(v):
    """把 datetime / Decimal 轉成 JSON 可以吃的型別。"""
    if isinstance(v, datetime):
        return v.isoformat(sep=" ", timespec="seconds")
    if isinstance(v, Decimal):
        return float(v)
    return v


# =====================
# Login
# =====================
def handle_login(conn, req):
    email = req.get("email")
    password = req.get("password")

    with conn.cursor(cursor_factory=RealDictCursor) as cur:
        cur.execute(
            """
            SELECT student_no, full_name, email
            FROM users
            WHERE email = %s
              AND password_hash = %s
              AND is_verified = TRUE
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
        }
    else:
        return {"status": "fail", "message": "Email 或密碼錯誤，或帳號尚未驗證。"}


# =====================
# 買家/訪客：瀏覽商品
# =====================
def handle_list_items(conn, req):
    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT i.item_id,
                   i.title,
                   i.price,
                   i.condition,
                   i.quantity,
                   c.name AS category_name,
                   u.full_name AS seller_name
            FROM items AS i
            LEFT JOIN categories AS c ON i.category_id = c.category_id
            JOIN users AS u ON i.seller_student_no = u.student_no
            WHERE i.status = 'Listed'
              AND i.quantity > 0
            ORDER BY i.item_id
            """
        )
        rows = cur.fetchall()

    items = []
    for r in rows:
        item = {
            "item_id": r[0],
            "title": r[1],
            "price": float(r[2]),
            "condition": r[3],
            "quantity": r[4],
            "category_name": r[5],
            "seller_name": r[6],
        }
        items.append(item)

    return {"status": "ok", "items": items}


# =====================
# 賣家：查看自己上架的商品
# =====================
def handle_list_my_selling_items(conn, req):
    student_no = req.get("student_no")

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT item_id, title, price, quantity, status
            FROM items
            WHERE seller_student_no = %s
            ORDER BY item_id
            """,
            (student_no,),
        )
        rows = cur.fetchall()

    items = []
    for r in rows:
        items.append(
            {
                "item_id": r[0],
                "title": r[1],
                "price": float(r[2]),
                "quantity": r[3],
                "status": r[4],
            }
        )

    return {"status": "ok", "items": items}


# =====================
# 下單（直接購買）
# =====================
def handle_place_order(conn, req):
    """
    建立一筆 direct order：
    - 檢查商品是否存在 / 上架 / 庫存足夠
    - 建立 orders
    - 建立 order_items
    - 建立 payments (Success)
    - 更新 items.quantity 與 status
    """
    buyer_no = req.get("student_no")
    item_id = req.get("item_id")
    qty = req.get("qty")

    if not isinstance(qty, int) or qty <= 0:
        return {"status": "fail", "message": "數量必須為正整數。"}

    try:
        with conn:
            with conn.cursor() as cur:
                # 1. 鎖定商品
                cur.execute(
                    """
                    SELECT seller_student_no, price, quantity, status
                    FROM items
                    WHERE item_id = %s
                    FOR UPDATE
                    """,
                    (item_id,),
                )
                row = cur.fetchone()
                if not row:
                    return {"status": "fail", "message": "找不到此商品。"}

                seller_no, price, stock, status = row
                if status != "Listed" or stock <= 0:
                    return {"status": "fail", "message": "商品已下架或無庫存。"}

                if stock < qty:
                    return {
                        "status": "fail",
                        "message": f"庫存不足，剩餘 {stock} 件。",
                    }

                total_amount = price * qty

                # 2. 建立訂單（直接視為已付款）
                cur.execute(
                    """
                    INSERT INTO orders (
                        buyer_student_no, seller_student_no,
                        order_type, status, total_amount,
                        consignee_name, consignee_phone, shipping_address,
                        created_at, paid_at
                    )
                    SELECT %s, %s,
                           'direct', 'Paid', %s,
                           full_name, phone, '校內面交',
                           NOW(), NOW()
                    FROM users
                    WHERE student_no = %s
                    RETURNING order_id
                    """,
                    (buyer_no, seller_no, total_amount, buyer_no),
                )
                order_id = cur.fetchone()[0]

                # 3. 建立 order_items
                cur.execute(
                    """
                    INSERT INTO order_items (order_id, item_id, qty, price_each, title_snapshot)
                    SELECT %s, i.item_id, %s, i.price, i.title
                    FROM items AS i
                    WHERE i.item_id = %s
                    """,
                    (order_id, qty, item_id),
                )

                # 4. 建立 payment（Success）
                cur.execute(
                    """
                    INSERT INTO payments (order_id, method, amount, status, txn_ref, paid_at)
                    VALUES (%s, 'credit_card', %s, 'Success', %s, NOW())
                    """,
                    (order_id, total_amount, f"TXN-{order_id:06d}"),
                )

                # 5. 更新庫存
                new_stock = stock - qty
                new_status = "SoldOut" if new_stock == 0 else "Listed"
                cur.execute(
                    """
                    UPDATE items
                    SET quantity = %s,
                        status = %s,
                        updated_at = NOW()
                    WHERE item_id = %s
                    """,
                    (new_stock, new_status, item_id),
                )

        return {
            "status": "ok",
            "message": f"下單成功！訂單編號 {order_id}，總金額 {total_amount}.",
            "order_id": order_id,
            "total_amount": float(total_amount),
        }

    except Exception as e:
        return {"status": "fail", "message": f"下單失敗：{e}"}


# =====================
# 買家：查看自己的訂單
# =====================
def handle_my_orders(conn, req):
    student_no = req.get("student_no")

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT o.order_id,
                   o.status,
                   o.total_amount,
                   o.created_at,
                   o.paid_at,
                   o.shipped_at,
                   o.completed_at,
                   u.full_name AS seller_name
            FROM orders AS o
            JOIN users AS u ON u.student_no = o.seller_student_no
            WHERE o.buyer_student_no = %s
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
                "created_at": serialize_value(r[3]),
                "paid_at": serialize_value(r[4]) if r[4] else None,
                "shipped_at": serialize_value(r[5]) if r[5] else None,
                "completed_at": serialize_value(r[6]) if r[6] else None,
                "seller_name": r[7],
            }
        )

    return {"status": "ok", "orders": orders}


# =====================
# 賣家：查看待出貨訂單（Paid）
# =====================
def handle_orders_to_ship(conn, req):
    """賣家查看需要出貨的訂單（狀態 = Paid）。"""
    seller_no = req.get("student_no")

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT o.order_id,
                   o.total_amount,
                   o.created_at,
                   u.full_name AS buyer_name
            FROM orders AS o
            JOIN users AS u ON u.student_no = o.buyer_student_no
            WHERE o.seller_student_no = %s
              AND o.status = 'Paid'
            ORDER BY o.created_at
            """,
            (seller_no,),
        )
        rows = cur.fetchall()

    orders = []
    for r in rows:
        orders.append(
            {
                "order_id": r[0],
                "total_amount": float(r[1]),
                "created_at": serialize_value(r[2]),
                "buyer_name": r[3],
            }
        )

    return {"status": "ok", "orders": orders}


# =====================
# 賣家：出貨（改成 Shipped + 新增/更新 shipment）
# =====================
def handle_ship_order(conn, req):
    """賣家將訂單標記為 Shipped，建立 shipment。"""
    seller_no = req.get("student_no")
    order_id = req.get("order_id")
    carrier = req.get("carrier") or "7-11"
    tracking_no = req.get("tracking_no") or f"PKG-{int(order_id):06d}"

    try:
        with conn:
            with conn.cursor() as cur:
                # 檢查訂單是否存在且狀態為 Paid，且屬於此賣家
                cur.execute(
                    """
                    SELECT status, seller_student_no
                    FROM orders
                    WHERE order_id = %s
                    """,
                    (order_id,),
                )
                row = cur.fetchone()
                if not row:
                    return {"status": "fail", "message": "找不到此訂單。"}

                status, db_seller = row
                if db_seller != seller_no:
                    return {"status": "fail", "message": "此訂單不屬於你。"}
                if status != "Paid":
                    return {
                        "status": "fail",
                        "message": f"訂單狀態不是 Paid，而是 {status}。",
                    }

                # 更新訂單狀態
                cur.execute(
                    """
                    UPDATE orders
                    SET status = 'Shipped',
                        shipped_at = NOW()
                    WHERE order_id = %s
                    """,
                    (order_id,),
                )

                # 建立或更新 shipment
                cur.execute(
                    """
                    INSERT INTO shipments (order_id, carrier, tracking_no, shipped_at)
                    VALUES (%s, %s, %s, NOW())
                    ON CONFLICT (order_id) DO UPDATE
                    SET carrier = EXCLUDED.carrier,
                        tracking_no = EXCLUDED.tracking_no,
                        shipped_at = EXCLUDED.shipped_at
                    """,
                    (order_id, carrier, tracking_no),
                )

        return {"status": "ok", "message": "已更新為 Shipped 並建立出貨紀錄。"}

    except Exception as e:
        return {"status": "fail", "message": f"出貨失敗：{e}"}


# =====================
# 買家：查看尚未評價的訂單
# =====================
def handle_pending_reviews(conn, req):
    """買家查看可以評價但尚未評價的訂單（Completed 且還沒有 review）。"""
    buyer_no = req.get("student_no")

    with conn.cursor() as cur:
        cur.execute(
            """
            SELECT o.order_id,
                   o.completed_at,
                   u.full_name AS seller_name
            FROM orders AS o
            JOIN users AS u ON u.student_no = o.seller_student_no
            WHERE o.buyer_student_no = %s
              AND o.status = 'Completed'
              AND NOT EXISTS (
                    SELECT 1
                    FROM reviews r
                    WHERE r.order_id = o.order_id
                      AND r.rater_student_no = o.buyer_student_no
              )
            ORDER BY o.completed_at DESC
            """,
            (buyer_no,),
        )
        rows = cur.fetchall()

    orders = []
    for r in rows:
        orders.append(
            {
                "order_id": r[0],
                "completed_at": serialize_value(r[1]),
                "seller_name": r[2],
            }
        )

    return {"status": "ok", "orders": orders}


# =====================
# 買家：新增評價
# =====================
def handle_create_review(conn, req):
    buyer_no = req.get("student_no")
    order_id = req.get("order_id")
    rating = req.get("rating")
    comment = req.get("comment", "")

    try:
        rating = int(rating)
    except Exception:
        return {"status": "fail", "message": "評分必須為 1~5 的整數。"}

    if not (1 <= rating <= 5):
        return {"status": "fail", "message": "評分必須介於 1~5。"}

    try:
        with conn:
            with conn.cursor() as cur:
                # 查訂單資訊
                cur.execute(
                    """
                    SELECT buyer_student_no, seller_student_no, status
                    FROM orders
                    WHERE order_id = %s
                    """,
                    (order_id,),
                )
                row = cur.fetchone()
                if not row:
                    return {"status": "fail", "message": "找不到此訂單。"}

                buyer_db, seller_db, status = row
                if buyer_db != buyer_no:
                    return {"status": "fail", "message": "這不是你的訂單。"}
                if status != "Completed":
                    return {"status": "fail", "message": "訂單尚未完成，不能評價。"}

                # 檢查是否已評價
                cur.execute(
                    """
                    SELECT 1
                    FROM reviews
                    WHERE order_id = %s
                      AND rater_student_no = %s
                    """,
                    (order_id, buyer_no),
                )
                if cur.fetchone():
                    return {"status": "fail", "message": "你已經對此訂單留下評價。"}

                # 建立評價
                cur.execute(
                    """
                    INSERT INTO reviews (
                        order_id, rater_student_no, ratee_student_no,
                        rating, comment, created_at
                    )
                    VALUES (%s, %s, %s, %s, %s, NOW())
                    """,
                    (order_id, buyer_no, seller_db, rating, comment),
                )

        return {"status": "ok", "message": "評價已送出，謝謝你的回饋！"}

    except Exception as e:
        return {"status": "fail", "message": f"建立評價失敗：{e}"}


# =====================
# 賣家：新增商品
# =====================
def handle_add_item(conn, req):
    """賣家新增商品。"""
    seller_no = req.get("student_no")
    title = req.get("title")
    description = req.get("description") or ""
    category_id = req.get("category_id")
    condition = req.get("condition")
    quantity = req.get("quantity")
    price = req.get("price")

    if condition not in ("new", "like-new", "good", "fair", "used"):
        return {"status": "fail", "message": "condition 不合法。"}

    try:
        quantity = int(quantity)
        price = float(price)
    except Exception:
        return {"status": "fail", "message": "數量與價格必須為數字。"}

    if quantity <= 0 or price < 0:
        return {"status": "fail", "message": "數量與價格必須為正。"}

    try:
        with conn:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO items (
                        seller_student_no, category_id,
                        title, description,
                        condition, quantity, price,
                        status, created_at, updated_at
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s,
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

        return {
            "status": "ok",
            "message": f"商品已上架！item_id={item_id}",
            "item_id": item_id,
        }

    except Exception as e:
        return {"status": "fail", "message": f"新增商品失敗：{e}"}


# =====================
# Client handler
# =====================
def handle_client(conn_socket, addr):
    db_conn = None
    try:
        data = conn_socket.recv(8192).decode("utf-8")
        if not data:
            return

        req = json.loads(data)
        action = req.get("action")

        db_conn = get_db_connection()

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
        else:
            res = {"status": "fail", "message": f"Unknown action: {action}"}

        conn_socket.send(json.dumps(res, ensure_ascii=False).encode("utf-8"))

    except Exception as e:
        err = {"status": "fail", "message": f"Server error: {e}"}
        try:
            conn_socket.send(json.dumps(err, ensure_ascii=False).encode("utf-8"))
        except Exception:
            pass
    finally:
        if db_conn is not None:
            try:
                db_conn.close()
            except Exception:
                pass
        conn_socket.close()


def main():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    # 避免重啟時遇到 Address already in use
    s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    s.bind((HOST, PORT))
    s.listen(5)
    print(f"[SERVER] NTU Marketplace server running on {HOST}:{PORT}")

    try:
        while True:
            client_socket, addr = s.accept()
            print(f"[SERVER] Client connected from {addr}")
            t = threading.Thread(target=handle_client, args=(client_socket, addr))
            t.daemon = True
            t.start()
    finally:
        s.close()


if __name__ == "__main__":
    main()
