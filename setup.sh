#!/bin/bash
set -e

if [[ -z "${ENV_NAME}" || -z "${PYTHON_VERSION}" ]]; then
  echo "ENV_NAME and PYTHON_VERSION must be set."
  echo "Usage: ENV_NAME=<env_name> PYTHON_VERSION=<python_version> ./setup.sh"
  exit 1
fi

echo "Creating a conda environment: ${ENV_NAME} with Python ${PYTHON_VERSION}"
conda create --name "${ENV_NAME}" python="${PYTHON_VERSION}" -y

echo "Installing Poetry (>=1.8) into ${ENV_NAME}"
conda run -n "${ENV_NAME}" pip install "poetry>=1.8"

echo "Binding Poetry to the env's Python"
PYBIN=$(conda run -n "${ENV_NAME}" python -c 'import sys; print(sys.executable)')
conda run -n "${ENV_NAME}" poetry env use "${PYBIN}"

echo "Installing project dependencies with Poetry"
conda run -n "${ENV_NAME}" poetry install

echo "Installing pre-commit hooks"
conda run -n "${ENV_NAME}" poetry run pre-commit install --allow-missing-config

echo "Done. Activate the env with:"
echo "  conda activate ${ENV_NAME}"
echo "Then run the API with:"
echo "  poetry run uvicorn tfl_task_scheduler.main:app --reload --port 5555"
