from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from api.routes.login import router as login_router
from api.routes.chat_ia_rag import router as chat_router

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(login_router)
app.include_router(chat_router)