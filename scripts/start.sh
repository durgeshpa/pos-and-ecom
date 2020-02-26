source /home/ubuntu/project/prod/bin/activate
cd /home/ubuntu/project/retailer-backend/

#fake all previous migrations
python manage.py makemigrations
python manage.py migrate --fake

#pull latest code
/bin/su -c "/home/ubuntu/project/scripts/pull.sh" - ubuntu

#create new migrations and migrate
pip install -r requirements.txt

python manage.py makemigrations
python manage.py makemigrations services
python manage.py migrate

python manage.py collectstatic --noinput --no-post-process
#restart server
sudo supervisorctl restart all
