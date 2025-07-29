# Build book

## 1. Connect to the Azure VM using SSH key

### 1.1 Change mode of the SSH key generated in Azure to have the mode 400 
- user: read-only
- group: no access
- other: no access

```bash
chmod 400 ~/Documents/projects/study_bites/my_key.pem
```

### 1.2 Upload the source code to remote machine
```bash
sftp -i ~/Documents/projects/study_bites/my_key.pem myuser@4.246.67.29
put /Users/myuser/Documents/projects/study_bites/study_bites.zip

bye
```

### 1.3 Log onto the remote machine
```bash
ssh -i ~/Documents/projects/study_bites/my_key.pem myuser@4.246.67.29
sudo apt install unzip
unzip study_bites.zip 

cd study_bites/
ls
```

## 2. Setup env variable

First get the keys from local Mac
```bash
cat ~/.zshrc    
```

```bash
echo "export FLASK_SECRET_KEY=<my_secret_key>" > ~/.bashrc
echo "export QLOO_API_KEY=<my_qloo_key>" >> ~/.bashrc
source ~/.bashrc
```

## 3. Install python packages

Use the Python Pillow image library for processing images using the [Hugging Face zer0int/CLIP-GmP-ViT-L-14 model](https://huggingface.co/zer0int/CLIP-GmP-ViT-L-14), which is fine tuned from the OpenAI model [ openai/clip-vit-large-patch14](https://huggingface.co/openai/clip-vit-large-patch14).

```bash
sudo apt update
sudo apt install python3 python3-pip -y
python3 --version
pip3 --version

sudo apt install python3.12-venv
python3 -m venv myenv
source myenv/bin/activate

pip3 install transformers torch 
pip3 install flask
pip3 install Pillow

readlink -f /home/myuser/study_bites/myenv/bin/python3.12
sudo setcap 'cap_net_bind_service=+ep' /usr/bin/python3.12
```

## 4. Start development server for testing
```bash
python3 -m flask --app app.py --debug run --port 2000 --host=0.0.0.0
```

To run as a background service:
```bash
cd study_bites/

source myenv/bin/activate

nohup python3 app.py > flask.log 2>&1 &
```

To stop the running application at the background:
```bash
ps -aux | grep mindful
kill -9 <pid>
```


## 5. Web server deployment
### 5.1 Configure Nginx proxy listening on HTTP port 80
```bash
sudo apt update
sudo apt install nginx

sudo vi /etc/nginx/sites-enabled/flask_app
```

```
server {
    listen 80;
    server_name qloo.simplyjec.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
sudo systemctl start nginx
```

### 5.2 Install Let's Encypt SSL certificate and listen on HTTPS port 443
```bash
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d qloo.simplyjec.com
sudo systemctl restart nginx
```

## 6. Production deployment as a wheel package running on Gunicorn
### 6.1 Create a `pyproject.toml` configuration file with Flask/ML dependencies

```toml
[build-system]
requires = ["setuptools>=61.0", "wheel"]
build-backend = "setuptools.build_meta"

[project]
name = "study_bites"
version = "1.0.1"
description = "Student bites powered by Qloo Taste AI™ API and Hugging Face Image LLM"
requires-python = ">=3.12"
dependencies = [
    "flask",
    "requests",
    "transformers",
    "torch",
    "pillow"
]

[tool.setuptools]
include-package-data = true

[tool.setuptools.package-data]
study_bites = [
  "templates/*.html",
  "static/**/*"
]

```

### 6.2 Generate a wheel package

```bash
source ~/bin/activate
pip3 install build
python3 -m build
```

This will create:
 - dist/
   - study_bites-1.0.1-py3-none-any.whl

### 6.3 Upload to the server
```bash
scp -i ~/Documents/projects/my_key.pem dist/study_bites-1.0.1-py3-none-any.whl myuser@4.246.67.29:/home/myuser  study_bites-1.0.1-py3-none-any.whl
```


### 6.4 Deploy on the Gunicon server
```bash
python3 -m venv myenv
source myenv/bin/activate
pip3 install study_bites-1.0.1-py3-none-any.whl
pip3 install gunicorn

sudo mkdir -p /var/log/study_bites
sudo chown myuser:www-data /var/log/study_bites

gunicorn -w 5 -b 0.0.0.0:5000 study_bites.app:app \
  --access-logfile /var/log/study_bites/access.log \
  --error-logfile /var/log/study_bites/error.log \
  --log-level info \
  --daemon
```

To stop the application for redeployment.
```bash
ps aux | grep gunicorn
kill -9 <pid>
```

### 6.5 Auto-start on Ubuntu server reboot
```bash
sudo vi /etc/systemd/system/study_bites.service
```

```
[Unit]
Description=StudyBites Gunicorn Service
After=network.target

[Service]
EnvironmentFile=/home/myuser/.env
User=myuser
Group=www-data
WorkingDirectory=/home/myuser/study_bites
ExecStart=/home/myuser/myenv/bin/gunicorn \
    -w 5 -b 0.0.0.0:5000 study_bites.app:app \
    --access-logfile /var/log/study_bites/access.log \
    --error-logfile /var/log/study_bites/error.log \
    --log-level info

[Install]
WantedBy=multi-user.target
```

Where `/home/myuser/.env` contains:
- export FLASK_SECRET_KEY=<my_secret_key>
- export QLOO_API_KEY=<my_api_key>

```bash
sudo systemctl daemon-reexec
sudo systemctl daemon-reload
sudo systemctl enable study_bites
sudo systemctl start study_bites

sudo systemctl status study_bites
```

### 6.6 Verify the application

Stop the VM then boot the machine again.
```bash
sudo shutdown
exit
```

Access `https://qloo.simplyjec.com/` in a browser and the happy journey starts.

Double confirm by checking access log
```bash
tail -f /var/log/study_bites/access.log
```
