import sqlite3
from contextlib import contextmanager
from datetime import datetime
from config import DB_PATH


@contextmanager
def db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    with db() as c:
        c.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY, username TEXT, full_name TEXT,
            balance REAL NOT NULL DEFAULT 0, language TEXT DEFAULT 'uz',
            created_at TEXT NOT NULL, last_seen TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS admins (user_id INTEGER PRIMARY KEY, added_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS channels (chat_id TEXT PRIMARY KEY, title TEXT, username TEXT, added_at TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL, service_id INTEGER,
            service_name TEXT, link TEXT, quantity INTEGER, amount REAL, remote_id TEXT,
            status TEXT DEFAULT 'Pending', created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS settings (key TEXT PRIMARY KEY, value TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS products (
            code TEXT PRIMARY KEY, title TEXT NOT NULL, description TEXT DEFAULT '',
            price REAL NOT NULL, active INTEGER NOT NULL DEFAULT 1, updated_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS deposits (
            id INTEGER PRIMARY KEY AUTOINCREMENT, user_id INTEGER NOT NULL,
            amount REAL NOT NULL, method TEXT NOT NULL, status TEXT NOT NULL DEFAULT 'pending',
            provider_id TEXT, payer_info TEXT, created_at TEXT NOT NULL, paid_at TEXT
        );
        """)
        for statement in (
            "ALTER TABLE users ADD COLUMN referrer_id INTEGER",
            "ALTER TABLE users ADD COLUMN referral_earned REAL NOT NULL DEFAULT 0",
            "ALTER TABLE deposits ADD COLUMN payer_info TEXT",
        ):
            try:
                c.execute(statement)
            except sqlite3.OperationalError:
                pass
        defaults = [
            ("stars_50", "⭐ 50", "Telegram Stars", 9695),
            ("stars_75", "⭐ 75", "Telegram Stars", 14543),
            ("stars_100", "⭐ 100", "Telegram Stars", 19390),
            ("stars_150", "⭐ 150", "Telegram Stars", 29085),
            ("stars_200", "⭐ 200", "Telegram Stars", 38780),
            ("stars_250", "⭐ 250", "Telegram Stars", 48475),
            ("stars_300", "⭐ 300", "Telegram Stars", 58170),
            ("stars_500", "⭐ 500", "Telegram Stars", 96950),
            ("stars_1000", "⭐ 1000", "Telegram Stars", 193900),
            ("stars_2000", "⭐ 2000", "Telegram Stars", 387800),
            ("stars_3000", "⭐ 3000", "Telegram Stars", 581700),
            ("premium_3", "👑 3 oy — Premium", "Premium obuna", 145000),
            ("premium_6", "👑 6 oy — Premium", "Premium obuna", 195000),
            ("premium_12", "👑 12 oy — Premium", "Premium obuna", 349900),
            ("uc_30", "💎 30 UC", "PUBG Mobile UC", 6900),
            ("uc_60", "💎 60 UC", "PUBG Mobile UC", 11690),
            ("uc_120", "💎 120 UC", "PUBG Mobile UC", 25800),
            ("uc_180", "💎 180 UC", "PUBG Mobile UC", 37900),
            ("uc_325", "💎 325 UC", "PUBG Mobile UC", 58990),
            ("uc_660", "💎 660 UC", "PUBG Mobile UC", 113990),
            ("uc_1320", "💎 1320 UC", "PUBG Mobile UC", 249000),
        ]
        c.executemany("INSERT OR IGNORE INTO products(code,title,description,price,updated_at) VALUES(?,?,?,?,?)", [(*p, now()) for p in defaults])


def now():
    return datetime.utcnow().isoformat(timespec="seconds")


def is_admin(user_id: int) -> bool:
    from config import OWNER_ID
    with db() as c:
        return user_id == OWNER_ID or c.execute("SELECT 1 FROM admins WHERE user_id=?", (user_id,)).fetchone() is not None


def ensure_user(user):
    with db() as c:
        c.execute("""INSERT INTO users(id, username, full_name, created_at, last_seen)
        VALUES(?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET username=excluded.username,
        full_name=excluded.full_name, last_seen=excluded.last_seen""",
                  (user.id, user.username, user.full_name, now(), now()))


def set_referrer(user_id, referrer_id):
    if user_id == referrer_id:
        return
    with db() as c:
        row = c.execute("SELECT referrer_id FROM users WHERE id=?", (user_id,)).fetchone()
        if row and row["referrer_id"] is None:
            c.execute("UPDATE users SET referrer_id=? WHERE id=?", (referrer_id, user_id))


def referral_stats(user_id):
    with db() as c:
        count = c.execute("SELECT COUNT(*) n FROM users WHERE referrer_id=?", (user_id,)).fetchone()["n"]
        earned = c.execute("SELECT referral_earned FROM users WHERE id=?", (user_id,)).fetchone()
        return count, (earned["referral_earned"] if earned else 0)


def get_user(user_id):
    with db() as c:
        return c.execute("SELECT * FROM users WHERE id=?", (user_id,)).fetchone()


def list_users():
    with db() as c:
        return c.execute("SELECT * FROM users ORDER BY id").fetchall()


def get_stats():
    with db() as c:
        return {
            "users": c.execute("SELECT COUNT(*) n FROM users").fetchone()["n"],
            "orders": c.execute("SELECT COUNT(*) n FROM orders").fetchone()["n"],
            "revenue": c.execute("SELECT COALESCE(SUM(amount),0) n FROM orders").fetchone()["n"],
            "balance": c.execute("SELECT COALESCE(SUM(balance),0) n FROM users").fetchone()["n"],
        }


def change_balance(user_id, amount):
    with db() as c:
        row = c.execute("SELECT balance FROM users WHERE id=?", (user_id,)).fetchone()
        if not row or row["balance"] + amount < 0:
            return None
        c.execute("UPDATE users SET balance=balance+? WHERE id=?", (amount, user_id))
        return row["balance"] + amount


def create_order(user_id, service, link, quantity, amount, remote_id):
    with db() as c:
        cur = c.execute("""INSERT INTO orders(user_id,service_id,service_name,link,quantity,amount,remote_id,created_at)
        VALUES(?,?,?,?,?,?,?,?)""", (user_id, service["service"], service["name"], link, quantity, amount, str(remote_id), now()))
        return cur.lastrowid


def user_orders(user_id):
    with db() as c:
        return c.execute("SELECT * FROM orders WHERE user_id=? ORDER BY id DESC LIMIT 10", (user_id,)).fetchall()


def create_product_order(user_id, product):
    with db() as c:
        user = c.execute("SELECT balance FROM users WHERE id=?", (user_id,)).fetchone()
        if not user or user['balance'] < product['price']:
            return None
        cur = c.execute("""INSERT INTO orders(user_id,service_id,service_name,link,quantity,amount,remote_id,status,created_at)
        VALUES(?,?,?,?,?,?,?,?,?)""", (user_id, None, product['title'], '', 1, product['price'], 'product:' + product['code'], 'Pending', now()))
        return cur.lastrowid


def get_order(order_id):
    with db() as c:
        return c.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()


def complete_product_order(order_id):
    with db() as c:
        row = c.execute("SELECT * FROM orders WHERE id=? AND status='Pending' AND remote_id LIKE 'product:%'", (order_id,)).fetchone()
        if not row:
            return None
        user = c.execute("SELECT balance FROM users WHERE id=?", (row['user_id'],)).fetchone()
        if not user or user['balance'] < row['amount']:
            return "INSUFFICIENT_BALANCE"
        c.execute("UPDATE users SET balance=balance-? WHERE id=?", (row['amount'], row['user_id']))
        c.execute("UPDATE orders SET status='Completed' WHERE id=?", (order_id,))
        return row


def cancel_product_order(order_id):
    with db() as c:
        row = c.execute("SELECT * FROM orders WHERE id=? AND status='Pending' AND remote_id LIKE 'product:%'", (order_id,)).fetchone()
        if not row:
            return None
        c.execute("UPDATE orders SET status='Cancelled' WHERE id=?", (order_id,))
        return row


def add_admin(user_id):
    with db() as c:
        c.execute("INSERT OR IGNORE INTO admins(user_id, added_at) VALUES(?,?)", (user_id, now()))


def remove_admin(user_id):
    with db() as c:
        c.execute("DELETE FROM admins WHERE user_id=?", (user_id,))


def list_admins():
    with db() as c:
        return c.execute("SELECT user_id, added_at FROM admins ORDER BY added_at").fetchall()


def add_channel(chat_id, title, username):
    with db() as c:
        c.execute("INSERT OR REPLACE INTO channels(chat_id,title,username,added_at) VALUES(?,?,?,?)", (chat_id,title,username,now()))


def remove_channel(chat_id):
    with db() as c:
        c.execute("DELETE FROM channels WHERE chat_id=?", (chat_id,))


def list_channels():
    with db() as c:
        return c.execute("SELECT * FROM channels ORDER BY added_at").fetchall()


def products(prefix=None):
    with db() as c:
        if prefix:
            return c.execute("SELECT * FROM products WHERE code LIKE ? AND active=1 ORDER BY rowid", (prefix + '%',)).fetchall()
        return c.execute("SELECT * FROM products ORDER BY rowid").fetchall()


def get_product(code):
    with db() as c:
        return c.execute("SELECT * FROM products WHERE code=?", (code,)).fetchone()


def set_product_price(code, price):
    with db() as c:
        c.execute("UPDATE products SET price=?, updated_at=? WHERE code=?", (price, now(), code))


def update_product(code, title=None, description=None, price=None):
    with db() as c:
        row = c.execute("SELECT * FROM products WHERE code=?", (code,)).fetchone()
        if not row:
            return False
        c.execute("UPDATE products SET title=?, description=?, price=?, updated_at=? WHERE code=?", (title if title is not None else row['title'], description if description is not None else row['description'], price if price is not None else row['price'], now(), code))
        return True


def add_product(code, title, price, description=''):
    with db() as c:
        c.execute("INSERT OR REPLACE INTO products(code,title,description,price,active,updated_at) VALUES(?,?,?,?,1,?)", (code,title,description,price,now()))


def delete_product(code):
    with db() as c:
        c.execute("DELETE FROM products WHERE code=?", (code,))


def get_setting(key, default=''):
    with db() as c:
        row = c.execute("SELECT value FROM settings WHERE key=?", (key,)).fetchone()
        return row["value"] if row else default


def set_setting(key, value):
    with db() as c:
        c.execute("INSERT OR REPLACE INTO settings(key,value) VALUES(?,?)", (key, str(value)))


def create_deposit(user_id, amount, method, provider_id=''):
    with db() as c:
        cur = c.execute("INSERT INTO deposits(user_id,amount,method,provider_id,created_at) VALUES(?,?,?,?,?)", (user_id, amount, method, provider_id, now()))
        return cur.lastrowid


def set_deposit_payer(deposit_id, payer_info):
    with db() as c:
        c.execute("UPDATE deposits SET payer_info=? WHERE id=?", (payer_info, deposit_id))


def get_deposit(deposit_id):
    with db() as c:
        return c.execute("SELECT * FROM deposits WHERE id=?", (deposit_id,)).fetchone()


def complete_deposit(deposit_id, provider_id=''):
    with db() as c:
        row = c.execute("SELECT * FROM deposits WHERE id=? AND status='pending'", (deposit_id,)).fetchone()
        if not row:
            return None
        c.execute("UPDATE deposits SET status='paid', provider_id=COALESCE(NULLIF(?,''),provider_id), paid_at=? WHERE id=?", (provider_id, now(), deposit_id))
        c.execute("UPDATE users SET balance=balance+? WHERE id=?", (row['amount'], row['user_id']))
        return row


def complete_deposit_amount(deposit_id, amount):
    with db() as c:
        row = c.execute("SELECT * FROM deposits WHERE id=? AND status='pending'", (deposit_id,)).fetchone()
        if not row or amount <= 0:
            return None
        c.execute("UPDATE deposits SET status='partial', paid_at=? WHERE id=?", (now(), deposit_id))
        c.execute("UPDATE users SET balance=balance+? WHERE id=?", (amount, row['user_id']))
        return row


def fail_deposit(deposit_id):
    with db() as c:
        row = c.execute("SELECT * FROM deposits WHERE id=? AND status='pending'", (deposit_id,)).fetchone()
        if row:
            c.execute("UPDATE deposits SET status='failed', paid_at=? WHERE id=?", (now(), deposit_id))
        return row
