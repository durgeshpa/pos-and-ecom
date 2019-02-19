cp -R /home/ubuntu/projects/tmp/retailer_backend /home/ubuntu/projects/retailer-backend
cp /tmp/.env /home/ubuntu/project/retailer-backend/.env
source /home/ubuntu/projects/prod/bin/activate
cd /home/ubuntu/project/retailer-backend/
python manage.py makemigrations
python manage.py migrate

sudo supervisorctl restart all