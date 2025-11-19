import os
from datetime import datetime, timezone
from typing import List, Optional

from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from database import db, create_document, get_documents
from schemas import DailyItem

app = FastAPI(title="Daily Planner API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def read_root():
    return {"message": "Daily Planner Backend Running"}


@app.get("/test")
def test_database():
    response = {
        "backend": "✅ Running",
        "database": "❌ Not Available",
        "database_url": None,
        "database_name": None,
        "connection_status": "Not Connected",
        "collections": []
    }

    try:
        if db is not None:
            response["database"] = "✅ Available"
            response["database_url"] = "✅ Configured"
            response["database_name"] = db.name if hasattr(db, 'name') else "✅ Connected"
            response["connection_status"] = "Connected"

            try:
                collections = db.list_collection_names()
                response["collections"] = collections[:10]
                response["database"] = "✅ Connected & Working"
            except Exception as e:
                response["database"] = f"⚠️  Connected but Error: {str(e)[:50]}"
        else:
            response["database"] = "⚠️  Available but not initialized"

    except Exception as e:
        response["database"] = f"❌ Error: {str(e)[:50]}"

    # Check environment variables
    response["database_url"] = "✅ Set" if os.getenv("DATABASE_URL") else "❌ Not Set"
    response["database_name"] = "✅ Set" if os.getenv("DATABASE_NAME") else "❌ Not Set"

    return response


# Models for requests
class DailyItemCreate(DailyItem):
    pass


class DailyItemOut(DailyItem):
    id: str


@app.post("/items", response_model=dict)
def create_item(payload: DailyItemCreate):
    try:
        item_id = create_document("dailyitem", payload)
        return {"id": item_id}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/items", response_model=List[dict])
def list_items(
    day: Optional[str] = Query(None, description="YYYY-MM-DD to filter by date"),
    include_completed: bool = Query(True)
):
    try:
        filter_dict = {}
        if day:
            # Match by date field string comparison; database stores date as datetime.date via pydantic -> dict
            filter_dict["day"] = datetime.fromisoformat(day).date()
        if not include_completed:
            filter_dict["completed"] = False
        docs = get_documents("dailyitem", filter_dict)
        # Convert ObjectId and datetime to strings
        def serialize(doc):
            doc["id"] = str(doc.pop("_id"))
            for k, v in list(doc.items()):
                if isinstance(v, (datetime,)):
                    doc[k] = v.astimezone(timezone.utc).isoformat()
            # date and time fields may be datetime.date/time, convert to isoformat strings
            if "day" in doc and hasattr(doc["day"], "isoformat"):
                doc["day"] = doc["day"].isoformat()
            for key in ["start_time", "end_time"]:
                if key in doc and hasattr(doc[key], "isoformat"):
                    doc[key] = doc[key].isoformat()
            return doc
        return [serialize(d) for d in docs]
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/items/upcoming", response_model=List[dict])
def upcoming_notifications(limit: int = 20):
    try:
        now = datetime.now(timezone.utc)
        # Find items with notify_at >= now and not yet notified
        docs = db["dailyitem"].find({
            "notify_at": {"$gte": now},
            "notified": False
        }).sort("notify_at", 1).limit(limit)
        result = []
        for d in docs:
            d["id"] = str(d.pop("_id"))
            if d.get("notify_at"):
                d["notify_at"] = d["notify_at"].astimezone(timezone.utc).isoformat()
            if d.get("day") and hasattr(d["day"], "isoformat"):
                d["day"] = d["day"].isoformat()
            for key in ["start_time", "end_time"]:
                if key in d and hasattr(d[key], "isoformat"):
                    d[key] = d[key].isoformat()
            result.append(d)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/items/{item_id}/complete", response_model=dict)
def mark_complete(item_id: str):
    try:
        from bson import ObjectId
        res = db["dailyitem"].update_one({"_id": ObjectId(item_id)}, {"$set": {"completed": True, "updated_at": datetime.now(timezone.utc)}})
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="Item not found")
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/items/{item_id}/notified", response_model=dict)
def mark_notified(item_id: str):
    try:
        from bson import ObjectId
        res = db["dailyitem"].update_one({"_id": ObjectId(item_id)}, {"$set": {"notified": True, "updated_at": datetime.now(timezone.utc)}})
        if res.matched_count == 0:
            raise HTTPException(status_code=404, detail="Item not found")
        return {"status": "ok"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
