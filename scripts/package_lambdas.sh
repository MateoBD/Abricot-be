#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build/lambdas"
CACHE_DIR="${ROOT_DIR}/.cache/lambda_deps"
PIP_CACHE_DIR="${ROOT_DIR}/.cache/pip"
export PIP_CACHE_DIR

find_python() {
  if command -v python3 >/dev/null 2>&1; then
    command -v python3
    return 0
  fi

  if command -v python >/dev/null 2>&1; then
    command -v python
    return 0
  fi

  echo "ERROR: python3 or python is required to package Lambda dependencies." >&2
  return 1
}

copy_tree() {
  local source_dir="$1"
  local target_dir="$2"

  mkdir -p "${target_dir}"
  cp -R "${source_dir}/." "${target_dir}/"
}

clean_python_artifacts() {
  local target_dir="$1"

  find "${target_dir}" -type d -name "__pycache__" -prune -exec rm -rf {} +
  find "${target_dir}" -type f \( -name "*.pyc" -o -name "*.pyo" \) -delete
}

requirements_hash() {
  local requirements_file="$1"

  "${PYTHON_BIN}" - "${requirements_file}" <<'PY'
import hashlib
import pathlib
import sys

path = pathlib.Path(sys.argv[1])
print(hashlib.sha256(path.read_bytes()).hexdigest()[:16])
PY
}

install_dependencies() {
  local service_name="$1"
  local target_dir="$2"
  local requirements_file="${ROOT_DIR}/lambdas/${service_name}/requirements.txt"

  if [[ ! -f "${requirements_file}" ]]; then
    echo "No ${service_name} requirements.txt found; skipping dependency install"
    return 0
  fi

  local req_hash
  req_hash="$(requirements_hash "${requirements_file}")"

  local cache_root="${CACHE_DIR}/${service_name}/py${PYTHON_VERSION}/${req_hash}"
  local cache_python="${cache_root}/python"
  local ready_marker="${cache_root}/.ready"

  if [[ ! -f "${ready_marker}" ]]; then
    echo "Building dependency cache for ${service_name} (${req_hash})"
    rm -rf "${cache_root}"
    mkdir -p "${cache_python}"
    "${PYTHON_BIN}" -m pip install \
      --upgrade \
      -r "${requirements_file}" \
      -t "${cache_python}"
    clean_python_artifacts "${cache_python}"
    touch "${ready_marker}"
  else
    echo "Reusing dependency cache for ${service_name} (${req_hash})"
  fi

  echo "Copying cached ${service_name} dependencies into build/lambdas/${service_name}"
  copy_tree "${cache_python}" "${target_dir}"
}

PYTHON_BIN="$(find_python)"
PYTHON_VERSION="$("${PYTHON_BIN}" - <<'PY'
import sys

print(f"{sys.version_info.major}.{sys.version_info.minor}")
PY
)"

if ! "${PYTHON_BIN}" -m pip --version >/dev/null 2>&1; then
  echo "ERROR: pip is required. Install pip for ${PYTHON_BIN} and retry." >&2
  exit 1
fi

echo "Packaging Abricot Lambda deployment folders"
echo "Repository: ${ROOT_DIR}"
echo "Python: ${PYTHON_BIN} (${PYTHON_VERSION})"
echo "Dependency cache: ${CACHE_DIR}"
echo "pip cache: ${PIP_CACHE_DIR}"

rm -rf "${BUILD_DIR}"
mkdir -p "${CACHE_DIR}" "${PIP_CACHE_DIR}"
mkdir -p \
  "${BUILD_DIR}/health" \
  "${BUILD_DIR}/users_service" \
  "${BUILD_DIR}/catalog_service" \
  "${BUILD_DIR}/orders_service" \
  "${BUILD_DIR}/restaurants_service" \
  "${BUILD_DIR}/reservations_service" \
  "${BUILD_DIR}/promotions_service" \
  "${BUILD_DIR}/analytics_service" \
  "${BUILD_DIR}/email_worker" \
  "${BUILD_DIR}/analytics_worker" \
  "${BUILD_DIR}/db_migrate"

echo "Copying health-lambda source"
copy_tree "${ROOT_DIR}/lambdas/health" "${BUILD_DIR}/health"

echo "Copying users-service-lambda source"
copy_tree "${ROOT_DIR}/lambdas/users_service" "${BUILD_DIR}/users_service"
copy_tree "${ROOT_DIR}/lambdas/common" "${BUILD_DIR}/users_service/common"
copy_tree "${ROOT_DIR}/app" "${BUILD_DIR}/users_service/app"
install_dependencies "users_service" "${BUILD_DIR}/users_service"

echo "Copying catalog-service-lambda source"
copy_tree "${ROOT_DIR}/lambdas/catalog_service" "${BUILD_DIR}/catalog_service"
copy_tree "${ROOT_DIR}/lambdas/common" "${BUILD_DIR}/catalog_service/common"
copy_tree "${ROOT_DIR}/app" "${BUILD_DIR}/catalog_service/app"
install_dependencies "catalog_service" "${BUILD_DIR}/catalog_service"

echo "Copying orders-service-lambda source"
copy_tree "${ROOT_DIR}/lambdas/orders_service" "${BUILD_DIR}/orders_service"
copy_tree "${ROOT_DIR}/lambdas/common" "${BUILD_DIR}/orders_service/common"
copy_tree "${ROOT_DIR}/app" "${BUILD_DIR}/orders_service/app"
install_dependencies "orders_service" "${BUILD_DIR}/orders_service"

echo "Copying restaurants-service-lambda source"
copy_tree "${ROOT_DIR}/lambdas/restaurants_service" "${BUILD_DIR}/restaurants_service"
copy_tree "${ROOT_DIR}/lambdas/common" "${BUILD_DIR}/restaurants_service/common"
copy_tree "${ROOT_DIR}/app" "${BUILD_DIR}/restaurants_service/app"
install_dependencies "restaurants_service" "${BUILD_DIR}/restaurants_service"

echo "Copying reservations-service-lambda source"
copy_tree "${ROOT_DIR}/lambdas/reservations_service" "${BUILD_DIR}/reservations_service"
copy_tree "${ROOT_DIR}/lambdas/common" "${BUILD_DIR}/reservations_service/common"
copy_tree "${ROOT_DIR}/app" "${BUILD_DIR}/reservations_service/app"
install_dependencies "reservations_service" "${BUILD_DIR}/reservations_service"

echo "Copying promotions-service-lambda source"
copy_tree "${ROOT_DIR}/lambdas/promotions_service" "${BUILD_DIR}/promotions_service"
copy_tree "${ROOT_DIR}/lambdas/common" "${BUILD_DIR}/promotions_service/common"
copy_tree "${ROOT_DIR}/app" "${BUILD_DIR}/promotions_service/app"
install_dependencies "promotions_service" "${BUILD_DIR}/promotions_service"

echo "Copying analytics-service-lambda source"
copy_tree "${ROOT_DIR}/lambdas/analytics_service" "${BUILD_DIR}/analytics_service"
copy_tree "${ROOT_DIR}/lambdas/common" "${BUILD_DIR}/analytics_service/common"
copy_tree "${ROOT_DIR}/app" "${BUILD_DIR}/analytics_service/app"
install_dependencies "analytics_service" "${BUILD_DIR}/analytics_service"

echo "Copying email-worker-lambda source"
copy_tree "${ROOT_DIR}/lambdas/email_worker" "${BUILD_DIR}/email_worker"
install_dependencies "email_worker" "${BUILD_DIR}/email_worker"

echo "Copying analytics-worker-lambda source"
copy_tree "${ROOT_DIR}/lambdas/analytics_worker" "${BUILD_DIR}/analytics_worker"
install_dependencies "analytics_worker" "${BUILD_DIR}/analytics_worker"

echo "Copying db-migrate-lambda source"
copy_tree "${ROOT_DIR}/lambdas/db_migrate" "${BUILD_DIR}/db_migrate"

echo "Copying backend app/ and migrations/ into db-migrate package"
copy_tree "${ROOT_DIR}/app" "${BUILD_DIR}/db_migrate/app"
copy_tree "${ROOT_DIR}/migrations" "${BUILD_DIR}/db_migrate/migrations"

if [[ ! -f "${ROOT_DIR}/lambdas/db_migrate/requirements.txt" ]]; then
  echo "ERROR: lambdas/db_migrate/requirements.txt is required." >&2
  exit 1
fi
install_dependencies "db_migrate" "${BUILD_DIR}/db_migrate"

clean_python_artifacts "${BUILD_DIR}"

echo "Built Lambda folders:"
find "${BUILD_DIR}" -maxdepth 2 -type d | sort

echo "Done. Terraform archive_file will read from build/lambdas/*."
