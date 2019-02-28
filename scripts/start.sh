cp -a /home/ubuntu/project/tmp/retailer_backend/. /home/ubuntu/project/retailer-backend
cp /tmp/.env /home/ubuntu/project/retailer-backend/.env
source /home/ubuntu/project/prod/bin/activate
cd /home/ubuntu/project/retailer-backend/
python manage.py migrate --fake
python manage.py makemigrations
python manage.py migrate

sudo supervisorctl restart all