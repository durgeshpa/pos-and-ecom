source /home/ubuntu/project/prod/bin/activate
cd /home/ubuntu/project/retailer-backend/

#fake all previous migrations
python manage.py makemigrations
python manage.py migrate --fake

echo "############################-----User Is ------####### "
echo "$USER"
#pull latest code
git pull

#create new migrations and migrate
python manage.py makemigrations
python manage.py migrate

#restart server
sudo supervisorctl restart all
