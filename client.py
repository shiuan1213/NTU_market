# ==========================================
# NTU Marketplace - Final Client.py (Fixed Admin)
# ==========================================
import socket
import json

HOST = "127.0.0.1"
PORT = 5000


def send_request(payload: dict) -> dict:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    s.send(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    data = s.recv(16384).decode("utf-8")
    s.close()

    try:
        return json.loads(data)
    except:
        return {"status": "fail", "message": "無法解析伺服器回應"}


# ============================================================
# Login
# ============================================================
def login_flow():
    print("----------------------------------------")
    print(" NTU Marketplace - Login")
    print("----------------------------------------")

    while True:
        email = input("Email: ").strip()
        password = input("Password: ").strip()

        res = send_request({"action": "login", "email": email, "password": password})

        if res.get("status") == "ok":
            print(f"\n登入成功！歡迎 {res['full_name']} ({res['student_no']})")

            return {
                "student_no": res["student_no"],
                "full_name": res["full_name"],
                "email": res["email"],
                "role": res["role"],     # ← 保留 admin 角色
            }

        else:
            print("登入失敗：", res.get("message"))
            if input("再試一次？(y/n): ").lower() != "y":
                return None


# ============================================================
# Main Menu
# ============================================================
def show_main_menu(user):
    print("\n----------------------------------------")
    print(" NTU Marketplace - Main Menu")
    print("----------------------------------------")
    print(f"登入身分：{user['full_name']} ({user['student_no']})")
    print(f"角色：{user['role']}")

    print("[1] 瀏覽可購買商品")
    print("[2] 購買商品")
    print("[3] 查看我買過的訂單")
    print("[4] 查看我正在賣的商品")
    print("[5] 新增商品上架")
    print("[6] （賣家）待出貨訂單")
    print("[7] （賣家）出貨")
    print("[8] （買家）評價訂單")
    print("[9] 登出")

    if user["role"] == "admin":
        print("----------------------------------------")
        print("📊 進階分析功能（Admin）")
        print("[10] SQL 系統分析")
        print("[11] NoSQL 行為紀錄分析（JSONB）")

    return input("\n請輸入選項：")


# ============================================================
# Basic Functions
# ============================================================
def action_list_items(user):
    res = send_request({"action": "list_items"})
    if res["status"] != "ok":
        print("失敗：", res["message"])
        return

    for it in res["items"]:
        print(f"#{it['item_id']} {it['title']} | NT${it['price']} | 庫存 {it['quantity']} | 賣家 {it['seller_name']}")


def action_place_order(user):
    try:
        item_id = int(input("item_id："))
        qty = int(input("數量："))
    except:
        print("格式錯誤")
        return

    res = send_request({
        "action": "place_order",
        "student_no": user["student_no"],
        "item_id": item_id,
        "qty": qty,
    })

    if res.get("status") == "ok":
        print("✅ 下單成功！")
        print(f"訂單編號：{res.get('order_id')}")
        print(f"總金額：NT${res.get('total_amount')}")
    else:
        print("❌ 下單失敗：", res.get("message"))


def action_my_orders(user):
    res = send_request({"action": "my_orders", "student_no": user["student_no"]})
    if res["status"] != "ok":
        print("查詢失敗：", res["message"])
        return

    for o in res["orders"]:
        print(f"訂單#{o['order_id']} | {o['status']} | NT${o['total_amount']} | 賣家 {o['seller_name']}")


def action_my_selling_items(user):
    res = send_request({
        "action": "list_my_selling_items",
        "student_no": user["student_no"]
    })
    if res["status"] != "ok":
        print(res["message"])
        return

    for it in res["items"]:
        print(f"#{it['item_id']} {it['title']} | NT${it['price']} | 狀態 {it['status']}")


def action_add_item(user):
    title = input("標題：")
    description = input("描述：")

    try:
        category_id = int(input("分類 ID："))
        quantity = int(input("數量："))
        price = float(input("價格："))
    except:
        print("格式錯誤")
        return

    condition = input("狀況（new/like-new/good/fair/used）：")

    res = send_request({
        "action": "add_item",
        "student_no": user["student_no"],
        "title": title,
        "description": description,
        "category_id": category_id,
        "condition": condition,
        "quantity": quantity,
        "price": price,
    })
    print(res["message"])


def action_orders_to_ship(user):
    res = send_request({
        "action": "orders_to_ship",
        "student_no": user["student_no"]
    })
    for o in res["orders"]:
        print(f"訂單 #{o['order_id']} | NT${o['total_amount']} | 買家 {o['buyer_name']}")


def action_ship_order(user):
    try:
        order_id = int(input("訂單 ID："))
    except:
        print("格式錯誤")
        return

    carrier = input("物流（預設 7-11）：")
    tracking = input("追蹤碼：")

    res = send_request({
        "action": "ship_order",
        "student_no": user["student_no"],
        "order_id": order_id,
        "carrier": carrier,
        "tracking_no": tracking,
    })
    print(res["message"])


def action_pending_reviews(user):
    res = send_request({
        "action": "pending_reviews",
        "student_no": user["student_no"],
    })

    if not res["orders"]:
        print("沒有可評價的訂單")
        return []

    for o in res["orders"]:
        print(f"訂單 #{o['order_id']} | 賣家 {o['seller_name']} | 完成於 {o['completed_at']}")

    return res["orders"]


def action_create_review(user):
    try:
        order_id = int(input("訂單 ID："))
        rating = int(input("評分 1~5："))
    except:
        print("格式錯誤")
        return

    comment = input("評論：")

    res = send_request({
        "action": "create_review",
        "student_no": user["student_no"],
        "order_id": order_id,
        "rating": rating,
        "comment": comment,
    })
    print(res["message"])


# ============================================================
# SQL Analytics (Admin)
# ============================================================
def sql_menu():
    print("\n=== SQL 系統分析 ===")
    print("[1] 依分類銷售額")
    print("[2] 每月營收")
    print("[3] 賣家平均評價")
    print("[4] 熱門商品")
    print("[0] 返回")
    return input("選項：")


def sql_show(res):
    if res["status"] != "ok":
        print(res["message"])
        return
    for r in res["data"]:
        print(r)


def action_sql_analytics(user):
    while True:
        c = sql_menu()

        if c == "1":
            sql_show(send_request({
                "action": "analytics_category_revenue",
                "student_no": user["student_no"],
                "role": user["role"]
            }))
        elif c == "2":
            sql_show(send_request({
                "action": "analytics_monthly_revenue",
                "student_no": user["student_no"],
                "role": user["role"]
            }))
        elif c == "3":
            sql_show(send_request({
                "action": "analytics_seller_rating",
                "student_no": user["student_no"],
                "role": user["role"]
            }))
        elif c == "4":
            sql_show(send_request({
                "action": "analytics_top_items",
                "student_no": user["student_no"],
                "role": user["role"]
            }))
        elif c == "0":
            return
        else:
            print("無效選項")


# ============================================================
# NoSQL Analytics (Admin)
# ============================================================
def nosql_menu():
    print("\n=== NoSQL 行為紀錄分析 ===")
    print("[1] 手機瀏覽紀錄")
    print("[2] 熱門瀏覽商品 Top10")
    print("[0] 返回")
    return input("選項：")


def action_nosql_analytics(user):
    while True:
        c = nosql_menu()

        if c == "1":
            sql_show(send_request({
                "action": "nosql_mobile_views",
                "student_no": user["student_no"],
                "role": user["role"]
            }))
        elif c == "2":
            sql_show(send_request({
                "action": "nosql_hot_views",
                "student_no": user["student_no"],
                "role": user["role"]
            }))
        elif c == "0":
            return
        else:
            print("無效選項")


# ============================================================
# Main
# ============================================================
def main():
    print("========================================")
    print("   NTU Marketplace Console Client")
    print("========================================")

    user = login_flow()
    if not user:
        return

    while True:
        choice = show_main_menu(user)

        if choice == "1":
            action_list_items(user)
        elif choice == "2":
            action_place_order(user)
        elif choice == "3":
            action_my_orders(user)
        elif choice == "4":
            action_my_selling_items(user)
        elif choice == "5":
            action_add_item(user)
        elif choice == "6":
            action_orders_to_ship(user)
        elif choice == "7":
            action_ship_order(user)
        elif choice == "8":
            if action_pending_reviews(user):
                action_create_review(user)
        elif choice == "9":
            print("已登出，再見！")
            break

        # Admin only
        elif choice == "10" and user["role"] == "admin":
            action_sql_analytics(user)
        elif choice == "11" and user["role"] == "admin":
            action_nosql_analytics(user)
        else:
            print("無效選項。")


if __name__ == "__main__":
    main()
