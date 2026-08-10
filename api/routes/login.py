from fastapi import APIRouter
from ..functions.login import LoginRequest, login

router = APIRouter()


@router.post("/api/login")
def login_route(data: LoginRequest):
    response = login(data.uid, data.password)
    return response