from fastapi import APIRouter, Body, HTTPException

from models.api import QueryRequest, QueryResponse
from datastore.datastore import datastore

query_router = APIRouter()

@query_router.post(
    "/query",
    response_model=QueryResponse,
    description="Accepts search query objects with query and optional filter. Break down complex questions into sub-questions. Refine results by criteria, e.g. time / source, don't do this often. Split queries if ResponseTooLargeError occurs.",
)
async def query(
    request: QueryRequest = Body(...),
):
    try:
        results = await datastore.query(
            request.queries,
        )
        return QueryResponse(results=results)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")
