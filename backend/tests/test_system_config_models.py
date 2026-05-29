import pytest
from httpx import ASGITransport, AsyncClient

from app.main import app
from app.services import sysconfig_svc


@pytest.mark.asyncio
async def test_workspace_models_hide_non_visible_models_for_admin(isolated_data_root):
    from app.core import deps

    sysconfig_svc.update_llm_model(
        "xiaomi/visible-model",
        {
            "label": "Visible",
            "input_unit_price": 0,
            "output_unit_price": 0,
            "enabled": True,
            "visible_to_user": True,
        },
    )
    sysconfig_svc.update_llm_model(
        "xiaomi/hidden-model",
        {
            "label": "Hidden",
            "input_unit_price": 0,
            "output_unit_price": 0,
            "enabled": True,
            "visible_to_user": False,
        },
    )
    sysconfig_svc.update_llm_default_model("xiaomi/hidden-model")

    async def fake_admin():
        return {"id": "admin-1", "auth_role": "super_admin"}

    app.dependency_overrides[deps.get_current_user] = fake_admin
    transport = ASGITransport(app=app)
    async with AsyncClient(transport=transport, base_url="http://test") as ac:
        r = await ac.get("/api/v1/system-config/models")
    app.dependency_overrides.clear()

    assert r.status_code == 200
    data = r.json()["data"]
    ids = [item["id"] for item in data["items"]]
    assert "xiaomi/visible-model" in ids
    assert "xiaomi/hidden-model" not in ids
    assert data["default"] != "xiaomi/hidden-model"
