# FoodLoop — Smart Hackathon Edition

FoodLoop is a Flask + SQLite surplus food rescue platform designed for the FoodLoop hackathon problem statement.

## What was added

### SmartMatch Engine
A transparent, no-API-key matching engine ranks listings using:
- food category compatibility
- required quantity vs available quantity
- preferred location
- rescue urgency

The UI displays the score and the reasons behind the recommendation, which is useful for a hackathon demo because judges can understand how the "AI" decision was made.

### Urgency Engine
The prototype parses common deadline text such as:
- Today 4:30 PM
- Today 8:00 PM
- Tomorrow

It generates a rescue score and labels listings:
- Critical
- High
- Medium
- Low

### Impact Dashboard
Includes:
- portions rescued
- portions picked up
- urgent rescue queue
- rescue rate
- pickup completion
- food-category breakdown
- estimated impact metric

The environmental number is explicitly marked as a prototype estimate and should be replaced by a verified methodology for production.

### New UI
- modern responsive landing page
- SmartMatch page
- rescue-first food cards
- polished dashboard
- urgency badges
- match score rings
- animated progress bars
- mobile layout

## Run

### Windows

```bash
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
python app.py
```

Open:

http://127.0.0.1:5000

### macOS/Linux

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python app.py
```

## Demo flow

1. Home → show SmartMatch and live impact numbers.
2. Donate → create a listing with a near deadline.
3. Find Food → show urgency-first sorting.
4. SmartMatch → select category + quantity + location.
5. Show the ranked recommendation and reasons.
6. Rescue Food → claim a quantity.
7. Dashboard → show the quantity change and rescue metrics.
8. Mark Picked Up → show the pickup completion update.

## Important
The SmartMatch feature is an explainable scoring engine, not a call to a third-party AI API. This means the project runs offline and needs no API key.
