cp /home/ubuntu/project/retailer-backend/.env /tmp/.env
if [ -d /home/ubuntu/project/retailer-backend ]; then
  sudo rm -R /home/ubuntu/project/retailer-backend
  mkdir /home/ubuntu/project/retailer-backend
fi