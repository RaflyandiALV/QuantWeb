#!/bin/bash
# ==============================================================================
# SCRIPT DEPLOYMENT OTOMATIS CRV-BOT (KHUSUS UBUNTU/LINUX)
# ==============================================================================
# Cara pakai di VPS: 
# 1. Pindah ke folder crv-bot: cd ~/crv-bot
# 2. Beri hak akses eksekusi: chmod +x setup_vps.sh
# 3. Jalankan: ./setup_vps.sh
# ==============================================================================

echo "🚀 Memulai Setup CRV-BOT untuk VPS Ubuntu..."
echo "--------------------------------------------------------"

# 1. Mengamankan file konfigurasi rahasia
if [ -f ".python_config_cache" ]; then
    echo "🔒 Mengunci file .python_config_cache (Lapis 2 Security)..."
    chmod 600 .python_config_cache
else
    echo "⚠️ Peringatan: File .python_config_cache tidak ditemukan!"
    echo "Tolong pastikan Anda sudah mengupload file tersebut."
fi

# 2. Update sistem dan install python environment (jika belum ada)
echo "📦 Menginstall dependencies sistem Python (memerlukan password 'sudo' jika diminta)..."
sudo apt update && sudo apt install -y python3 python3-venv python3-pip

# 3. Membuat virtual environment
if [ ! -d "venv" ]; then
    echo "🐍 Membuat Python Virtual Environment (venv)..."
    python3 -m venv venv
fi

# 4. Install requirements
echo "📚 Menginstall modul Python dari requirements.txt..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# 5. Membuat Service systemd agar bot berjalan 24/7 dan auto-restart
echo "⚙️ Membuat Daemon Service (systemd) supaya bot menyala 24/7 otomatis..."
SERVICE_FILE="/etc/systemd/system/crvbot.service"
CURRENT_DIR=$(pwd)
CURRENT_USER=$(whoami)

sudo bash -c "cat > $SERVICE_FILE" <<EOL
[Unit]
Description=Trading Bot CRV-USDT
After=network.target

[Service]
Type=simple
User=${CURRENT_USER}
WorkingDirectory=${CURRENT_DIR}
ExecStart=${CURRENT_DIR}/venv/bin/python bot_runner.py
Restart=always
RestartSec=10
StandardOutput=append:${CURRENT_DIR}/bot.log
StandardError=append:${CURRENT_DIR}/bot_error.log

[Install]
WantedBy=multi-user.target
EOL

# 6. Mengaktifkan dan Menjalankan Service
echo "🟢 Menjalankan bot di background..."
sudo systemctl daemon-reload
sudo systemctl enable crvbot
sudo systemctl restart crvbot

echo "--------------------------------------------------------"
echo "✅ SETUP SELESAI!"
echo "Bot CRV-USDT sekarang sudah berjalan di VPS Anda secara 24/7."
echo ""
echo "Perintah berguna untuk memonitor bot:"
echo "1. Cek status bot:    sudo systemctl status crvbot"
echo "2. Lihat log live:    tail -n 50 -f bot.log"
echo "3. Matikan bot:       sudo systemctl stop crvbot"
echo "=============================================================================="
