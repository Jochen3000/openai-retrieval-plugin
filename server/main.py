import uvicorn
import os
from fastapi import FastAPI, File, HTTPException, Body, UploadFile, Form
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from pymongo import MongoClient
import certifi

from models.api import (
    DeleteRequest,
    DeleteResponse,
    QueryRequest,
    QueryResponse,
    UpsertRequest,
    UpsertResponse,
)
from datastore.datastore import get_datastore
from services.file import get_document_from_file

from .query_router import query_router  
from .prompt_router import prompt_router

# Connect to mongodb
connection_string = os.getenv('MONGO_DB_URL')
db_client = MongoClient(connection_string, tlsCAFile=certifi.where())
db = db_client['podojo_metadata']

app = FastAPI()
app.mount("/.well-known", StaticFiles(directory=".well-known"), name="static")

#cors
cors_origins_str1 = os.getenv('CORS_ORIGINS_1')
cors_origins_str2 = os.getenv('CORS_ORIGINS_2')
cors_origins_str3 = os.getenv('CORS_ORIGINS_3') 

origins = [origin for origin in [cors_origins_str1, cors_origins_str2, cors_origins_str3] if origin]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(query_router, prefix="/sub") 
app.include_router(prompt_router)

# Create a sub-application, in order to access just the query endpoints
sub_app = FastAPI(
    title="Retrieval Plugin API",
    description="A retrieval API for querying and filtering documents based on natural language queries and metadata",
    version="1.0.0",
    servers=[{"url": "https://openai-retrieval-plugin.onrender.com"}],
)
app.mount("/sub", sub_app)

# upload document
@app.post(
    "/upsert-file",
    response_model=UpsertResponse,
)
async def upsert_file(
    file: UploadFile = File(...),
    document_id: str = Form(...),
    author: str = Form(None),
    timestamp: str = Form(None), 
    source: str = Form(None), 
    source_id: str = Form(None),  
    groups: str = Form(None), 
    chunking_strategy: str = Form("tokens"), #lines for interviews, tokens otherwise
):
    document = await get_document_from_file(file, document_id, source, author, source_id)
    metadata_collection = db[source]

    try:
        ids = await datastore.upsert([document], chunking_strategy=chunking_strategy)  # pass the strategy to upsert
        await upsert_metadata(metadata_collection, document, author, timestamp, source_id, groups)
        return UpsertResponse(ids=ids)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail=f"str({e})")

# upsert metadata to mongodb
async def upsert_metadata(metadata_collection, document, author, timestamp, source_id, groups):  # Receive the additional values
    metadata = {
        "id": document.id,
        "author": author,
        "timestamp": timestamp,
        "source_id": source_id,
        "groups": groups,
    }

    result = metadata_collection.replace_one({"id": document.id}, metadata, upsert=True)
    return result

@app.post(
    "/upsert",
    response_model=UpsertResponse,
)
async def upsert(
    request: UpsertRequest = Body(...),
):
    try:
        ids = await datastore.upsert(request.documents)
        return UpsertResponse(ids=ids)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


@app.post(
    "/query",
    response_model=QueryResponse,
)
async def query_main(
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


@sub_app.post(
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


@app.delete(
    "/delete",
    response_model=DeleteResponse,
)
async def delete(
    request: DeleteRequest = Body(...),
):
    if not (request.ids or request.filter or request.delete_all):
        raise HTTPException(
            status_code=400,
            detail="One of ids, filter, or delete_all is required",
        )
    try:
        success = await datastore.delete(
            ids=request.ids,
            filter=request.filter,
            delete_all=request.delete_all,
        )

        if request.ids:
            for document_id in request.ids:
                await delete_metadata(request.filter.source, document_id)
        elif request.filter and request.filter.document_id:
            await delete_metadata(request.filter.source, request.filter.document_id)

        return DeleteResponse(success=success)
    except Exception as e:
        print("Error:", e)
        raise HTTPException(status_code=500, detail="Internal Service Error")


async def delete_metadata(source: str, document_id: str):
    metadata_collection = db[source]
    result = metadata_collection.delete_one({"id": document_id})
    return result.deleted_count > 0

@app.on_event("startup")
async def startup():
    global datastore
    datastore = await get_datastore()


def start():
    uvicorn.run("server.main:app", host="0.0.0.0", port=8000, reload=True)