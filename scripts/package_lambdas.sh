#!/usr/bin/env bash
set -euo pipefail

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
BUILD_DIR="${ROOT_DIR}/build/lambdas"

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

rm -rf "${BUILD_DIR}"
mkdir -p \
  "${BUILD_DIR}/health" \
  "${BUILD_DIR}/users_service" \
  "${BUILD_DIR}/catalog_service" \
  "${BUILD_DIR}/orders_service" \
  "${BUILD_DIR}/restaurants_service" \
  "${BUILD_DIR}/reservations_service" \
  "${BUILD_DIR}/promotions_service" \
  "${BUILD_DIR}/analytics_service" \
  "${BUILD_DIR}/db_migrate"

echo "Copying health-lambda source"
copy_tree "${ROOT_DIR}/lambdas/health" "${BUILD_DIR}/health"

echo "Copying users-service-lambda source"
copy_tree "${ROOT_DIR}/lambdas/users_service" "${BUILD_DIR}/users_service"
copy_tree "${ROOT_DIR}/lambdas/common" "${BUILD_DIR}/users_service/common"
copy_tree "${ROOT_DIR}/app" "${BUILD_DIR}/users_service/app"

if [[ -f "${ROOT_DIR}/lambdas/users_service/requirements.txt" ]]; then
  echo "Installing users-service dependencies into build/lambdas/users_service"
  "${PYTHON_BIN}" -m pip install \
    --no-cache-dir \
    -r "${ROOT_DIR}/lambdas/users_service/requirements.txt" \
    -t "${BUILD_DIR}/users_service"
else
  echo "No users-service requirements.txt found; skipping dependency install"
fi

echo "Copying catalog-service-lambda source"
copy_tree "${ROOT_DIR}/lambdas/catalog_service" "${BUILD_DIR}/catalog_service"
copy_tree "${ROOT_DIR}/lambdas/common" "${BUILD_DIR}/catalog_service/common"
copy_tree "${ROOT_DIR}/app" "${BUILD_DIR}/catalog_service/app"

if [[ -f "${ROOT_DIR}/lambdas/catalog_service/requirements.txt" ]]; then
  echo "Installing catalog-service dependencies into build/lambdas/catalog_service"
  "${PYTHON_BIN}" -m pip install \
    --no-cache-dir \
    -r "${ROOT_DIR}/lambdas/catalog_service/requirements.txt" \
    -t "${BUILD_DIR}/catalog_service"
else
  echo "No catalog-service requirements.txt found; skipping dependency install"
fi

echo "Copying orders-service-lambda source"
copy_tree "${ROOT_DIR}/lambdas/orders_service" "${BUILD_DIR}/orders_service"
copy_tree "${ROOT_DIR}/lambdas/common" "${BUILD_DIR}/orders_service/common"
copy_tree "${ROOT_DIR}/app" "${BUILD_DIR}/orders_service/app"

if [[ -f "${ROOT_DIR}/lambdas/orders_service/requirements.txt" ]]; then
  echo "Installing orders-service dependencies into build/lambdas/orders_service"
  "${PYTHON_BIN}" -m pip install \
    --no-cache-dir \
    -r "${ROOT_DIR}/lambdas/orders_service/requirements.txt" \
    -t "${BUILD_DIR}/orders_service"
else
  echo "No orders-service requirements.txt found; skipping dependency install"
fi

echo "Copying restaurants-service-lambda source"
copy_tree "${ROOT_DIR}/lambdas/restaurants_service" "${BUILD_DIR}/restaurants_service"
copy_tree "${ROOT_DIR}/lambdas/common" "${BUILD_DIR}/restaurants_service/common"
copy_tree "${ROOT_DIR}/app" "${BUILD_DIR}/restaurants_service/app"

if [[ -f "${ROOT_DIR}/lambdas/restaurants_service/requirements.txt" ]]; then
  echo "Installing restaurants-service dependencies into build/lambdas/restaurants_service"
  "${PYTHON_BIN}" -m pip install \
    --no-cache-dir \
    -r "${ROOT_DIR}/lambdas/restaurants_service/requirements.txt" \
    -t "${BUILD_DIR}/restaurants_service"
else
  echo "No restaurants-service requirements.txt found; skipping dependency install"
fi

echo "Copying reservations-service-lambda source"
copy_tree "${ROOT_DIR}/lambdas/reservations_service" "${BUILD_DIR}/reservations_service"
copy_tree "${ROOT_DIR}/lambdas/common" "${BUILD_DIR}/reservations_service/common"
copy_tree "${ROOT_DIR}/app" "${BUILD_DIR}/reservations_service/app"

if [[ -f "${ROOT_DIR}/lambdas/reservations_service/requirements.txt" ]]; then
  echo "Installing reservations-service dependencies into build/lambdas/reservations_service"
  "${PYTHON_BIN}" -m pip install \
    --no-cache-dir \
    -r "${ROOT_DIR}/lambdas/reservations_service/requirements.txt" \
    -t "${BUILD_DIR}/reservations_service"
else
  echo "No reservations-service requirements.txt found; skipping dependency install"
fi

echo "Copying promotions-service-lambda source"
copy_tree "${ROOT_DIR}/lambdas/promotions_service" "${BUILD_DIR}/promotions_service"
copy_tree "${ROOT_DIR}/lambdas/common" "${BUILD_DIR}/promotions_service/common"
copy_tree "${ROOT_DIR}/app" "${BUILD_DIR}/promotions_service/app"

if [[ -f "${ROOT_DIR}/lambdas/promotions_service/requirements.txt" ]]; then
  echo "Installing promotions-service dependencies into build/lambdas/promotions_service"
  "${PYTHON_BIN}" -m pip install \
    --no-cache-dir \
    -r "${ROOT_DIR}/lambdas/promotions_service/requirements.txt" \
    -t "${BUILD_DIR}/promotions_service"
else
  echo "No promotions-service requirements.txt found; skipping dependency install"
fi

echo "Copying analytics-service-lambda source"
copy_tree "${ROOT_DIR}/lambdas/analytics_service" "${BUILD_DIR}/analytics_service"
copy_tree "${ROOT_DIR}/lambdas/common" "${BUILD_DIR}/analytics_service/common"
copy_tree "${ROOT_DIR}/app" "${BUILD_DIR}/analytics_service/app"

if [[ -f "${ROOT_DIR}/lambdas/analytics_service/requirements.txt" ]]; then
  echo "Installing analytics-service dependencies into build/lambdas/analytics_service"
  "${PYTHON_BIN}" -m pip install \
    --no-cache-dir \
    -r "${ROOT_DIR}/lambdas/analytics_service/requirements.txt" \
    -t "${BUILD_DIR}/analytics_service"
else
  echo "No analytics-service requirements.txt found; skipping dependency install"
fi

echo "Copying db-migrate-lambda source"
copy_tree "${ROOT_DIR}/lambdas/db_migrate" "${BUILD_DIR}/db_migrate"

echo "Copying backend app/ and migrations/ into db-migrate package"
copy_tree "${ROOT_DIR}/app" "${BUILD_DIR}/db_migrate/app"
copy_tree "${ROOT_DIR}/migrations" "${BUILD_DIR}/db_migrate/migrations"

if [[ ! -f "${ROOT_DIR}/lambdas/db_migrate/requirements.txt" ]]; then
  echo "ERROR: lambdas/db_migrate/requirements.txt is required." >&2
  exit 1
fi

echo "Installing db-migrate/backend dependencies into build/lambdas/db_migrate"
"${PYTHON_BIN}" -m pip install \
  --no-cache-dir \
  -r "${ROOT_DIR}/lambdas/db_migrate/requirements.txt" \
  -t "${BUILD_DIR}/db_migrate"

clean_python_artifacts "${BUILD_DIR}"

echo "Built Lambda folders:"
find "${BUILD_DIR}" -maxdepth 2 -type d | sort

echo "Done. Terraform archive_file will read from build/lambdas/*."
