from pathlib import Path


PACK = Path(__file__).resolve().parents[2]


def test_function_service_deployment_artifacts_exist():
    assert not (PACK / "Dockerfile.function").exists()
    assert not (PACK / "docker-compose.function.yaml").exists()


def test_function_deployment_does_not_embed_host_docker_internal():
    config = (PACK / "tools" / "config.example.yaml").read_text(encoding="utf-8")
    requirements = (PACK / "tools" / "requirements.txt").read_text(encoding="utf-8")
    assert "service_url" not in config
    assert "fastapi" not in requirements.lower()
    assert "uvicorn" not in requirements.lower()
