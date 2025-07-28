# Build book

## 1. Connect to the Azure VM using SSH key

### 1.1 Change mode of the SSH key generated in Azure to have the mode 400 (user: read-only, group: no access, other: no access)
```
chmod 400 ~/Documents/projects/mindful_meals/my_key.pem
```

### 1.2 Upload the source code to remote machine
```
sftp -i ~/Documents/projects/mindful_meals/my_key.pem myuser@4.155.11.254
put /Users/myuser/Documents/projects/mindful_meals/mindful_meals.zip

bye
```

### 1.3 Log onto the remote machine
```
ssh -i ~/Documents/projects/mindful_meals/my_key.pem myuser@4.155.11.254
sudo apt install unzip
unzip mindful_meals.zip 

cd mindful_meals/
ls
```

## 2. Setup env variable

First get the keys from local Mac
```
cat ~/.zshrc    
```

```
echo "export FLASK_SECRET_KEY=<my_secret_key>" > ~/.bashrc
echo "export QLOO_API_KEY=<my_qloo_key>" >> ~/.bashrc
source ~/.bashrc
```

## 3. Install python packages
```
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

readlink -f /home/myuser/mindful_meals/myenv/bin/python3.12
sudo setcap 'cap_net_bind_service=+ep' /usr/bin/python3.12

python3 -m flask --app app.py --debug run --port 2000 --host=0.0.0.0
```

```
sudo apt update
sudo apt install nginx

sudo vi /etc/nginx/sites-enabled/flask_app
server {
    listen 80;
    server_name qloo.simplyjec.com;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}

sudo systemctl start nginx
```

Install SSL certificate
```
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d qloo.simplyjec.com
sudo systemctl restart nginx
```

## 4. Start instance to run in background
```
cd mindful_meals/

source myenv/bin/activate

nohup python3 app.py > flask.log 2>&1 &
```

To stop the running application at the background:
```
ps -aux | grep mindful
kill -9 <pid>
``

## 5. Stop machine
```
sudo shutdown
exit
```