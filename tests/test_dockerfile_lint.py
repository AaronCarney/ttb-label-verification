"""Smoke-lint the Dockerfile + frontmatter without invoking docker."""
from pathlib import Path


def test_cpu_dockerfile_uses_python_312_slim():
    content = Path("Dockerfile").read_text()
    assert "FROM python:3.12-slim" in content
    assert "uv sync" in content
    assert "CMD" in content and "uvicorn" in content
    assert "0.0.0.0" in content and "8000" in content
    # E7 island bundle ships with `COPY app ./app`
    assert "COPY app ./app" in content


def test_gpu_dockerfile_uses_cuda():
    content = Path("Dockerfile.gpu").read_text()
    assert "nvidia/cuda" in content
    assert "uv sync" in content and "--extra gpu" in content


def test_compose_files_exist_and_share_model_snapshot():
    cpu = Path("docker-compose.yml").read_text()
    gpu = Path("docker-compose.gpu.yml").read_text()
    assert "LLM_MODEL_SNAPSHOT" in cpu and "LLM_MODEL_SNAPSHOT" in gpu
    import re
    cpu_pin = re.search(r"LLM_MODEL_SNAPSHOT.*\$\{LLM_MODEL_SNAPSHOT:-([^}]+)\}", cpu)
    gpu_pin = re.search(r"LLM_MODEL_SNAPSHOT.*\$\{LLM_MODEL_SNAPSHOT:-([^}]+)\}", gpu)
    assert cpu_pin and gpu_pin and cpu_pin.group(1) == gpu_pin.group(1)


def test_dockerignore_excludes_frontend_source():
    content = Path(".dockerignore").read_text()
    lines = [ln.strip() for ln in content.split("\n")]
    assert "frontend/" in lines or "frontend" in lines
    assert any("node_modules" in ln for ln in lines)


def test_readme_has_hf_frontmatter():
    content = Path("README.md").read_text()
    assert content.startswith("---\n")
    assert "sdk: docker" in content
    assert "app_port: 8000" in content
    assert "hardware: cpu-basic" in content
