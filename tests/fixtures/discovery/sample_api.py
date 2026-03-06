"""Sample API module for discovery tests."""

from django.urls import path, re_path
from fastapi import APIRouter, FastAPI
from flask import Blueprint, Flask

app = FastAPI()
router = APIRouter()
flask_app = Flask(__name__)
bp = Blueprint("items", __name__)


class UserResponse: ...


@app.get("/users/{id}", response_model=UserResponse)
def get_user(user_id: int) -> dict[str, int]:
    """Retrieve a user by ID."""

    return {"id": user_id}


@app.post("/users")
def create_user(payload: dict[str, str]) -> dict[str, str]:
    return payload


@router.patch("/users/{id}")
def update_user(user_id: int, payload: dict[str, str]) -> dict[str, str]:
    return {"id": user_id, **payload}


@bp.route("/items", methods=["GET", "POST"])
def items() -> list[str]:
    return ["a", "b"]


@flask_app.route("/health")
def health() -> tuple[str, int]:
    return "ok", 200


def user_detail(request: object, user_id: int) -> None:
    """Show one user."""


def legacy_view(request: object, slug: str) -> None:
    return None


urlpatterns = [
    path("users/<int:user_id>/", user_detail, name="user-detail"),
    re_path(r"^legacy/(?P<slug>[-\w]+)/$", legacy_view),
]
