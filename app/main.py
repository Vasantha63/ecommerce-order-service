from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
from prometheus_client import Counter, Histogram, generate_latest
from fastapi.responses import PlainTextResponse
import sqlite3
import uvicorn

app = FastAPI(title="E-Commerce Order Service")

# Prometheus metrics
request_counter = Counter("order_requests_total", "Total requests", ["method", "endpoint"])

# Database setup
def get_db():
    conn = sqlite3.connect("orders.db")
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    conn.execute("""
        CREATE TABLE IF NOT EXISTS orders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            total_price REAL NOT NULL,
            status TEXT DEFAULT 'pending'
        )
    """)
    conn.execute("INSERT OR IGNORE INTO orders (id, user_id, product_id, quantity, total_price, status) VALUES (1, 1, 1, 2, 100000, 'completed')")
    conn.execute("INSERT OR IGNORE INTO orders (id, user_id, product_id, quantity, total_price, status) VALUES (2, 2, 3, 5, 2500, 'pending')")
    conn.commit()
    conn.close()

init_db()

# Models
class Order(BaseModel):
    user_id: int
    product_id: int
    quantity: int
    total_price: float
    status: Optional[str] = "pending"

# Routes
@app.get("/orders")
def get_orders():
    request_counter.labels(method="GET", endpoint="/orders").inc()
    conn = get_db()
    orders = conn.execute("SELECT * FROM orders").fetchall()
    conn.close()
    return [dict(o) for o in orders]

@app.get("/orders/{order_id}")
def get_order(order_id: int):
    request_counter.labels(method="GET", endpoint="/orders/id").inc()
    conn = get_db()
    order = conn.execute("SELECT * FROM orders WHERE id=?", (order_id,)).fetchone()
    conn.close()
    if not order:
        raise HTTPException(status_code=404, detail="Order not found")
    return dict(order)

@app.post("/orders")
def create_order(order: Order):
    request_counter.labels(method="POST", endpoint="/orders").inc()
    conn = get_db()
    cursor = conn.execute(
        "INSERT INTO orders (user_id, product_id, quantity, total_price, status) VALUES (?, ?, ?, ?, ?)",
        (order.user_id, order.product_id, order.quantity, order.total_price, order.status)
    )
    conn.commit()
    conn.close()
    return {"id": cursor.lastrowid, "message": "Order created!"}

@app.put("/orders/{order_id}")
def update_order(order_id: int, order: Order):
    request_counter.labels(method="PUT", endpoint="/orders/id").inc()
    conn = get_db()
    conn.execute(
        "UPDATE orders SET status=? WHERE id=?",
        (order.status, order_id)
    )
    conn.commit()
    conn.close()
    return {"message": "Order updated!"}

@app.delete("/orders/{order_id}")
def delete_order(order_id: int):
    request_counter.labels(method="DELETE", endpoint="/orders/id").inc()
    conn = get_db()
    conn.execute("DELETE FROM orders WHERE id=?", (order_id,))
    conn.commit()
    conn.close()
    return {"message": "Order deleted!"}

@app.get("/health")
def health():
    return {"status": "healthy", "service": "order-service"}

@app.get("/metrics", response_class=PlainTextResponse)
def metrics():
    return generate_latest()

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8002)