from fastapi import FastAPI
from api.routes import chat, health
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI(title="SmartB100 API", description="API para o sistema SmartB100")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(chat.router)
app.include_router(health.router)