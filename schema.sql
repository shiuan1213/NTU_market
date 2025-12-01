------------------------------------------------------------
-- NTU Marketplace - Schema + Fake Data (FULL EXECUTABLE)
------------------------------------------------------------

------------------------------------------------------------
-- DROP TABLES (依外鍵順序)
------------------------------------------------------------
DROP TABLE IF EXISTS reviews      CASCADE;
DROP TABLE IF EXISTS shipments    CASCADE;
DROP TABLE IF EXISTS payments     CASCADE;
DROP TABLE IF EXISTS order_items  CASCADE;
DROP TABLE IF EXISTS orders       CASCADE;
DROP TABLE IF EXISTS item_images  CASCADE;
DROP TABLE IF EXISTS items        CASCADE;
DROP TABLE IF EXISTS categories   CASCADE;
DROP TABLE IF EXISTS user_roles   CASCADE;
DROP TABLE IF EXISTS users        CASCADE;

------------------------------------------------------------
-- USERS
------------------------------------------------------------
CREATE TABLE users (
    student_no     VARCHAR(20) PRIMARY KEY,
    email          VARCHAR(255) NOT NULL UNIQUE,
    password_hash  VARCHAR(255) NOT NULL,
    full_name      VARCHAR(120) NOT NULL,
    phone          VARCHAR(30),
    is_verified    BOOLEAN NOT NULL DEFAULT FALSE,
    created_at     TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at     TIMESTAMP NOT NULL DEFAULT NOW()
);

------------------------------------------------------------
-- USER ROLES
------------------------------------------------------------
CREATE TABLE user_roles (
    student_no  VARCHAR(20) NOT NULL,
    role        VARCHAR(20) NOT NULL,
    granted_at  TIMESTAMP NOT NULL DEFAULT NOW(),
    PRIMARY KEY (student_no, role),
    FOREIGN KEY (student_no) REFERENCES users(student_no) ON DELETE CASCADE,
    CHECK (role IN ('buyer', 'seller', 'admin'))
);

------------------------------------------------------------
-- CATEGORIES
------------------------------------------------------------
CREATE TABLE categories (
    category_id         SERIAL PRIMARY KEY,
    name                VARCHAR(120) NOT NULL,
    parent_category_id  INTEGER REFERENCES categories(category_id),
    path                VARCHAR(400)
);

------------------------------------------------------------
-- ITEMS
------------------------------------------------------------
CREATE TABLE items (
    item_id            SERIAL PRIMARY KEY,
    seller_student_no  VARCHAR(20) NOT NULL,
    category_id        INTEGER REFERENCES categories(category_id),
    title              VARCHAR(200) NOT NULL,
    description        TEXT,
    condition          VARCHAR(30) NOT NULL,
    quantity           INTEGER NOT NULL DEFAULT 1 CHECK (quantity >= 0),
    price              NUMERIC(12,2) NOT NULL CHECK (price >= 0),
    status             VARCHAR(20) NOT NULL DEFAULT 'Listed',
    created_at         TIMESTAMP NOT NULL DEFAULT NOW(),
    updated_at         TIMESTAMP NOT NULL DEFAULT NOW(),
    FOREIGN KEY (seller_student_no) REFERENCES users(student_no),
    CHECK (condition IN ('new','like-new','good','fair','used')),
    CHECK (status IN ('Draft','Listed','SoldOut','Removed'))
);

------------------------------------------------------------
-- ITEM IMAGES
------------------------------------------------------------
CREATE TABLE item_images (
    image_id    SERIAL PRIMARY KEY,
    item_id     INTEGER NOT NULL REFERENCES items(item_id) ON DELETE CASCADE,
    image_url   VARCHAR(500) NOT NULL,
    sort_order  INTEGER NOT NULL DEFAULT 0
);

------------------------------------------------------------
-- ORDERS
------------------------------------------------------------
CREATE TABLE orders (
    order_id          SERIAL PRIMARY KEY,
    buyer_student_no  VARCHAR(20) NOT NULL,
    seller_student_no VARCHAR(20) NOT NULL,
    order_type        VARCHAR(12) NOT NULL,
    status            VARCHAR(20) NOT NULL DEFAULT 'Created',
    total_amount      NUMERIC(12,2) NOT NULL CHECK (total_amount >= 0),
    consignee_name    VARCHAR(120),
    consignee_phone   VARCHAR(30),
    shipping_address  TEXT,
    created_at        TIMESTAMP NOT NULL DEFAULT NOW(),
    paid_at           TIMESTAMP,
    shipped_at        TIMESTAMP,
    completed_at      TIMESTAMP,
    cancelled_at      TIMESTAMP,
    FOREIGN KEY (buyer_student_no)  REFERENCES users(student_no),
    FOREIGN KEY (seller_student_no) REFERENCES users(student_no),
    CHECK (order_type IN ('direct','auction')),
    CHECK (status IN ('Created','Paid','Shipped','Completed','Cancelled'))
);

------------------------------------------------------------
-- ORDER ITEMS
------------------------------------------------------------
CREATE TABLE order_items (
    order_id       INTEGER NOT NULL,
    item_id        INTEGER NOT NULL,
    qty            INTEGER NOT NULL CHECK (qty > 0),
    price_each     NUMERIC(12,2) NOT NULL CHECK (price_each >= 0),
    title_snapshot VARCHAR(200),
    PRIMARY KEY (order_id, item_id),
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (item_id)  REFERENCES items(item_id)
);

------------------------------------------------------------
-- PAYMENTS
------------------------------------------------------------
CREATE TABLE payments (
    payment_id  SERIAL PRIMARY KEY,
    order_id    INTEGER NOT NULL UNIQUE,
    method      VARCHAR(30) NOT NULL,
    amount      NUMERIC(12,2) NOT NULL CHECK (amount >= 0),
    status      VARCHAR(20) NOT NULL DEFAULT 'Pending',
    txn_ref     VARCHAR(120),
    paid_at     TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE,
    CHECK (status IN ('Pending','Success','Failed','Refunded'))
);

------------------------------------------------------------
-- SHIPMENTS
------------------------------------------------------------
CREATE TABLE shipments (
    shipment_id  SERIAL PRIMARY KEY,
    order_id     INTEGER NOT NULL UNIQUE,
    carrier      VARCHAR(60),
    tracking_no  VARCHAR(80),
    shipped_at   TIMESTAMP,
    delivered_at TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES orders(order_id) ON DELETE CASCADE
);

------------------------------------------------------------
-- REVIEWS
------------------------------------------------------------
CREATE TABLE reviews (
    review_id         SERIAL PRIMARY KEY,
    order_id          INTEGER NOT NULL,
    rater_student_no  VARCHAR(20) NOT NULL,
    ratee_student_no  VARCHAR(20) NOT NULL,
    rating            SMALLINT NOT NULL CHECK (rating BETWEEN 1 AND 5),
    comment           TEXT,
    created_at        TIMESTAMP NOT NULL DEFAULT NOW(),
    FOREIGN KEY (order_id)         REFERENCES orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (rater_student_no) REFERENCES users(student_no),
    FOREIGN KEY (ratee_student_no) REFERENCES users(student_no)
);

------------------------------------------------------------
-- 清空資料
------------------------------------------------------------
TRUNCATE TABLE reviews, shipments, payments, order_items, orders,
               item_images, items, categories, user_roles, users
RESTART IDENTITY CASCADE;

------------------------------------------------------------
-- INSERT USERS
------------------------------------------------------------
INSERT INTO users (student_no, email, password_hash, full_name, phone, is_verified, created_at, updated_at)
VALUES
('B11000001', 'b11000001@ntu.edu.tw', 'hash_01', '林冠宇', '0912-111-001', TRUE, NOW() - INTERVAL '60 days', NOW() - INTERVAL '3 days'),
('B11000002', 'b11000002@ntu.edu.tw', 'hash_02', '陳怡君', '0912-111-002', TRUE, NOW() - INTERVAL '58 days', NOW() - INTERVAL '2 days'),
('B11000003', 'b11000003@ntu.edu.tw', 'hash_03', '張博彥', '0912-111-003', TRUE, NOW() - INTERVAL '55 days', NOW() - INTERVAL '1 days'),
('B11000004', 'b11000004@ntu.edu.tw', 'hash_04', '李雅婷', '0912-111-004', TRUE, NOW() - INTERVAL '50 days', NOW() - INTERVAL '4 days'),
('B11000005', 'b11000005@ntu.edu.tw', 'hash_05', '王俊偉', '0912-111-005', FALSE, NOW() - INTERVAL '45 days', NOW() - INTERVAL '5 days'),
('B11000006', 'b11000006@ntu.edu.tw', 'hash_06', '吳品涵', '0912-111-006', TRUE, NOW() - INTERVAL '40 days', NOW() - INTERVAL '3 days'),
('B11000007', 'b11000007@ntu.edu.tw', 'hash_07', '周伯承', '0912-111-007', TRUE, NOW() - INTERVAL '35 days', NOW() - INTERVAL '2 days'),
('B11000008', 'b11000008@ntu.edu.tw', 'hash_08', '蔡郁庭', '0912-111-008', TRUE, NOW() - INTERVAL '30 days', NOW() - INTERVAL '1 days'),
('B11000009', 'b11000009@ntu.edu.tw', 'hash_09', '許庭瑜', FALSE, NOW() - INTERVAL '25 days', NOW() - INTERVAL '1 days'),
('B11000010', 'b11000010@ntu.edu.tw', 'hash_10', '鄭雅雯', '0912-111-010', TRUE, NOW() - INTERVAL '20 days', NOW());

------------------------------------------------------------
-- USER ROLES
------------------------------------------------------------
INSERT INTO user_roles (student_no, role, granted_at)
VALUES
('B11000001','buyer',NOW()-INTERVAL '60 days'),
('B11000002','buyer',NOW()-INTERVAL '58 days'),
('B11000002','seller',NOW()-INTERVAL '55 days'),
('B11000003','buyer',NOW()-INTERVAL '55 days'),
('B11000003','seller',NOW()-INTERVAL '52 days'),
('B11000004','buyer',NOW()-INTERVAL '50 days'),
('B11000004','seller',NOW()-INTERVAL '48 days'),
('B11000005','buyer',NOW()-INTERVAL '45 days'),
('B11000006','buyer',NOW()-INTERVAL '40 days'),
('B11000006','seller',NOW()-INTERVAL '38 days'),
('B11000007','buyer',NOW()-INTERVAL '35 days'),
('B11000008','buyer',NOW()-INTERVAL '30 days'),
('B11000008','seller',NOW()-INTERVAL '28 days'),
('B11000009','buyer',NOW()-INTERVAL '25 days'),
('B11000010','buyer',NOW()-INTERVAL '20 days'),
('B11000010','admin',NOW()-INTERVAL '15 days');

------------------------------------------------------------
-- CATEGORIES
------------------------------------------------------------
INSERT INTO categories (category_id, name, parent_category_id, path) VALUES
(1,'3C',NULL,'/3C/'),
(2,'Books',NULL,'/Books/'),
(3,'Clothing',NULL,'/Clothing/'),
(4,'Home',NULL,'/Home/'),
(5,'Sport',NULL,'/Sport/');

INSERT INTO categories (category_id, name, parent_category_id, path) VALUES
(6,'Laptops',1,'/3C/Laptops/'),
(7,'Headphones',1,'/3C/Headphones/'),
(8,'Textbooks',2,'/Books/Textbooks/'),
(9,'Jackets',3,'/Clothing/Jackets/'),
(10,'Dorm Items',4,'/Home/Dorm Items/');

------------------------------------------------------------
-- ITEMS
------------------------------------------------------------
INSERT INTO items (item_id, seller_student_no, category_id, title, description, condition, quantity, price, status, created_at, updated_at)
VALUES
(1,'B11000002',6,'MacBook Air 13\" 2020','二手 MacBook Air', 'good',1,23000,'Listed',NOW()-INTERVAL '20 days',NOW()-INTERVAL '5 days'),
(2,'B11000002',7,'Sony WH-1000XM4 耳機','降噪耳機', 'like-new',1,6800,'Listed',NOW()-INTERVAL '18 days',NOW()-INTERVAL '2 days'),
(3,'B11000003',8,'微積分（第7版）','課本', 'good',2,350,'Listed',NOW()-INTERVAL '25 days',NOW()-INTERVAL '10 days'),
(4,'B11000003',8,'普通物理實驗講義','講義', 'fair',1,150,'Listed',NOW()-INTERVAL '23 days',NOW()-INTERVAL '8 days'),
(5,'B11000004',9,'NTU 連帽外套','外套', 'like-new',1,900,'Listed',NOW()-INTERVAL '30 days',NOW()-INTERVAL '7 days'),
(6,'B11000004',3,'灰色帽T','帽T', 'used',1,250,'Listed',NOW()-INTERVAL '15 days',NOW()-INTERVAL '3 days'),
(7,'B11000006',10,'宿舍桌燈','桌燈', 'good',1,400,'Listed',NOW()-INTERVAL '12 days',NOW()-INTERVAL '2 days'),
(8,'B11000006',4,'IKEA 收納盒','收納盒', 'good',3,120,'Listed',NOW()-INTERVAL '10 days',NOW()-INTERVAL '1 days'),
(9,'B11000008',5,'羽毛球拍','球拍','good',1,1500,'Listed',NOW()-INTERVAL '22 days',NOW()-INTERVAL '5 days'),
(10,'B11000008',5,'瑜珈墊','瑜珈墊','like-new',1,500,'Listed',NOW()-INTERVAL '8 days',NOW()-INTERVAL '2 days'),
(11,'B11000003',8,'線性代數課本','課本','good',1,320,'Listed',NOW()-INTERVAL '18 days',NOW()-INTERVAL '5 days'),
(12,'B11000002',6,'二手筆電 ASUS','文書機','fair',1,11000,'Listed',NOW()-INTERVAL '28 days',NOW()-INTERVAL '6 days'),
(13,'B11000006',10,'衣架 20 入','衣架','good',1,100,'Listed',NOW()-INTERVAL '7 days',NOW()-INTERVAL '1 days'),
(14,'B11000004',9,'格紋襯衫','襯衫','used',1,300,'Listed',NOW()-INTERVAL '14 days',NOW()-INTERVAL '3 days'),
(15,'B11000008',5,'護膝','護膝','used',1,200,'Listed',NOW()-INTERVAL '6 days',NOW());

------------------------------------------------------------
-- ITEM IMAGES
------------------------------------------------------------
INSERT INTO item_images (item_id, image_url, sort_order) VALUES
(1,'https://example.com/items/1_1.jpg',0),
(1,'https://example.com/items/1_2.jpg',1),
(2,'https://example.com/items/2_1.jpg',0),
(3,'https://example.com/items/3_1.jpg',0),
(4,'https://example.com/items/4_1.jpg',0),
(5,'https://example.com/items/5_1.jpg',0),
(6,'https://example.com/items/6_1.jpg',0),
(7,'https://example.com/items/7_1.jpg',0),
(8,'https://example.com/items/8_1.jpg',0),
(9,'https://example.com/items/9_1.jpg',0),
(10,'https://example.com/items/10_1.jpg',0),
(11,'https://example.com/items/11_1.jpg',0),
(12,'https://example.com/items/12_1.jpg',0),
(13,'https://example.com/items/13_1.jpg',0),
(14,'https://example.com/items/14_1.jpg',0),
(15,'https://example.com/items/15_1.jpg',0);

------------------------------------------------------------
-- ORDERS
------------------------------------------------------------
INSERT INTO orders (order_id,buyer_student_no,seller_student_no,order_type,status,total_amount,
consignee_name,consignee_phone,shipping_address,created_at,paid_at,shipped_at,completed_at,cancelled_at)
VALUES
(1,'B11000001','B11000002','direct','Completed',23000,'林冠宇','0912-111-001','台北市大安區羅斯福路',NOW()-INTERVAL '19 days',NOW()-INTERVAL '18 days',NOW()-INTERVAL '17 days',NOW()-INTERVAL '15 days',NULL),
(2,'B11000001','B11000003','direct','Completed',350,'林冠宇','0912-111-001','台北市新生南路',NOW()-INTERVAL '17 days',NOW()-INTERVAL '16 days',NOW()-INTERVAL '15 days',NOW()-INTERVAL '13 days',NULL),
(3,'B11000002','B11000004','direct','Shipped',900,'陳怡君','0912-111-002','公館路',NOW()-INTERVAL '10 days',NOW()-INTERVAL '9 days',NOW()-INTERVAL '8 days',NULL,NULL),
(4,'B11000003','B11000004','direct','Paid',250,'張博彥','0912-111-003','辛亥路',NOW()-INTERVAL '7 days',NOW()-INTERVAL '6 days',NULL,NULL,NULL),
(5,'B11000006','B11000006','direct','Completed',400,'吳品涵','0912-111-006','指南路',NOW()-INTERVAL '12 days',NOW()-INTERVAL '11 days',NOW()-INTERVAL '10 days',NOW()-INTERVAL '8 days',NULL),
(6,'B11000007','B11000008','direct','Completed',1500,'周伯承','0912-111-007','南京東路',NOW()-INTERVAL '9 days',NOW()-INTERVAL '8 days',NOW()-INTERVAL '7 days',NOW()-INTERVAL '5 days',NULL),
(7,'B11000008','B11000006','direct','Paid',120,'蔡郁庭','0912-111-008','基河路',NOW()-INTERVAL '5 days',NOW()-INTERVAL '4 days',NULL,NULL,NULL),
(8,'B11000009','B11000008','direct','Cancelled',500,'許庭瑜','0912-111-009','信義路',NOW()-INTERVAL '4 days',NULL,NULL,NULL,NOW()-INTERVAL '2 days');

------------------------------------------------------------
-- ORDER ITEMS
------------------------------------------------------------
INSERT INTO order_items (order_id,item_id,qty,price_each,title_snapshot)
VALUES
(1,1,1,23000,'MacBook Air 13\"'),
(2,3,1,350,'微積分'),
(3,5,1,900,'外套'),
(4,6,1,250,'灰色帽T'),
(5,7,1,400,'桌燈'),
(6,9,1,1500,'球拍'),
(7,8,1,120,'收納盒'),
(8,10,1,500,'瑜珈墊');

------------------------------------------------------------
-- PAYMENTS
------------------------------------------------------------
INSERT INTO payments (payment_id,order_id,method,amount,status,txn_ref,paid_at) VALUES
(1,1,'bank_transfer',23000,'Success','TXN1', (SELECT paid_at FROM orders WHERE order_id=1)),
(2,2,'bank_transfer',350,'Success','TXN2', (SELECT paid_at FROM orders WHERE order_id=2)),
(3,3,'credit_card',900,'Success','TXN3', (SELECT paid_at FROM orders WHERE order_id=3)),
(4,4,'credit_card',250,'Success','TXN4', (SELECT paid_at FROM orders WHERE order_id=4)),
(5,5,'bank_transfer',400,'Success','TXN5', (SELECT paid_at FROM orders WHERE order_id=5)),
(6,6,'bank_transfer',1500,'Success','TXN6', (SELECT paid_at FROM orders WHERE order_id=6)),
(7,7,'credit_card',120,'Pending',NULL,NULL),
(8,8,'credit_card',500,'Refunded','TXN8',NULL);

------------------------------------------------------------
-- SHIPMENTS
------------------------------------------------------------
INSERT INTO shipments (shipment_id,order_id,carrier,tracking_no,shipped_at,delivered_at)
VALUES
(1,1,'7-11','711123456', (SELECT shipped_at FROM orders WHERE order_id=1),
                  (SELECT completed_at FROM orders WHERE order_id=1)),
(2,2,'Familymart','FML987654', (SELECT shipped_at FROM orders WHERE order_id=2),
                  (SELECT completed_at FROM orders WHERE order_id=2)),
(3,3,'Post','POST112233', (SELECT shipped_at FROM orders WHERE order_id=3), NULL),
(4,5,'7-11','711556677', (SELECT shipped_at FROM orders WHERE order_id=5),
                  (SELECT completed_at FROM orders WHERE order_id=5)),
(5,6,'Familymart','FML223344', (SELECT shipped_at FROM orders WHERE order_id=6),
                     (SELECT completed_at FROM orders WHERE order_id=6));

------------------------------------------------------------
-- REVIEWS
------------------------------------------------------------
INSERT INTO reviews (review_id,order_id,rater_student_no,ratee_student_no,rating,comment,created_at)
VALUES
(1,1,'B11000001','B11000002',5,'出貨迅速！',NOW()-INTERVAL '14 days'),
(2,2,'B11000001','B11000003',5,'CP值高。',NOW()-INTERVAL '12 days'),
(3,5,'B11000006','B11000006',4,'符合描述。',NOW()-INTERVAL '7 days'),
(4,6,'B11000007','B11000008',5,'賣家友善。',NOW()-INTERVAL '4 days');


------------------------------------------------------------
-- 修正序列（非常重要）
------------------------------------------------------------

-- items.item_id
SELECT setval('items_item_id_seq', (SELECT COALESCE(MAX(item_id),1) FROM items));

-- item_images.image_id
SELECT setval('item_images_image_id_seq', (SELECT COALESCE(MAX(image_id),1) FROM item_images));

-- orders.order_id
SELECT setval('orders_order_id_seq', (SELECT COALESCE(MAX(order_id),1) FROM orders));

-- payments.payment_id
SELECT setval('payments_payment_id_seq', (SELECT COALESCE(MAX(payment_id),1) FROM payments));

-- shipments.shipment_id
SELECT setval('shipments_shipment_id_seq', (SELECT COALESCE(MAX(shipment_id),1) FROM shipments));

-- reviews.review_id
SELECT setval('reviews_review_id_seq', (SELECT COALESCE(MAX(review_id),1) FROM reviews));
SELECT setval('shipments_shipment_id_seq', (SELECT MAX(shipment_id) FROM shipments));

------------------------------------------------------------
-- 完成
------------------------------------------------------------
