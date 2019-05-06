source /home/ubuntu/project/prod/bin/activate
cd /home/ubuntu/project/retailer-backend/
python manage.py migrate --fake
git pull
python manage.py makemigrations
python manage.py migrate
sudo supervisorctl restart all
