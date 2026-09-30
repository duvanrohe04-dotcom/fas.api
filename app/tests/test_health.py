"""Tests for the health endpoint and the app factory."""

from __future__ import annotations

from fastapi import FastAPI
from httpx import AsyncClient

from app.core.database import database_health_dependency
from app.main import create_app


async def test_health_returns_ok(client: AsyncClient) -> None:
    """GET /api/v1/health reports the service as operational."""
    response = await client.get("/api/v1/health")

    assert response.status_code == 200
    body = response.json()
    assert body["status"] == "ok"
    assert body["database"] == "up"
    assert body["environment"] == "testing"


async def test_health_is_reachable_without_prefix(client: AsyncClient) -> None:
    """The health check is also exposed at the root path."""
    response = await client.get("/health")

    assert response.status_code == 200


async def test_health_returns_503_when_database_is_down(app: FastAPI, client: AsyncClient) -> None:
    """A failing database check degrades the service to 503."""
    app.dependency_overrides[database_health_dependency] = lambda: False

    response = await client.get("/api/v1/health")

    assert response.status_code == 503
    assert response.json()["status"] == "degraded"


def test_openapi_is_generated() -> None:
    """The OpenAPI schema is valid and exposes the v1 endpoints."""
    schema = create_app().openapi()

    assert schema["info"]["title"]
    assert "/api/v1/health" in schema["paths"]
