source /home/ubuntu/project/prod/bin/activate
cd /home/ubuntu/project/retailer-backend/
git pull origin master
python manage.py migrate --fake
python manage.py makemigrations
python manage.py migrate

sudo supervisorctl restart all