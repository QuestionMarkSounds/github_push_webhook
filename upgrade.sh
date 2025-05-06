cd /home/ubuntu/couples_assistant

source /home/ubuntu/couples_assistant/.venv/bin/activate

git pull origin dev_server

pip3 install -r requirements.txt

sudo systemctl restart couples_assistant_bot.service

sudo systemctl restart couples_assistant_server.service