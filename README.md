NTU Marketplace — Database Final Project

一個以 PostgreSQL + Python Socket 實作的 NTU 二手交易平台。
本系統實作包含 登入、瀏覽商品、下單購買、賣家出貨、買家評價、商品上架 等功能，並以真實資料庫交易流程模擬完整電商平台。
🔧 Tech Stack

    Python（Socket TCP Server / Console Client）

    PostgreSQL 14+

    psycopg2

    JSONB（模擬 NoSQL 類型資料）

    ER Model + 資料字典 + 10+ SQL 查詢功能

📁 Project Structure

project/
│── server.py          # 主伺服器程式（處理所有指令）
│── client.py          # 終端機用戶端（操作選單）
│── db_config.py       # PostgreSQL 連線設定
│── schema.sql         # 建表指令（10 張資料表）
│── seed_data.sql      # 假資料（users / items / orders...）
│── nosql_view_logs.sql # JSONB 行為紀錄 NoSQL 資料表
│── README.md

✔️ Implemented Features（展示影片操作範圍）
1. 登入 Login

    使用 email + password_hash

    僅允許 is_verified = TRUE 的帳號登入

2. 瀏覽可購買的商品

    JOIN categories, users

    僅顯示 status = 'Listed' 且有庫存

3. 購買商品（下單）

    檢查庫存、狀態、賣家

    自動建立：

        orders

        order_items

        payments（Success）

    自動扣庫存、上架狀態更新

4. 查看我買過的訂單

    使用 JOIN 查賣家名字

    依時間排序

5. 賣家查看正在賣的商品
6. 商品上架（insert item）
7. 賣家查看待出貨訂單（Paid）
8. 賣家出貨

    更新 order status → Shipped

    建立 shipment（ON CONFLICT 更新）

9. 買家對完成訂單留下評價

    僅 Completed 且未評價的訂單允許新增 review

📦 Database Schema（共 10 張表）

    users

    user_roles

    categories

    items

    item_images

    orders

    order_items

    payments

    shipments

    reviews

所有 schema 已包含在 schema.sql。
📝 Usage — 如何執行
1. 匯入 schema + 假資料

psql -U postgres -d marketplace -f schema.sql
psql -U postgres -d marketplace -f seed_data.sql

2. 啟動 Server

python server.py

3. 啟動 Client（另開一個 Terminal）

python client.py

👤 Demo Account（建議展示用）
買家 + 賣家功能完整

Email: b11000004@ntu.edu.tw
Password: hash_04
Name: 李雅婷 (B11000004)

可示範：

    賣家上架商品

    賣家出貨

    買家評價

🧪 Demo Flow（展示影片腳本可用）

    使用李雅婷登入

    查看可購買商品

    購買任意商品

    切換到賣家功能查看待出貨訂單

    執行「出貨」

    回到買家選單 → 完成訂單 → 評價

    查看賣家端商品狀態/訂單狀態更新

🧰 NoSQL（如未展示可刪）

我們使用 PostgreSQL JSONB 建立 view_logs 紀錄瀏覽紀錄：

CREATE TABLE view_logs (
    id BIGSERIAL PRIMARY KEY,
    student_no VARCHAR(20),
    item_id INTEGER,
    viewed_at TIMESTAMP DEFAULT NOW(),
    metadata JSONB
);

示範查詢：

SELECT * FROM view_logs
WHERE metadata->>'device' = 'mobile';

📜 License

Educational use only（2024 NTU Database Course）