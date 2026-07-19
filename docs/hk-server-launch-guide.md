# 香港服务器 IP-only 部署指南

> 本文是 Electric Showcase WebUI 的实际部署操作手册。
> 适用场景：香港 Ubuntu 22.04 VPS，IP 直接访问，无域名无 HTTPS。

## 0. 服务器要求

| 项目 | 要求 |
|------|------|
| 地域 | 中国香港 |
| 系统 | Ubuntu 22.04 LTS（纯净版，不预装宝塔/WordPress/Docker/LNMP） |
| 配置 | 2核 2G，40G SSD |
| 端口 | 开放 22（SSH）和 8000（FastAPI） |

## 1. 安全组放行端口

在阿里云/腾讯云控制台 -> 安全组/防火墙规则：

- **入方向** TCP 22 端口 -> 0.0.0.0/0（SSH）
- **入方向** TCP 8000 端口 -> 0.0.0.0/0（WebUI）

## 2. SSH 登录服务器

```bash
ssh root@<服务器IP>
```

首次登录确认 fingerprint。

## 3. 安装系统依赖

```bash
apt update
apt install -y python3 python3-venv python3-pip git
```

验证 Python 版本 >= 3.10：

```bash
python3 --version
```

## 4. 获取项目代码

```bash
cd /opt
git clone https://github.com/mechanic-Q/electric.git ellectric
cd ellectric
```

如果仓库是私有的，用 `gh auth login` 或 deploy key。

## 5. 创建虚拟环境 + 安装最小依赖

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r ellectric/requirements-showcase.txt
```

`requirements-showcase.txt` 只包含展示服务器需要的最小依赖（FastAPI + pandas + LangChain），不含 xgboost/shap/ASSUME/PyTorch。

## 6. 构建 Frontend（如果在本地已构建可跳过）

如果服务器上需要重新构建前端：

```bash
apt install -y nodejs npm
cd ellectric/web
npm install
npm run build
cd ../..
```

构建产物输出到 `ellectric/api/static/`。

**推荐**：在本地构建好 `ellectric/api/static/` 后，用 `scp` 上传到服务器，避免服务器装 Node.js。

## 7. 设置 DeepSeek API Key

```bash
export DEEPSEEK_API_KEY='sk-你的deepseek-api-key'
```

验证：

```bash
echo $DEEPSEEK_API_KEY
```

**安全**：不要把 key 写进代码或 git。只在环境变量中设置。

## 8. 启动服务

```bash
. .venv/bin/activate
cd /opt/ellectric
uvicorn ellectric.api.server:app --host 0.0.0.0 --port 8000
```

浏览器打开：

```
http://<服务器IP>:8000
```

验证：
- 页面加载，动画自动播放
- Copilot 面板显示
- 问 Copilot "XGBoost 是什么" 能正常回答

## 9. 配置 systemd 守护进程

创建 `/etc/systemd/system/ellectric.service`：

```ini
[Unit]
Description=Ellectric Showcase WebUI
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/opt/ellectric
Environment=DEEPSEEK_API_KEY=sk-你的deepseek-api-key
ExecStart=/opt/ellectric/.venv/bin/uvicorn ellectric.api.server:app --host 0.0.0.0 --port 8000
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

启用：

```bash
systemctl daemon-reload
systemctl enable ellectric
systemctl start ellectric
systemctl status ellectric
```

验证：

```bash
curl -f http://127.0.0.1:8000/rolling-demo.json | head -c 100
```

现在服务会在 SSH 断开和服务器重启后自动恢复。

## 10. 验证清单

| 检查项 | 命令 | 预期 |
|--------|------|------|
| 页面加载 | 浏览器开 `http://IP:8000` | 显示 dashboard |
| 静态数据 | `curl -f http://127.0.0.1:8000/rolling-demo.json` | 返回 JSON |
| 报告列表 | `curl -f http://127.0.0.1:8000/reports` | 返回 JSON 数组 |
| Copilot | 页面上问 "XGBoost 是什么" | 流式回答 |
| 服务状态 | `systemctl status ellectric` | active (running) |
| 开机自启 | `systemctl is-enabled ellectric` | enabled |

## 11. 后续（暂不做）

以下功能在 IP-only 验证通过后再考虑：

- **域名**：购买域名，DNS A 记录指向服务器 IP
- **HTTPS**：安装 Caddy（自动 Let's Encrypt 证书），反代 uvicorn
- **Caddy 优于 nginx**：SSE 流式传输默认不缓冲，配置更简单
- **更换弱密码**：改 root 密码或改用 SSH 密钥登录
