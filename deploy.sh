#!/bin/bash
# PuriGuide Deployment Script for Contabo
# Run as: ./deploy.sh

set -e

echo "=========================================="
echo "PuriGuide Deployment Script v2"
echo "=========================================="

# Configuration
REPO_URL="https://github.com/pritishpattanaik/stayinpuri.git"
DEPLOY_DIR="/opt/staywith_puri/puriguide"
SERVICE_NAME="stayinpuri-web"
DB_NAME="stayinpuri"
DB_USER="stayinpuri"
DB_PASS="stayinpuri123"  # Database password

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

print_success() { echo -e "${GREEN}✓ $1${NC}"; }
print_error() { echo -e "${RED}✗ $1${NC}"; }
print_info() { echo -e "${YELLOW}→ $1${NC}"; }

# Check if running as root
if [ "$EUID" -ne 0 ]; then
    print_error "Please run as root"
    exit 1
fi

print_info "Step 1: Installing system dependencies..."
dnf install -y python3.9 python3.9-pip python3.9-devel postgresql-devel python3-dotenv 2>/dev/null || \
yum install -y python39 python39-pip python39-devel postgresql-devel python3-dotenv 2>/dev/null || \
echo "Dependencies already installed or different package manager"
print_success "System dependencies ready"

print_info "Step 2: Setting up PostgreSQL..."
su - postgres -c "psql -c \"DROP DATABASE IF EXISTS ${DB_NAME};\"" 2>/dev/null || true
su - postgres -c "psql -c \"CREATE DATABASE ${DB_NAME};\"" 2>/dev/null || echo "Database may exist"
su - postgres -c "psql -c \"DROP USER IF EXISTS ${DB_USER};\"" 2>/dev/null || true
su - postgres -c "psql -c \"CREATE USER ${DB_USER} WITH PASSWORD '${DB_PASS}';\"" 2>/dev/null || echo "User may exist"
su - postgres -c "psql -c \"GRANT ALL PRIVILEGES ON DATABASE ${DB_NAME} TO ${DB_USER};\"" 2>/dev/null
print_success "Database '${DB_NAME}' ready"

print_info "Step 3: Getting repository..."
mkdir -p /opt/staywith_puri
cd /opt/staywith_puri

if [ -d "$DEPLOY_DIR" ]; then
    print_info "Updating existing repository..."
    cd "$DEPLOY_DIR"
    git pull origin main || print_error "Git pull failed, trying fresh clone..."
fi

if [ ! -d "$DEPLOY_DIR" ] || [ ! -d "$DEPLOY_DIR/backend" ]; then
    print_info "Cloning repository..."
    rm -rf "$DEPLOY_DIR"
    git clone "$REPO_URL" "$DEPLOY_DIR" || {
        print_error "Git clone failed, downloading zip..."
        curl -L https://github.com/pritishpattanaik/stayinpuri/archive/refs/heads/main.zip -o /tmp/puriguide.zip
        unzip -o /tmp/puriguide.zip -d /opt/staywith_puri/
        mv /opt/staywith_puri/stayinpuri-main "$DEPLOY_DIR"
        rm /tmp/puriguide.zip
    }
fi
cd "$DEPLOY_DIR"
print_success "Repository ready"

print_info "Step 4: Creating Python virtual environment..."
cd "$DEPLOY_DIR/backend"
rm -rf venv
python3.9 -m venv venv
source venv/bin/activate
pip install --upgrade pip -q
pip install -r requirements.txt -q
print_success "Python environment ready"

print_info "Step 5: Creating .env file..."
cat > "$DEPLOY_DIR/backend/.env" << EOF
# App
APP_NAME=PuriGuide
APP_ENV=production
APP_PORT=3005
APP_HOST=127.0.0.1

# Database
DB_HOST=localhost
DB_PORT=5432
DB_NAME=${DB_NAME}
DB_USER=${DB_USER}
DB_PASSWORD=${DB_PASS}
DATABASE_URL=postgresql+asyncpg://${DB_USER}:${DB_PASS}@localhost:5432/${DB_NAME}

# CORS
CORS_ORIGINS=https://travel.placsoft.in,https://www.travel.placsoft.in,http://travel.placsoft.in

# Booking settings
BOOKING_REF_PREFIX=PG
PROPERTY_1_NAME=Asiyana
PROPERTY_1_SLUG=asiyana
PROPERTY_1_CAPACITY=4
PROPERTY_1_PRICE=2500
PROPERTY_1_BEDROOMS=2
PROPERTY_2_NAME=Tulsi Vihar
PROPERTY_2_SLUG=tulsi-vihar
PROPERTY_2_CAPACITY=3
PROPERTY_2_PRICE=2000
PROPERTY_2_BEDROOMS=2

# Site meta
SITE_NAME=PuriGuide
SITE_TAGLINE=Your Complete Puri Travel Companion
SITE_CONTACT_EMAIL=contact@puriguide.in
CARETAKER_NAME=Caretaker
CARETAKER_PHONE=+91XXXXXXXXXX
SITE_PHONE=+91XXXXXXXXXX
EOF

# Also update alembic.ini with correct database URL
sed -i "s|postgresql://.*@localhost:5432/.*|postgresql://${DB_USER}:${DB_PASS}@localhost:5432/${DB_NAME}|" alembic.ini

print_success ".env and alembic.ini configured"

print_info "Step 6: Running database migrations..."
source venv/bin/activate
alembic upgrade head
print_success "Migrations completed"

print_info "Step 7: Seeding initial data..."
python -m app.seed
print_success "Data seeded"

print_info "Step 8: Creating systemd service..."
cat > "/etc/systemd/system/${SERVICE_NAME}.service" << EOF
[Unit]
Description=PuriGuide Travel API
After=network-online.target postgresql.service
Wants=network-online.target

[Service]
Type=simple
User=root
WorkingDirectory=${DEPLOY_DIR}/backend
EnvironmentFile=${DEPLOY_DIR}/backend/.env
ExecStart=${DEPLOY_DIR}/backend/venv/bin/uvicorn app.main:app --host 127.0.0.1 --port 3005
Restart=on-failure
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

print_info "Step 9: Reloading and restarting service..."
systemctl daemon-reload
systemctl enable "$SERVICE_NAME"
systemctl restart "$SERVICE_NAME"
sleep 3
print_success "Service restarted"

print_info "Step 10: Checking service status..."
systemctl status "$SERVICE_NAME" --no-pager -l || true

print_info "Step 11: Testing API..."
sleep 2
echo ""
echo "=== Testing /api/health ==="
curl -s http://localhost:3005/api/health || print_error "Health check failed"
echo ""
echo "=== Testing /api/properties/ ==="
curl -s http://localhost:3005/api/properties/ | head -c 200 || print_error "Properties endpoint failed"
echo ""
echo "=== Testing /api/health ==="
curl -s http://localhost:3005/api/health || print_error "Health check failed"
echo ""

echo ""
echo "=========================================="
print_success "Deployment completed!"
echo "=========================================="
echo ""
echo "Service: systemctl status ${SERVICE_NAME}"
echo "Logs: journalctl -u ${SERVICE_NAME} -f"
echo "Site: http://travel.placsoft.in"
echo "API: http://travel.placsoft.in/docs"
echo ""
