# Hướng Dẫn Setup CI/CD với GitHub Actions

## 📋 Tổng Quan

CI/CD pipeline này sẽ tự động deploy **TẤT CẢ** các layers lên server mỗi khi bạn push code lên GitHub:
- ✅ **Builder-Layer-End**: Pipeline với Docker containers (Neo4j, Fuseki, Redis, PostgreSQL, Stellio, Kafka)
- ✅ **Layer-Business**: Backend API (Node.js/TypeScript) + Frontend (React/Vite)

**Thông tin:**
- Repository: https://github.com/NguyenDinhAnhTuan04/deploy.git
- Server: 54.179.155.70
- User: deepminds
- Architecture:
  - Builder-Layer-End: Docker Compose (`docker-compose.test.yml`)
  - Layer-Business Backend: PM2 process manager
  - Layer-Business Frontend: PM2 process manager

---

## 🚀 Bước 1: Setup GitHub Secrets

1. Truy cập repository của bạn trên GitHub
2. Vào **Settings** → **Secrets and variables** → **Actions**
3. Nhấn **New repository secret** và thêm các secrets sau:

### Secrets cần tạo:

| Secret Name | Value | Mô tả |
|------------|-------|-------|
| `SERVER_HOST` | `54.179.155.70` | IP của server |
| `SERVER_USER` | `deepminds` | Username SSH |
| `SERVER_PASSWORD` | `Deepmind@2004` | Password SSH |

### Hướng dẫn chi tiết:

#### 1. SERVER_HOST
- Name: `SERVER_HOST`
- Value: `54.179.155.70`

#### 2. SERVER_USER
- Name: `SERVER_USER`
- Value: `deepminds`

#### 3. SERVER_PASSWORD
- Name: `SERVER_PASSWORD`
- Value: `Deepmind@2004`

---

## 🔧 Bước 2: Setup Server

### 2.1. Kết nối vào server qua SSH:

```bash
ssh deepminds@54.179.155.70
# Password: Deepmind@2004
```

### 2.2. Cài đặt Docker, Docker Compose và Node.js (nếu chưa có):

```bash
# Cài Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker $USER

# Cài Docker Compose
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# Cài Node.js v20.x (LTS)
curl -fsSL https://deb.nodesource.com/setup_20.x | sudo -E bash -
sudo apt-get install -y nodejs

# Cài PM2 (Process Manager cho Node.js)
sudo npm install -g pm2

# Verify installations
docker --version
docker-compose --version
node --version
npm --version
pm2 --version
```

### 2.3. Clone repository:

```bash
cd /home/deepminds
git clone https://github.com/NguyenDinhAnhTuan04/deploy.git
cd deploy
```

### 2.4. Setup Git credentials (để pull tự động):

```bash
# Option 1: HTTPS với Personal Access Token (recommended)
git config --global credential.helper store
git pull  # Nhập username và PAT khi được yêu cầu

# Option 2: SSH Key (alternative)
ssh-keygen -t ed25519 -C "your_email@example.com"
cat ~/.ssh/id_ed25519.pub  # Copy và add vào GitHub Settings > SSH Keys
```

### 2.5. Copy deploy script (optional):

```bash
cd /home/deepminds/deploy
chmod +x deploy-server.sh
```

### 2.6. Test deploy thủ công lần đầu:

```bash
# Test Builder-Layer-End (Pipeline)
cd /home/deepminds/deploy/Builder-Layer-End
docker-compose -f docker-compose.test.yml up -d

# Setup và test Backend
cd /home/deepminds/deploy/Layer-Business/backend
npm install
npm run build
pm2 start dist/server.js --name hcmc-backend

# Setup và test Frontend
cd /home/deepminds/deploy/Layer-Business/frontend
npm install
npm run build
pm2 start npm --name hcmc-frontend -- run preview

# Kiểm tra tất cả services
docker ps  # Xem pipeline containers
pm2 list   # Xem backend + frontend processes

# Enable PM2 startup on boot
pm2 startup
pm2 save
```

---

## 📝 Bước 3: Cấu Trúc Files

Sau khi setup, repository của bạn sẽ có các files:

```
deploy/
├── .github/
│   └── workflows/
│       └── deploy.yml                    # GitHub Actions workflow
├── Builder-Layer-End/                    # Pipeline layer
│   ├── docker-compose.test.yml          # File docker-compose chính
│   ├── docker-compose.yml               # File docker-compose phụ
│   ├── agents/                          # Pipeline agents
│   ├── tests/                           # Integration tests
│   └── ... (các files khác)
├── Layer-Business/                       # Business layer
│   ├── backend/                         # Node.js/TypeScript API
│   │   ├── src/
│   │   ├── dist/                        # Compiled files
│   │   ├── package.json
│   │   └── tsconfig.json
│   └── frontend/                        # React/Vite app
│       ├── src/
│       ├── dist/                        # Build output
│       ├── package.json
│       └── vite.config.ts
├── deploy-server.sh                      # Complete deploy script
└── DEPLOYMENT_GUIDE.md                   # File hướng dẫn này
```

---

## 🎯 Bước 4: Test CI/CD Pipeline

### 4.1. Push code lên GitHub:

```bash
git add .
git commit -m "Setup CI/CD pipeline"
git push origin main  # hoặc master
```

### 4.2. Kiểm tra GitHub Actions:

1. Truy cập repository trên GitHub
2. Vào tab **Actions**
3. Xem workflow "Deploy to Server" đang chạy
4. Click vào workflow để xem logs chi tiết

### 4.3. Verify trên server:

```bash
ssh deepminds@54.179.155.70

# Kiểm tra Pipeline containers
cd /home/deepminds/deploy/Builder-Layer-End
docker-compose -f docker-compose.test.yml ps
docker-compose -f docker-compose.test.yml logs --tail=50

# Kiểm tra Backend + Frontend
pm2 list
pm2 logs hcmc-backend --lines 50
pm2 logs hcmc-frontend --lines 50

# Kiểm tra ports
sudo netstat -tlnp | grep -E ':(3000|4173|8080|7474|7687|3030|6379|5432|9092)'
```

---

## 🔍 Cách Hoạt Động

### Workflow tự động khi:
- ✅ Push code lên branch `main` hoặc `master`
- ✅ Manual trigger từ GitHub Actions UI

### Các bước workflow thực hiện:

#### 1. Deploy Builder-Layer-End (Pipeline):
- Connect SSH vào server
- Pull latest code từ GitHub
- Stop pipeline containers hiện tại
- Pull Docker images mới nhất
- Build & Start pipeline containers (Neo4j, Fuseki, Redis, PostgreSQL, Stellio, Kafka)

#### 2. Deploy Layer-Business (Backend):
- Install/Update npm dependencies
- Build TypeScript → JavaScript
- Deploy với PM2 process manager
- Configure memory limit (4GB)

#### 3. Deploy Layer-Business (Frontend):
- Install/Update npm dependencies
- Build React/Vite app
- Deploy với PM2 (preview server)

#### 4. Verification:
- Verify tất cả pipeline containers đang chạy
- Verify backend PM2 process status
- Verify frontend PM2 process status
- Show logs và status

#### 5. Cleanup:
- Clean up unused Docker resources
- Show final status of all services

---

## 🛠️ Các Lệnh Hữu Ích

### Pipeline (Builder-Layer-End):

```bash
cd /home/deepminds/deploy/Builder-Layer-End

# Xem containers đang chạy
docker-compose -f docker-compose.test.yml ps

# Xem logs
docker-compose -f docker-compose.test.yml logs -f
docker-compose -f docker-compose.test.yml logs -f neo4j  # Specific service

# Restart services
docker-compose -f docker-compose.test.yml restart

# Stop all services
docker-compose -f docker-compose.test.yml down

# Start all services
docker-compose -f docker-compose.test.yml up -d

# Rebuild specific service
docker-compose -f docker-compose.test.yml up -d --build neo4j

# Clean up
docker system prune -af
docker volume prune -f
```

### Backend (Layer-Business):

```bash
cd /home/deepminds/deploy/Layer-Business/backend

# View logs
pm2 logs hcmc-backend
pm2 logs hcmc-backend --lines 100

# Restart
pm2 restart hcmc-backend

# Stop
pm2 stop hcmc-backend

# Start
pm2 start hcmc-backend

# View detailed info
pm2 describe hcmc-backend

# Monitor (real-time)
pm2 monit

# Rebuild and restart
npm run build
pm2 restart hcmc-backend
```

### Frontend (Layer-Business):

```bash
cd /home/deepminds/deploy/Layer-Business/frontend

# View logs
pm2 logs hcmc-frontend

# Restart
pm2 restart hcmc-frontend

# Stop
pm2 stop hcmc-frontend

# Rebuild and restart
npm run build
pm2 restart hcmc-frontend
```

### All Services:

```bash
# View all PM2 processes
pm2 list
pm2 status

# View all Docker containers
docker ps -a

# Restart everything
pm2 restart all
cd /home/deepminds/deploy/Builder-Layer-End && docker-compose -f docker-compose.test.yml restart

# Save PM2 configuration
pm2 save

# Delete all PM2 processes
pm2 delete all
```

### Deploy thủ công (Complete):

```bash
cd /home/deepminds/deploy
chmod +x deploy-server.sh
./deploy-server.sh
```

---

## ⚙️ Tùy Chỉnh Workflow

### Thay đổi branch trigger:

Sửa file `.github/workflows/deploy.yml`:

```yaml
on:
  push:
    branches:
      - main
      - develop  # Thêm branch khác
```

### Thêm notifications (Slack, Discord, etc.):

```yaml
- name: Notify Success
  if: success()
  run: |
    curl -X POST YOUR_WEBHOOK_URL \
      -H 'Content-Type: application/json' \
      -d '{"text":"Deployment successful!"}'
```

---

## 🐛 Troubleshooting

### Lỗi: SSH connection failed
- Kiểm tra secrets `SERVER_HOST`, `SERVER_USER`, `SERVER_PASSWORD` đã đúng chưa
- Verify server có thể SSH từ bên ngoài: `ssh deepminds@54.179.155.70`

### Lỗi: Git pull failed
- Kiểm tra Git credentials trên server
- Verify repository URL và permissions
- Thử: `cd /home/deepminds/deploy && git pull`

### Lỗi: Docker compose failed
```bash
# SSH vào server và check
cd /home/deepminds/deploy/Builder-Layer-End
docker-compose -f docker-compose.test.yml logs
docker-compose -f docker-compose.test.yml ps -a
```

### Lỗi: Permission denied (Docker)
```bash
sudo usermod -aG docker deepminds
newgrp docker
# Logout và login lại
```

### Lỗi: Backend build failed
```bash
cd /home/deepminds/deploy/Layer-Business/backend
npm install
npm run build
pm2 logs hcmc-backend --err
```

### Lỗi: Frontend build failed
```bash
cd /home/deepminds/deploy/Layer-Business/frontend
npm install
npm run build
pm2 logs hcmc-frontend --err
```

### Lỗi: PM2 process not found
```bash
# Reinstall PM2
npm install -g pm2
pm2 update

# Start processes manually
cd /home/deepminds/deploy/Layer-Business/backend
pm2 start dist/server.js --name hcmc-backend

cd /home/deepminds/deploy/Layer-Business/frontend
pm2 start npm --name hcmc-frontend -- run preview

pm2 save
```

### Lỗi: Port already in use
```bash
# Check what's using the port
sudo netstat -tlnp | grep :3000  # Backend port
sudo netstat -tlnp | grep :4173  # Frontend port

# Kill process
sudo kill -9 <PID>

# Or restart PM2
pm2 restart all
```

### Lỗi: Out of memory
```bash
# Increase PM2 memory limit
pm2 delete hcmc-backend
pm2 start dist/server.js --name hcmc-backend --max-memory-restart 8G

# Check server memory
free -h
```

### Containers không start
```bash
cd /home/deepminds/deploy/Builder-Layer-End

# Check specific container logs
docker-compose -f docker-compose.test.yml logs neo4j
docker-compose -f docker-compose.test.yml logs postgres
docker-compose -f docker-compose.test.yml logs stellio-api-gateway

# Restart specific container
docker-compose -f docker-compose.test.yml restart neo4j

# Rebuild from scratch
docker-compose -f docker-compose.test.yml down -v
docker-compose -f docker-compose.test.yml up -d --build
```

---

## 🔐 Bảo Mật

### Khuyến nghị:

1. **Sử dụng SSH Key thay vì password:**
   - Generate SSH key trên GitHub Actions runner
   - Add public key vào server `~/.ssh/authorized_keys`
   - Update workflow để dùng `key` thay vì `password`

2. **Giới hạn quyền truy cập:**
   - Chỉ cho phép SSH từ IP cụ thể
   - Sử dụng firewall rules

3. **Rotate credentials định kỳ**

4. **Backup dữ liệu thường xuyên**

---

## 📞 Hỗ Trợ

Nếu gặp vấn đề:
1. Kiểm tra GitHub Actions logs
2. SSH vào server xem logs: `docker-compose -f docker-compose.test.yml logs`
3. Xem Docker container status: `docker ps -a`

---

## ✅ Checklist Setup

- [ ] Đã tạo đủ 3 GitHub Secrets (SERVER_HOST, SERVER_USER, SERVER_PASSWORD)
- [ ] Server đã cài Docker và Docker Compose
- [ ] Server đã cài Node.js v20+ và npm
- [ ] Server đã cài PM2 global (`npm install -g pm2`)
- [ ] Đã clone repository vào `/home/deepminds/deploy`
- [ ] Git credentials đã được setup trên server
- [ ] Test deploy Builder-Layer-End thủ công thành công
- [ ] Test deploy Backend thủ công thành công
- [ ] Test deploy Frontend thủ công thành công
- [ ] PM2 startup đã được enable (`pm2 startup` và `pm2 save`)
- [ ] Đã push workflow file lên GitHub
- [ ] Workflow chạy thành công lần đầu
- [ ] Verify tất cả containers đang chạy: `docker ps`
- [ ] Verify tất cả PM2 processes đang chạy: `pm2 list`
- [ ] Backend API responding (kiểm tra endpoint)
- [ ] Frontend accessible qua browser

---

## 🌐 Ports và Services

### Pipeline (Builder-Layer-End):
| Service | Port | Description |
|---------|------|-------------|
| Neo4j HTTP | 7474 | Neo4j Browser UI |
| Neo4j Bolt | 7687 | Neo4j Database |
| Fuseki | 3030 | Apache Jena Triplestore |
| Redis | 6379 | Cache |
| PostgreSQL | 5432 | Stellio Database |
| Kafka | 9092 | Event Streaming |
| Stellio API Gateway | 8080 | NGSI-LD Context Broker |

### Business Layer:
| Service | Port | Description |
|---------|------|-------------|
| Backend API | 3000 | Node.js/Express API |
| Frontend | 4173 | React/Vite App (preview mode) |

### Firewall Rules (nếu cần):
```bash
# Allow necessary ports
sudo ufw allow 3000/tcp  # Backend
sudo ufw allow 4173/tcp  # Frontend
sudo ufw allow 8080/tcp  # Stellio
sudo ufw allow 22/tcp    # SSH
sudo ufw enable
sudo ufw status
```

---

**Chúc bạn deploy thành công! 🎉**
