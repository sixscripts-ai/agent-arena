import json

from appwrite.query import Query
from fastapi import APIRouter, Depends

from . import db
from .auth import get_current_user

router = APIRouter(prefix="/formats", tags=["formats"])


@router.get("")
def list_formats(_user_id: str = Depends(get_current_user)):
    databases = db.get_databases()
    res = databases.list_documents(db.get_database_id(), "formats", queries=[Query.limit(100)])
    out = []
    for doc in res.documents:
        cfg = json.loads(doc.data["config"])
        out.append({
            "id": doc.id,
            "name": cfg["name"],
            "engine": cfg["engine"],
            "description": cfg["description"],
            "slug": cfg["id"],
        })
    out.sort(key=lambda f: f["name"])
    return out
