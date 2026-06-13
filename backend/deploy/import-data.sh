#!/usr/bin/env bash
# 冷备一键导入：把 warden-stock-data 的 data-export 冷备灌入本地 market 表。
#
# 在 api 容器内执行 app.cli.import_backup（容器已含全部依赖，且经内网直连 postgres）。
# 把宿主机的 data-export 目录只读挂载到容器 /data-export。
#
# 用法：
#   ./import-data.sh [EXPORT_DIR] [-- 额外参数透传给 import_backup]
# 示例：
#   ./import-data.sh                                   # 用默认冷备路径，全量导入
#   ./import-data.sh /path/to/data-export              # 指定冷备目录
#   ./import-data.sh /path/to/data-export -- --only bars --no-truncate
set -euo pipefail

cd "$(dirname "$0")"

# 默认指向同级 warden-stock-data 的冷备目录，可用第一个参数覆盖。
DEFAULT_EXPORT="$(cd ../../.. && pwd)/warden-stock-data/backend/data-export"
EXPORT_DIR="${1:-$DEFAULT_EXPORT}"
shift || true
# 跳过可选的 -- 分隔符
if [[ "${1:-}" == "--" ]]; then shift; fi
EXTRA_ARGS=("$@")

if [[ ! -d "$EXPORT_DIR" ]]; then
  echo "错误：冷备目录不存在：$EXPORT_DIR" >&2
  echo "请传入 warden-stock-data 的 backend/data-export 目录路径。" >&2
  exit 1
fi

echo "冷备目录：$EXPORT_DIR"
echo "开始导入（容器内执行，约数分钟）..."

# 同时挂载本地 app 源码，确保使用最新 CLI（无需为 app/ 改动重建镜像）。
APP_DIR="$(cd .. && pwd)/app"

docker compose -f docker-compose.yml run --rm --no-deps \
  -v "$APP_DIR":/app/app:ro \
  -v "$EXPORT_DIR":/data-export:ro \
  api python -m app.cli.import_backup --path /data-export "${EXTRA_ARGS[@]}"
