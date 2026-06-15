from app.services import sysconfig_svc


def test_refresh_mify_route_precedes_model_id_catchall():
    from app.api.v1 import admin_settings

    paths = [getattr(route, "path", "") for route in admin_settings.router.routes]
    assert paths.index("/llm/models/refresh-mify") < paths.index("/llm/models/{model_id:path}")


def test_merge_mify_llm_models_preserves_admin_fields():
    existing = [
        {
            "id": "xiaomi/kimi-k2.5",
            "label": "Kimi Stable",
            "input_unit_price": 1.2,
            "output_unit_price": 4.8,
            "enabled": False,
            "visible_to_user": True,
        }
    ]
    rows = [
        {"id": "kimi-k2.5", "owned_by": "xiaomi", "model_type": "llm"},
        {"id": "glm-5", "owned_by": "xiaomi", "model_type": "llm"},
        {"id": "bge-m3", "owned_by": "xiaomi", "model_type": "text-embedding"},
        {"id": "", "owned_by": "xiaomi", "model_type": "llm"},
    ]

    merged, summary = sysconfig_svc._merge_mify_llm_models(existing, rows)

    by_id = {m["id"]: m for m in merged}
    assert by_id["xiaomi/kimi-k2.5"] == existing[0]
    assert by_id["xiaomi/glm-5"]["label"] == "glm-5 (xiaomi)"
    assert by_id["xiaomi/glm-5"]["enabled"] is True
    assert by_id["xiaomi/glm-5"]["visible_to_user"] is False
    assert summary == {
        "fetched": 4,
        "llm": 2,
        "inserted": 1,
        "updated": 0,
        "kept_existing": 0,
        "skipped_non_llm": 1,
        "skipped_invalid": 1,
    }


def test_refresh_llm_models_from_mify_saves_new_models(monkeypatch, isolated_data_root):
    monkeypatch.setattr(
        sysconfig_svc,
        "_list_mify_gateway_llm_models",
        lambda: [{"id": "new-model", "owned_by": "xiaomi", "model_type": "llm"}],
    )

    result = sysconfig_svc.refresh_llm_models_from_mify()

    assert result["summary"]["inserted"] == 1
    cfg = sysconfig_svc.get_llm_config()
    model = next(m for m in cfg["models"] if m["id"] == "xiaomi/new-model")
    assert model["visible_to_user"] is False
    assert model["enabled"] is True
