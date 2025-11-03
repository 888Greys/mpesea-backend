# M-Pesa Spending Tracker - Backend

FastAPI backend that receives M-Pesa SMS from Android app, parses transactions, tracks spending limits, and sends intelligent Slack notifications.

## Features
- 🎯 Webhook endpoint to receive SMS from Android app
- 📊 Intelligent M-Pesa SMS parser (handles sent, received, withdrawn, airtime, etc.)
- 💾 SQLite/PostgreSQL database for transaction history
- 🤖 Spending agent with daily limit tracking
- 💬 Slack notifications with smart messages
- 📈 Weekly spending summaries

## Quick Start on VM

### 1. Install Dependencies
```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Python 3.11 (if not installed)
sudo apt install python3.11 python3.11-venv python3-pip -y

# Install PostgreSQL (optional - can use SQLite)
sudo apt install postgresql postgresql-contrib -y
```

### 2. Setup Project
```bash
cd ~
mkdir mpesa-backend
cd mpesa-backend

# Upload all files from Windows to VM
# Use: scp, rsync, git clone, or any transfer method

# Create virtual environment
python3.11 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 3. Configure Environment
```bash
# Copy example env file
cp .env.example .env

# Edit configuration
nano .env
```

**Required settings in `.env`:**
```bash
# Database (use SQLite for simplicity)
DATABASE_URL=sqlite:///./mpesa_tracker.db

# Slack Webhook (get from Slack)
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL

# Daily spending limit (in KSH)
DAILY_LIMIT=2000

# Server settings
HOST=0.0.0.0
PORT=8000
```

### 4. Run the Server
```bash
# Activate venv
source venv/bin/activate

# Run server
python3 run.py
```

Server will start on `http://YOUR_VM_IP:8000`

### 5. Setup as Systemd Service (Run on boot)
```bash
sudo nano /etc/systemd/system/mpesa-tracker.service
```

```ini
[Unit]
Description=M-Pesa Spending Tracker
After=network.target

[Service]
Type=simple
User=kip
WorkingDirectory=/home/kip/mpesa-backend
Environment="PATH=/home/kip/mpesa-backend/venv/bin"
ExecStart=/home/kip/mpesa-backend/venv/bin/python3 run.py
Restart=always

[Install]
WantedBy=multi-user.target
```

```bash
sudo systemctl daemon-reload
sudo systemctl enable mpesa-tracker
sudo systemctl start mpesa-tracker
sudo systemctl status mpesa-tracker
```

### 6. Setup Nginx Reverse Proxy (Optional but recommended)
```bash
sudo apt install nginx -y
sudo nano /etc/nginx/sites-available/mpesa-tracker
```

```nginx
server {
    listen 80;
    server_name yourdomain.com;

    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }

    location /webhook/sms {
        proxy_pass http://127.0.0.1:8000/webhook/sms;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo ln -s /etc/nginx/sites-available/mpesa-tracker /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx
```

### 7. Setup SSL with Certbot (For HTTPS)
```bash
sudo apt install certbot python3-certbot-nginx -y
sudo certbot --nginx -d yourdomain.com
```

## Slack Webhook Setup

1. Go to https://api.slack.com/apps
2. Create New App → From scratch
3. Add features → Incoming Webhooks → Activate
4. Add New Webhook to Workspace → Select channel
5. Copy Webhook URL
6. Add to `.env` file

## API Endpoints

- `GET /` - Health check
- `POST /webhook/sms` - Receive SMS from Android app
- `GET /status` - Current spending status
- `GET /transactions` - Recent transactions
- `GET /summary/weekly` - Weekly summary
- `POST /test/slack` - Test Slack integration
- `GET /health` - System health check

## Testing

### Test from Android App
1. Configure webhook URL in app: `https://yourdomain.com/webhook/sms`
2. Click "Test Webhook" button
3. Check server logs and Slack

### Manual Test
```bash
curl -X POST http://YOUR_VM_IP:8000/webhook/sms \
  -H "Content-Type: application/json" \
  -d '{
    "sender": "MPESA",
    "message": "RK12AB34CD confirmed. You have sent Ksh500.00 to JOHN DOE. New M-PESA balance is Ksh1,234.56.",
    "timestamp": 1699000000000
  }'
```

## Project Structure
```
mpesa-backend/
├── app/
│   ├── __init__.py
│   ├── main.py          # FastAPI app & routes
│   ├── config.py        # Settings management
│   ├── database.py      # Database models & session
│   ├── parser.py        # M-Pesa SMS parser
│   ├── agent.py         # Spending analysis agent
│   └── slack.py         # Slack integration
├── tests/
├── .env                 # Configuration (create from .env.example)
├── requirements.txt
├── run.py              # Server runner
└── README.md
```

## Logs
```bash
# View systemd logs
sudo journalctl -u mpesa-tracker -f

# View nginx logs
sudo tail -f /var/log/nginx/access.log
sudo tail -f /var/log/nginx/error.log
```

## Troubleshooting

**Port already in use:**
```bash
sudo lsof -i :8000
sudo kill -9 <PID>
```

**Can't connect from Android app:**
- Check firewall: `sudo ufw allow 8000`
- Verify server is running: `curl http://localhost:8000`
- Check VM IP is correct and accessible

**Slack not working:**
- Test webhook: `curl -X POST YOUR_SLACK_WEBHOOK -d '{"text":"test"}'`
- Check `.env` has correct webhook URL

## License
MIT
