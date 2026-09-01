from pathlib import Path


TOOLS = Path(__file__).resolve().parents[1]


def test_tools_only_expose_supported_import_and_capability_entries():
    required = {
        "README.md",
        "config.example.yaml",
        "preflight.py",
        "load_sample_data.py",
        "import_kn.py",
        "setup_catalog.py",
        "bind_kn_resources.py",
        "smoke_test.py",
        "power_layer.py",
        "register_native_function_toolbox.py",
        "register_skills.py",
        "native_function_bundle.py",
        "managed_execution.py",
        "function_catalog.py",
    }
    assert required <= {path.name for path in TOOLS.iterdir()}
    assert (TOOLS / "fn").is_dir()
    assert (TOOLS / "assets").is_dir()

    retired_entries = {
        "action_gateway.py",
        "benchmark_third_party.py",
        "bind_action_datasets.py",
        "bind_skill_dataset.py",
        "bootstrap_action_layer.py",
        "compress_resolved_context.py",
        "export_fn_openapi.py",
        "fn_cli.py",
        "fn_service.py",
        "localize_kn.py",
        "localize_sample_data.py",
        "online_acceptance.py",
        "resolve_function_toolbox.py",
        "run_scenario.py",
        "service_dependencies.py",
        "setup_action_datasets.py",
        "setup_skill_dataset.py",
        "skill_orchestration.py",
        "start_function_service.py",
        "toolbox_resolution.py",
    }
    assert not ({path.name for path in TOOLS.iterdir()} & retired_entries)
    assert not any(
        (TOOLS / name).exists()
        for name in ("actions", "context", "dialogue", "eval", "scenario")
    )
