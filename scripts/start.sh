cp -R /home/ubuntu/project/tmp/retailer_backend /home/ubuntu/project/retailer-backend
cp /tmp/.env /home/ubuntu/project/retailer-backend/.env
source /home/ubuntu/projects/prod/bin/activate
cd /home/ubuntu/project/retailer-backend/
python manage.py makemigrations
python manage.py migrate

sudo supervisorctl restart all