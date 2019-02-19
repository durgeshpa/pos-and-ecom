cp /tmp/.env /home/ubuntu/project/retailer-backend/.env
cp -R /home/ubuntu/projects/tmp/retailer-backend /home/ubuntu/projects/
source /home/ubuntu/projects/prod/bin/activate
cd /home/ubuntu/project/retailer-backend/
python manage.py makemigrations
python manage.py migrate

sudo supervisorctl restart all