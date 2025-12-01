# client.py
import socket
import json

HOST = "127.0.0.1"
PORT = 5000


def send_request(payload: dict) -> dict:
    """送 request 給 server，拿回 JSON。"""
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((HOST, PORT))
    s.send(json.dumps(payload, ensure_ascii=False).encode("utf-8"))
    data = s.recv(8192).decode("utf-8")
    s.close()
    try:
        return json.loads(data)
    except Exception:
        return {"status": "fail", "message": "無法解析伺服器回應。"}


# ========== 登入流程 ==========

def login_flow():
    print("----------------------------------------")
    print(" NTU Marketplace - Login")
    print("----------------------------------------")
    while True:
        email = input("Email: ").strip()
        password = input("Password: ").strip()

        req = {"action": "login", "email": email, "password": password}
        res = send_request(req)

        if res.get("status") == "ok":
            print(f"\n登入成功！歡迎 {res['full_name']} ({res['student_no']})")
            return {
                "student_no": res["student_no"],
                "full_name": res["full_name"],
                "email": res["email"],
            }
        else:
            print("\n登入失敗：", res.get("message", "未知錯誤"))
            retry = input("要再試一次嗎？(y/n) ").strip().lower()
            if retry != "y":
                return None


# ========== 選單功能 ==========

def show_main_menu(user):
    print("\n----------------------------------------")
    print(" NTU Marketplace - Main Menu")
    print("----------------------------------------")
    print(f"目前登入：{user['full_name']} ({user['student_no']})")
    print("[1] 瀏覽可購買的商品")
    print("[2] 購買商品（建立訂單）")
    print("[3] 查看我買過的訂單")
    print("[4] 查看我正在賣的商品")
    print("[5] 新增商品上架")
    print("[6] （賣家）查看待出貨訂單")
    print("[7] （賣家）出貨")
    print("[8] （買家）對完成訂單留下評價")
    print("[9] 登出")
    print("----------------------------------------")
    choice = input("請輸入選項：").strip()
    return choice


def action_list_items(user):
    res = send_request({"action": "list_items"})
    if res.get("status") != "ok":
        print("查詢失敗：", res.get("message"))
        return

    items = res.get("items", [])
    if not items:
        print("目前沒有可購買的商品。")
        return

    print("\n=== 可購買商品列表 ===")
    for it in items:
        print(
            f"#{it['item_id']}: {it['title']} | NT${it['price']} | 狀況: {it['condition']} | "
            f"庫存: {it['quantity']} | 類別: {it['category_name']} | 賣家: {it['seller_name']}"
        )


def action_place_order(user):
    try:
        item_id = int(input("請輸入要購買的 item_id：").strip())
        qty = int(input("請輸入購買數量：").strip())
    except ValueError:
        print("輸入格式錯誤，請輸入數字。")
        return

    confirm = input(f"確認要購買 item {item_id}，數量 {qty} 嗎？(y/n) ").strip().lower()
    if confirm != "y":
        print("已取消下單。")
        return

    req = {
        "action": "place_order",
        "student_no": user["student_no"],
        "item_id": item_id,
        "qty": qty,
    }
    res = send_request(req)
    if res.get("status") == "ok":
        print("✅", res.get("message"))
    else:
        print("❌ 下單失敗：", res.get("message"))


def action_my_orders(user):
    req = {"action": "my_orders", "student_no": user["student_no"]}
    res = send_request(req)
    if res.get("status") != "ok":
        print("查詢失敗：", res.get("message"))
        return

    orders = res.get("orders", [])
    if not orders:
        print("你目前還沒有任何訂單。")
        return

    print("\n=== 我買過的訂單 ===")
    for o in orders:
        print(
            f"訂單 #{o['order_id']} | 賣家: {o['seller_name']} | "
            f"金額: NT${o['total_amount']} | 狀態: {o['status']} | 建立時間: {o['created_at']}"
        )


def action_my_selling_items(user):
    req = {"action": "list_my_selling_items", "student_no": user["student_no"]}
    res = send_request(req)
    if res.get("status") != "ok":
        print("查詢失敗：", res.get("message"))
        return

    items = res.get("items", [])
    if not items:
        print("你目前沒有上架任何商品。")
        return

    print("\n=== 我正在賣的商品 ===")
    for it in items:
        print(
            f"#{it['item_id']} {it['title']} | NT${it['price']} | "
            f"庫存: {it['quantity']} | 狀態: {it['status']}"
        )


def action_add_item(user):
    print("\n=== 新增商品上架 ===")
    title = input("商品標題：").strip()
    description = input("商品描述：").strip()

    try:
        category_id = int(
            input("分類 ID（例如 6=Laptops, 8=Textbooks...）：").strip()
        )
        quantity = int(input("數量：").strip())
        price = float(input("價格：").strip())
    except ValueError:
        print("輸入格式錯誤，請重新操作。")
        return

    print("狀況請輸入：new / like-new / good / fair / used")
    condition = input("商品狀況：").strip()

    req = {
        "action": "add_item",
        "student_no": user["student_no"],
        "title": title,
        "description": description,
        "category_id": category_id,
        "condition": condition,
        "quantity": quantity,
        "price": price,
    }

    res = send_request(req)
    if res.get("status") == "ok":
        print("✅", res.get("message"))
    else:
        print("❌ 上架失敗：", res.get("message"))


def action_orders_to_ship(user):
    req = {"action": "orders_to_ship", "student_no": user["student_no"]}
    res = send_request(req)
    if res.get("status") != "ok":
        print("查詢失敗：", res.get("message"))
        return

    orders = res.get("orders", [])
    if not orders:
        print("目前沒有需要出貨的訂單（狀態 Paid）。")
        return

    print("\n=== 待出貨訂單 ===")
    for o in orders:
        print(
            f"訂單 #{o['order_id']} | 買家: {o['buyer_name']} | "
            f"金額: NT${o['total_amount']} | 建立時間: {o['created_at']}"
        )


def action_ship_order(user):
    try:
        order_id = int(input("請輸入要出貨的訂單編號：").strip())
    except ValueError:
        print("請輸入數字訂單編號。")
        return

    carrier = input("物流業者（預設 7-11）：").strip()
    tracking_no = input("追蹤碼（若空白會自動產生）：").strip()

    req = {
        "action": "ship_order",
        "student_no": user["student_no"],
        "order_id": order_id,
        "carrier": carrier or None,
        "tracking_no": tracking_no or None,
    }

    res = send_request(req)
    if res.get("status") == "ok":
        print("✅", res.get("message"))
    else:
        print("❌ 出貨失敗：", res.get("message"))


def action_pending_reviews(user):
    """
    回傳可評價訂單列表，讓 main 決定要不要進一步呼叫 action_create_review。
    """
    req = {"action": "pending_reviews", "student_no": user["student_no"]}
    res = send_request(req)
    if res.get("status") != "ok":
        print("查詢失敗：", res.get("message"))
        return []

    orders = res.get("orders", [])
    if not orders:
        print("目前沒有可以評價的訂單。")
        return []

    print("\n=== 可評價訂單 ===")
    for o in orders:
        print(
            f"訂單 #{o['order_id']} | 賣家: {o['seller_name']} | 完成時間: {o['completed_at']}"
        )

    return orders


def action_create_review(user):
    try:
        order_id = int(input("請輸入要評價的訂單編號：").strip())
        rating = int(input("請輸入星等（1~5）：").strip())
    except ValueError:
        print("請輸入正確的數字格式。")
        return

    comment = input("請輸入評語（可空白）：").strip()

    req = {
        "action": "create_review",
        "student_no": user["student_no"],
        "order_id": order_id,
        "rating": rating,
        "comment": comment,
    }

    res = send_request(req)
    if res.get("status") == "ok":
        print("✅", res.get("message"))
    else:
        print("❌ 評價失敗：", res.get("message"))


# ========== 主程式 ==========

def main():
    print("========================================")
    print("   NTU Marketplace Console Client")
    print("========================================")

    user = login_flow()
    if not user:
        print("未登入，系統結束。")
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
            orders = action_pending_reviews(user)
            if orders:
                action_create_review(user)
        elif choice == "9":
            print("已登出，系統結束。")
            break
        else:
            print("無效的選項，請重新輸入。")


if __name__ == "__main__":
    main()
