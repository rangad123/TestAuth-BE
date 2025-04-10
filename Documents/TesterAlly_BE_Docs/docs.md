# TesterAlly - AI-Based Automation Testing Tool

## 1. Introduction
TesterAlly is an AI-powered automation testing tool designed to simplify test execution for desktop and web applications. With this new Windows installer approach, users can run the automation agent directly on their local machines, eliminating the need for cloud setup or manual deployment.

Users simply log in to https://testerally.ai, select their subscription plan, and download the Windows Installer (.exe). The installed agent connects securely to the cloud backend and executes tests as per project configurations.
---
## 2. Project Architecture
```
TestAuth-BE/
│-- TestAuth-BE/             # Django Backend Repository
│   │-- api/                   # API Application
│   │-- automation/            # Automation Application
|   |-- static/                # Django static file for FE build folder
|   |   |-- build/             # FE Build folder for single files
|   |-- staticfiles/           # Colleted static files after the command 
|   |   |-- build/             # Run the extensions with FE after Collect Static
│-- TestAuth-FE/             # React Frontend Repository
```
---
## 3. Technology Stack

- **Backend**: Django (REST API) with Gunicorn & Nginx
- **Frontend**: React
- **Automation**: PyAutoGUI, Replicate - OmniParser v2 Model
- **Remote Control**: Local windows - (PyGetWindows)
- **Database**: AWS RDS (Mysql)
- **Cloud Infrastructure**: AWS EC2 (t3.medium) with an Elastic IP (**13.48.64.40**)
- **Domain & Security**: Cloudflare (**testerally.ai**)

---
## 4. Installation Guide
### Step 1: Clone the Repositories
```sh
git clone https://github.com/rangad123/TestAuth-BE.git
cd TestAuth-BE

git clone https://github.com/rangad123/TestAuth-FE.git
cd TestAuth-FE
```

### Step 3: Set Up the Frontend (React)
```sh
# Move to Frontend Directory
cd ../TestAuth-FE

# Install Dependencies
npm install

# Start React Development Server
npm start

# Build the Frontend for single exe file\
npm run build

# Move the Build Folder to TestAuth-BE static folder
mv build TestAuth-BE/static/

```

### Step 2: Set Up the Backend (Django)
```sh
# Move to Backend Directory
cd TestAuth-BE

# Create a Virtual Environment
python3 -m venv venv
source venv/bin/activate  # For Linux/Mac
venv\Scripts\activate     # For Windows

# Install Required Dependencies
pip install -r requirements.txt

# Apply Migrations
python manage.py migrate

# Collect the static file with TestAuth-FE Build folder
python manage.py collectstatic

```
---
## 5. Configuring Gunicorn & Nginx on EC2
### Step 1: Connect to EC2 and Install Dependencies
```sh
ssh -i your-key.pem ubuntu@yourIPaddress
sudo apt update && sudo apt install -y python3-pip python3-venv nginx
```

---
### Step 2: Install Gunicorn & Start Django Server
```sh
cd /home/ubuntu/TesterAlly-BE
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

---
#### Gunicorn socket File Configuration
```sh
sudo nano /etc/systemd/system/gunicorn.socket

#Paste file

[[Unit]
Description=gunicorn socket

[Socket]
ListenStream=/run/gunicorn.sock

[Install]
WantedBy=sockets.target
```
---
#### Gunicorn Service File Configuration
```sh
sudo nano /etc/systemd/system/gunicorn.service

#Paste this file

[Unit]
Description=gunicorn daemon
Requires=gunicorn.socket
After=network.target

[Service]
Environment="DISPLAY=:1"
User=ubuntu
Group=www-data
WorkingDirectory=/home/ubuntu/TesterAlly-BE
ExecStart=/home/ubuntu/TesterAlly-BE/venv/bin/gunicorn \
          --access-logfile - \
          --workers 3 \
          --timeout 300 \
          --bind unix:/run/gunicorn.sock \
          testerally_be.wsgi:application

[Install]
WantedBy=multi-user.target

# Enable the configuration and restart socket
sudo systemctl start gunicorn.socket
sudo systemctl enable gunicorn.socket
```

---
### Step 3: Configure Nginx
```sh
sudo nano /etc/nginx/sites-available/nginx

#Paste File
# Frontend Nginx Config
server {
    listen 80;
    server_name testerally.ai;

    location / {
        autoindex on;
        root /var/www/vhosts/frontend/build;
        try_files $uri $uri/ /index.html;
    }
}

# Backend Nginx Config
server {
    listen 80;
    server_name api.testerally.ai;

   location = /favicon.ico {
        access_log off;
        log_not_found off;
    }

    # Serve static and media files (Django)
    location /staticfiles/ {
        alias /home/ubuntu/TesterAlly-BE/static;
    }

    location /media/ {
        alias /home/ubuntu/TesterAlly-BE/media/;
        autoindex on;
        allow all;
        access_log off;
        add_header Access-Control-Allow-Origin *;
        add_header X-Frame-Options SAMEORIGIN;
        add_header X-Content-Type-Options nosniff;
        expires 30d;
    }

    # Django Application (TesterAlly-BE)
    location / {
        include proxy_params;
        proxy_pass http://unix:/run/gunicorn.sock;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_read_timeout 300;  # ⏳ Increased timeout for Cloudflare
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    client_max_body_size 100M;
}

# Enable the configuration and restart Nginx
sudo systemctl daemon-reload
sudo systemctl restart nginx
sudo systemctl restart gunicorn
```

---
## 6. VNC Server Setup on EC2
### Step 1: Install VNC Server and XFCE4
```sh
sudo apt update
sudo apt install tightvncserver xfce4 xfce4-goodies dbus-x11 -y
```

### Step 2: Configure VNC Server
```sh
vncserver -kill :1
sudo rm -rf /tmp/.X1-lock /tmp/.X11-unix/X1
```

### Step 3: Edit .bashrc File for Auto Export Display Variable
```sh
nano ~/.bashrc
# Add the following line at the end of the file:
export DISPLAY=:1
source ~/.bashrc
```

### Step 4: Configure VNC Startup Script
```sh
nano ~/.vnc/xstartup
```

### Step 5: Set Permissions & Restart Services
```sh
chmod +x ~/.vnc/xstartup
rm -rf ~/.vnc/*.log ~/.vnc/*.pid
vncserver :1
```

### Step 6: Verify VNC Process
```sh
ps aux | grep Xtightvnc
ps aux | grep vnc
echo $DISPLAY
```

---
## 9. Troubleshooting
### Check Gunicorn Logs
```sh
sudo journalctl -u gunicorn -f
```

### Check Nginx Logs
```sh
sudo journalctl -u nginx --no-pager
```

### Restart Services
```sh
sudo systemctl restart nginx
sudo systemctl restart gunicorn
```

---
**© 2025 TesterAlly. All rights reserved.**

