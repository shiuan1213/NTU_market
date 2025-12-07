# NTU Marketplace — Database Final Project  
以 PostgreSQL + Python Socket 實作的 NTU 二手交易平台  
第六組｜2024 Fall — NTU 資料庫系統概論

NTU Marketplace 是一個專為台大學生打造的二手交易平台，模擬真實電商流程，包含使用者操作（上架、購買、出貨、評價）、交易管理、併行控制、SQL 後台分析、NoSQL(JSONB) 行為紀錄等。  
本專案完全以 **Python Socket** 與 **PostgreSQL** 實作，不依賴 ORM 或 Web Framework，強調資料庫核心處理。

---

## 🔧 Tech Stack

- **Python 3.10+**
  - 自行實作 Socket TCP Server / Console Client
  - JSON-based command protocol
- **PostgreSQL 14+**
  - Transaction / Row Locking / ACID
  - JSONB NoSQL 行為紀錄
- **psycopg2**
- **ER Model + Schema Design**
- **10+ SQL 查詢功能（含後台分析）**

---

## 📁 Project Structure

project/

│── server.py # 主伺服器程式：處理所有 action (login/order/ship/review/analytics)

│── client.py # 終端機操作選單，可多開終端示範買家/賣家併行

│── db_config.py # PostgreSQL 連線設定

│── schema.sql # 建表指令（10 張主表 + JSONB）

│── seed_data.sql # 初始假資料（users、items、orders、reviews…）

│── extra_orders.sql # 額外補充的大量訂單/評價資料（支援 SQL 分析）

│── nosql_view_logs.sql # JSONB 行為紀錄 table + 測試資料

│── README.md

│── presentation.pdf # 系統展示簡報（影片用）


---

## ✔️ Implemented Features（展示影片操作範圍）

### **1. 登入 Login**
- Email + password_hash 驗證  
- 僅允許 is_verified = TRUE  
- 回傳 user profile（student_no, name, role）

---

### **2. 瀏覽可購買的商品**
- JOIN categories + users  
- 僅顯示 `status='Listed'` 且 `quantity > 0`  
- 自動新增 view_logs（JSONB 行為紀錄）

---

### **3. 購買商品（下單 Transaction + Locking）**
完整 ACID 流程：

1. `SELECT ... FOR UPDATE` 鎖定商品  
2. 檢查庫存、賣家  
3. 建立：
   - orders  
   - order_items（商品快照）  
   - payments（Success）  
4. 扣庫存並更新 item.status  
5. 失敗自動 rollback

---

### **4. 查看我買過的訂單**
- JOIN seller name  
- 顯示狀態：Paid → Shipped → Completed  
- 顯示建立/付款/出貨/完成時間

---

### **5. 賣家查看正在賣的商品**
- 僅顯示 seller 的 item  
- 狀態切換（Listed / SoldOut）

---

### **6. 商品上架（insert item）**
- 手動輸入 title、描述、價格、分類  
- 自動寫入 created_at / updated_at

---

### **7. 賣家查看待出貨訂單**
- orders where `status='Paid'`  
- JOIN buyer name

---

### **8. 賣家出貨**
- 更新 orders.status → Shipped  
- 寫入 shipments  
- 若 shipment 已存在 → ON CONFLICT 更新

---

### **9. 買家評價（review）**
- 只能評 Completed 且未評價的訂單  
- 1–5 星 + 評語  
- 寫入 reviews

---

### **10. SQL 後台分析（Admin Only）**
透過 socket 呼叫 SQL 查詢：

#### ✔ 各分類銷售額 Category Revenue
#### ✔ 每月營收 Monthly Revenue
#### ✔ 賣家平均評價 Seller Rating
#### ✔ 暢銷商品排行 Top 10 Best Sellers

---

### **11. NoSQL 行為紀錄分析（JSONB）**
使用 JSONB metadata 儲存 device / ip / browser…

#### ✔ 查詢手機瀏覽紀錄  
```sql
SELECT * FROM view_logs WHERE metadata->>'device'='mobile';

✔ 熱門瀏覽商品排行（以 title 顯示）

SELECT i.title, COUNT(*) AS views
FROM view_logs v JOIN items i ON v.item_id = i.item_id
GROUP BY i.title ORDER BY views DESC;

📦 Database Schema（共 10+1 張表）
Table	說明
users	學生資料
user_roles	user/admin
categories	大分類 + 子分類（階層 path）
items	商品（庫存、價格、賣家）
item_images	延伸功能
orders	訂單主表
order_items	訂單明細（快照）
payments	付款紀錄
shipments	出貨紀錄
reviews	評價
view_logs(JSONB)	使用者瀏覽行為紀錄

所有表格定義可見於 schema.sql。
🧱 Transaction & Concurrency Control
下單流程使用 PostgreSQL Transaction

確保 ACID：

BEGIN;
SELECT * FROM items WHERE item_id = X FOR UPDATE;
-- 建立訂單 / 扣庫存
COMMIT;

併行控制（避免超賣）

    Row-level Lock

    兩個買家同時買同一商品時，後來者會等待鎖釋放

    100% 避免負庫存

📈 Index Tuning

建立索引於：

items(status, quantity)
orders(buyer_student_no, created_at)
orders(seller_student_no, status)
view_logs(item_id)

🔬 效能測試結果（list_items）
無索引 Avg	有索引 Avg
0.210 秒	0.210 秒

    由於測試資料量小，差異不大；
    但索引可避免系統擴大後查詢退化。

🧪 SQL 分析查詢（Admin）
1. 各分類銷售額

SELECT c.name, SUM(oi.qty * oi.price_each) AS revenue
FROM order_items oi
JOIN items i ON oi.item_id=i.item_id
JOIN categories c ON c.category_id=i.category_id
GROUP BY c.name;

2. 每月營收

SELECT DATE_TRUNC('month', paid_at), SUM(total_amount)
FROM orders
WHERE status='Completed'
GROUP BY 1;

3. 賣家平均評價

SELECT ratee_student_no, AVG(rating), COUNT(*)
FROM reviews GROUP BY ratee_student_no;

4. 暢銷商品 Top10

SELECT item_id, SUM(qty) AS sold
FROM order_items GROUP BY item_id
ORDER BY sold DESC LIMIT 10;

📊 NoSQL JSONB 分析查詢
手機瀏覽紀錄

SELECT * FROM view_logs
WHERE metadata->>'device'='mobile';

熱門瀏覽商品排行（含 title）

SELECT i.title, COUNT(*) AS views
FROM view_logs v JOIN items i ON v.item_id = i.item_id
GROUP BY i.title ORDER BY views DESC LIMIT 10;

▶ How to Run
1. 匯入資料庫

psql -U postgres -d marketplace -f schema.sql
psql -U postgres -d marketplace -f seed_data.sql
psql -U postgres -d marketplace -f extra_orders.sql
psql -U postgres -d marketplace -f nosql_view_logs.sql

2. 啟動伺服器

python server.py

3. 啟動用戶端（可多開）

python client.py

👤 Demo Account（推薦展示）
李雅婷（買家 + 賣家）

Email: b11000004@ntu.edu.tw
Password: hash_04
Name: 李雅婷

推薦示範內容：

    商品上架

    出貨

    評價

    查看訂單更新

🎥 Demo Flow（建議錄影用）

    登入（示範一次失敗 + 成功）

    瀏覽商品

    購買商品（觸發交易流程 + 扣庫存）

    賣家登入 → 查看待出貨 → 出貨

    買家登入 → 查看完成訂單 → 評價

    查看評價寫入

    Admin 登入 → 執行 SQL/NoSQL 分析

📜 License

Educational use only — NTU Database Course 2024 

跟我說一聲即可！

