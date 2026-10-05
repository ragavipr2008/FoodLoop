from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
import sqlite3
from pathlib import Path
from datetime import datetime, timedelta
import re

app = Flask(__name__)
app.secret_key = "foodloop-hackathon-secret"

BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "foodloop.db"


def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db():
    conn = get_db()
    conn.executescript("""
        CREATE TABLE IF NOT EXISTS food_listings (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            food_name TEXT NOT NULL,
            category TEXT NOT NULL,
            description TEXT,
            total_quantity INTEGER NOT NULL,
            available_quantity INTEGER NOT NULL,
            pickup_location TEXT NOT NULL,
            pickup_deadline TEXT NOT NULL,
            provider_name TEXT NOT NULL,
            image_url TEXT,
            status TEXT NOT NULL DEFAULT 'Available',
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS claims (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            food_id INTEGER NOT NULL,
            recipient_name TEXT NOT NULL,
            quantity INTEGER NOT NULL,
            status TEXT NOT NULL DEFAULT 'Claimed',
            claimed_at TEXT NOT NULL,
            FOREIGN KEY (food_id) REFERENCES food_listings(id)
        );
    """)

    count = conn.execute("SELECT COUNT(*) AS count FROM food_listings").fetchone()["count"]
    if count == 0:
        now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        sample = [
            (
                "Vegetable Biryani", "Meals",
                "Fresh surplus biryani from a college event.",
                50, 50, "College Canteen", "Today 8:00 PM",
                "Campus Food Team",
                "https://images.unsplash.com/photo-1563379091339-03246963d96c?auto=format&fit=crop&w=900&q=80",
                "Available", now
            ),
            (
                "Idli & Sambar", "Breakfast",
                "Surplus breakfast portions available for pickup.",
                30, 30, "Main Block Cafeteria", "Today 5:00 PM",
                "College Cafeteria",
                "https://images.unsplash.com/photo-1589301760014-d929f3979dbc?auto=format&fit=crop&w=900&q=80",
                "Available", now
            ),
            (
                "Fruit Packets", "Fruits",
                "Packed fresh fruits from a student event.",
                20, 20, "Seminar Hall", "Today 6:30 PM",
                "Event Volunteers",
                "https://images.unsplash.com/photo-1619566636858-adf3ef46400b?auto=format&fit=crop&w=900&q=80",
                "Available", now
            ),
            (
                "Veg Sandwiches", "Snacks",
                "Individually packed sandwiches from a workshop.",
                18, 18, "Innovation Lab", "Today 4:30 PM",
                "Student Volunteers",
                "https://images.unsplash.com/photo-1521390188846-e2a3a97453a0?auto=format&fit=crop&w=900&q=80",
                "Available", now
            )
        ]
        conn.executemany("""
            INSERT INTO food_listings
            (food_name, category, description, total_quantity, available_quantity,
             pickup_location, pickup_deadline, provider_name, image_url, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, sample)
    conn.commit()
    conn.close()


def urgency_info(deadline):
    """Hackathon-friendly heuristic urgency engine; no external API required."""
    text = (deadline or "").lower()
    score = 55

    if "today" in text:
        score += 20
    if "urgent" in text:
        score += 15
    if "tomorrow" in text:
        score -= 20

    # Understand common '4:30 PM' / '8:00 PM' strings.
    match = re.search(r'(\d{1,2})(?::(\d{2}))?\s*(am|pm)', text)
    if match:
        hour = int(match.group(1))
        minute = int(match.group(2) or 0)
        meridiem = match.group(3)
        if meridiem == "pm" and hour != 12:
            hour += 12
        if meridiem == "am" and hour == 12:
            hour = 0

        now = datetime.now()
        target = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
        if target < now and "today" in text:
            minutes_left = 0
        else:
            minutes_left = max(0, int((target - now).total_seconds() / 60))

        if "today" in text:
            if minutes_left <= 60:
                score += 25
            elif minutes_left <= 180:
                score += 15
            elif minutes_left <= 360:
                score += 8
    score = max(0, min(100, score))

    if score >= 85:
        label = "Critical"
    elif score >= 70:
        label = "High"
    elif score >= 50:
        label = "Medium"
    else:
        label = "Low"

    return score, label


def smart_score(food, desired_category="", desired_quantity=0, desired_location=""):
    """Transparent weighted SmartMatch score for demo purposes."""
    score = 0
    reasons = []

    category = (food["category"] or "").lower()
    desired_category = (desired_category or "").lower()
    location = (food["pickup_location"] or "").lower()
    desired_location = (desired_location or "").lower()

    if desired_category:
        if category == desired_category:
            score += 45
            reasons.append("Category match")
        elif desired_category in category or category in desired_category:
            score += 25
            reasons.append("Related category")
    else:
        score += 20

    if desired_quantity:
        if food["available_quantity"] >= desired_quantity:
            score += 30
            reasons.append("Enough quantity")
        else:
            score += 8
            reasons.append("Partial quantity")

    if desired_location:
        if desired_location in location or location in desired_location:
            score += 15
            reasons.append("Location match")
        else:
            score += 4
    else:
        score += 8

    urgency, label = urgency_info(food["pickup_deadline"])
    # More urgent food gets a small priority boost so it can be rescued sooner.
    score += round(urgency * 0.10)
    if urgency >= 70:
        reasons.append(f"{label} rescue priority")

    score = min(100, score)
    return score, reasons, urgency, label


@app.context_processor
def inject_globals():
    return {"current_year": datetime.now().year}


@app.route("/")
def index():
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM food_listings
        WHERE available_quantity > 0
        ORDER BY id DESC
    """).fetchall()

    stats = {
        "listings": conn.execute("SELECT COUNT(*) AS n FROM food_listings").fetchone()["n"],
        "available": conn.execute("SELECT COALESCE(SUM(available_quantity),0) AS n FROM food_listings").fetchone()["n"],
        "claimed": conn.execute("SELECT COALESCE(SUM(quantity),0) AS n FROM claims").fetchone()["n"],
        "picked_up": conn.execute("SELECT COALESCE(SUM(quantity),0) AS n FROM claims WHERE status='Picked Up'").fetchone()["n"],
    }
    conn.close()

    enriched = []
    for row in rows[:6]:
        item = dict(row)
        item["urgency_score"], item["urgency_label"] = urgency_info(item["pickup_deadline"])
        enriched.append(item)

    return render_template("index.html", stats=stats, latest=enriched)


@app.route("/add-food", methods=["GET", "POST"])
def add_food():
    if request.method == "POST":
        data = request.form
        required = ["food_name", "category", "quantity", "pickup_location", "pickup_deadline", "provider_name"]
        if not all(data.get(x, "").strip() for x in required):
            flash("Please fill in all required fields.", "error")
            return render_template("add_food.html")

        try:
            quantity = int(data.get("quantity", "0"))
            if quantity <= 0:
                raise ValueError
        except ValueError:
            flash("Quantity must be a positive whole number.", "error")
            return render_template("add_food.html")

        conn = get_db()
        conn.execute("""
            INSERT INTO food_listings
            (food_name, category, description, total_quantity, available_quantity,
             pickup_location, pickup_deadline, provider_name, image_url, status, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'Available', ?)
        """, (
            data["food_name"].strip(), data["category"].strip(),
            data.get("description", "").strip(), quantity, quantity,
            data["pickup_location"].strip(), data["pickup_deadline"].strip(),
            data["provider_name"].strip(), data.get("image_url", "").strip(),
            datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        ))
        conn.commit()
        conn.close()
        flash("Food listing published. SmartMatch is now evaluating it.", "success")
        return redirect(url_for("foods"))

    return render_template("add_food.html")


@app.route("/foods")
def foods():
    search = request.args.get("search", "").strip()
    category = request.args.get("category", "").strip()

    conn = get_db()
    query = "SELECT * FROM food_listings WHERE available_quantity > 0"
    params = []

    if search:
        query += " AND (food_name LIKE ? OR pickup_location LIKE ? OR description LIKE ? OR provider_name LIKE ?)"
        like = f"%{search}%"
        params.extend([like, like, like, like])

    if category:
        query += " AND category = ?"
        params.append(category)

    query += " ORDER BY id DESC"
    raw = conn.execute(query, params).fetchall()
    categories = conn.execute("SELECT DISTINCT category FROM food_listings ORDER BY category").fetchall()
    conn.close()

    listings = []
    for row in raw:
        item = dict(row)
        item["urgency_score"], item["urgency_label"] = urgency_info(item["pickup_deadline"])
        item["smart_score"], item["match_reasons"], _, _ = smart_score(item)
        listings.append(item)

    # Rescue-first ordering: urgent food first, then SmartMatch score.
    listings.sort(key=lambda x: (x["urgency_score"], x["smart_score"]), reverse=True)

    return render_template(
        "foods.html",
        listings=listings,
        categories=categories,
        search=search,
        selected_category=category
    )


@app.route("/claim/<int:food_id>", methods=["GET", "POST"])
def claim(food_id):
    conn = get_db()
    food = conn.execute("SELECT * FROM food_listings WHERE id = ?", (food_id,)).fetchone()

    if not food:
        conn.close()
        flash("Food listing not found.", "error")
        return redirect(url_for("foods"))

    if request.method == "POST":
        recipient = request.form.get("recipient_name", "").strip()
        try:
            quantity = int(request.form.get("quantity", "0"))
        except ValueError:
            quantity = 0

        if not recipient:
            flash("Please enter your name or organization.", "error")
        elif quantity <= 0:
            flash("Enter a valid quantity.", "error")
        elif quantity > food["available_quantity"]:
            flash(f"Only {food['available_quantity']} portions are available.", "error")
        else:
            new_available = food["available_quantity"] - quantity
            new_status = "Fully Claimed" if new_available == 0 else "Available"

            conn.execute("""
                INSERT INTO claims (food_id, recipient_name, quantity, status, claimed_at)
                VALUES (?, ?, ?, 'Claimed', ?)
            """, (food_id, recipient, quantity, datetime.now().strftime("%Y-%m-%d %H:%M:%S")))

            conn.execute("""
                UPDATE food_listings SET available_quantity=?, status=? WHERE id=?
            """, (new_available, new_status, food_id))
            conn.commit()
            conn.close()

            flash(f"Claim confirmed: {quantity} portion(s) of {food['food_name']}.", "success")
            return redirect(url_for("dashboard"))

    urgency_score, urgency_label = urgency_info(food["pickup_deadline"])
    conn.close()
    return render_template(
        "claim.html",
        food=food,
        urgency_score=urgency_score,
        urgency_label=urgency_label
    )


@app.route("/smart-match")
def smart_match():
    category = request.args.get("category", "").strip()
    location = request.args.get("location", "").strip()
    try:
        quantity = int(request.args.get("quantity", "0") or 0)
    except ValueError:
        quantity = 0

    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM food_listings
        WHERE available_quantity > 0
        ORDER BY id DESC
    """).fetchall()
    categories = conn.execute("SELECT DISTINCT category FROM food_listings ORDER BY category").fetchall()
    conn.close()

    results = []
    for row in rows:
        score, reasons, urgency, label = smart_score(row, category, quantity, location)
        item = dict(row)
        item.update({
            "smart_score": score,
            "match_reasons": reasons,
            "urgency_score": urgency,
            "urgency_label": label
        })
        results.append(item)

    results.sort(key=lambda x: (x["smart_score"], x["urgency_score"]), reverse=True)

    return render_template(
        "smart_match.html",
        results=results,
        categories=categories,
        selected_category=category,
        selected_location=location,
        selected_quantity=quantity
    )


@app.route("/dashboard")
def dashboard():
    conn = get_db()

    total_listed = conn.execute("SELECT COALESCE(SUM(total_quantity),0) AS n FROM food_listings").fetchone()["n"]
    available = conn.execute("SELECT COALESCE(SUM(available_quantity),0) AS n FROM food_listings").fetchone()["n"]
    claimed = conn.execute("SELECT COALESCE(SUM(quantity),0) AS n FROM claims").fetchone()["n"]
    picked_up = conn.execute("SELECT COALESCE(SUM(quantity),0) AS n FROM claims WHERE status='Picked Up'").fetchone()["n"]
    listings_count = conn.execute("SELECT COUNT(*) AS n FROM food_listings").fetchone()["n"]
    claims_count = conn.execute("SELECT COUNT(*) AS n FROM claims").fetchone()["n"]

    recent_claims = conn.execute("""
        SELECT claims.*, food_listings.food_name, food_listings.pickup_location
        FROM claims JOIN food_listings ON claims.food_id = food_listings.id
        ORDER BY claims.id DESC LIMIT 10
    """).fetchall()

    category_stats = conn.execute("""
        SELECT food_listings.category, COALESCE(SUM(claims.quantity),0) AS total
        FROM claims JOIN food_listings ON claims.food_id = food_listings.id
        GROUP BY food_listings.category ORDER BY total DESC
    """).fetchall()

    urgent_count = 0
    urgent_items = []
    all_available = conn.execute("""
        SELECT * FROM food_listings WHERE available_quantity > 0
    """).fetchall()
    conn.close()

    for row in all_available:
        score, label = urgency_info(row["pickup_deadline"])
        if score >= 70:
            urgent_count += 1
            urgent_items.append({
                "food_name": row["food_name"],
                "available_quantity": row["available_quantity"],
                "pickup_location": row["pickup_location"],
                "pickup_deadline": row["pickup_deadline"],
                "urgency_score": score,
                "urgency_label": label,
                "id": row["id"]
            })

    urgent_items.sort(key=lambda x: x["urgency_score"], reverse=True)

    rescue_rate = round((claimed / total_listed) * 100, 1) if total_listed else 0
    pickup_rate = round((picked_up / claimed) * 100, 1) if claimed else 0
    estimated_meals = claimed
    estimated_co2 = round(claimed * 0.5, 1)  # demo impact metric; label as estimate.

    return render_template(
        "dashboard.html",
        total_listed=total_listed,
        available=available,
        claimed=claimed,
        picked_up=picked_up,
        listings_count=listings_count,
        claims_count=claims_count,
        recent_claims=recent_claims,
        category_stats=category_stats,
        urgent_count=urgent_count,
        urgent_items=urgent_items[:5],
        rescue_rate=rescue_rate,
        pickup_rate=pickup_rate,
        estimated_meals=estimated_meals,
        estimated_co2=estimated_co2
    )


@app.post("/claim/<int:claim_id>/pickup")
def pickup_claim(claim_id):
    conn = get_db()
    claim = conn.execute("SELECT * FROM claims WHERE id=?", (claim_id,)).fetchone()

    if not claim:
        conn.close()
        flash("Claim not found.", "error")
        return redirect(url_for("dashboard"))

    conn.execute("UPDATE claims SET status='Picked Up' WHERE id=?", (claim_id,))
    conn.commit()
    conn.close()
    flash("Pickup marked as completed. Impact dashboard updated.", "success")
    return redirect(url_for("dashboard"))


@app.route("/api/stats")
def api_stats():
    conn = get_db()
    data = {
        "food_rescued": conn.execute("SELECT COALESCE(SUM(quantity),0) AS n FROM claims").fetchone()["n"],
        "food_available": conn.execute("SELECT COALESCE(SUM(available_quantity),0) AS n FROM food_listings").fetchone()["n"],
        "claims": conn.execute("SELECT COUNT(*) AS n FROM claims").fetchone()["n"],
        "listings": conn.execute("SELECT COUNT(*) AS n FROM food_listings").fetchone()["n"]
    }
    conn.close()
    return jsonify(data)


if __name__ == "__main__":
    init_db()
    app.run(debug=True)
