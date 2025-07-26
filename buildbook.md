# Build book
## 1. Setup env variable
```
echo "export FLASK_SECRET_KEY=<my_secret_key>" > ~/.bashrc
echo "export QLOO_API_KEY=<my_qloo_key>" >> ~/.bashrc
source ~/.bashrc
```

## 2. Install python packages
```
pip install transformers torch
```