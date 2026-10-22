#!/bin/zsh -l
cd "$(dirname "$0")"
if ! command -v npm >/dev/null 2>&1; then
  echo '需要 Node.js 22 与 npm。请安装后重新运行。'
  read -k 1
  exit 1
fi
if [[ ! -d node_modules ]]; then
  npm install --no-audit --no-fund || exit 1
fi
echo 'KiraOrder 启动后，请打开 http://127.0.0.1:5173/'
npm run dev
