if [ -d /home/ubuntu/project/retailer-backend ]; then
  sudo rm -R /home/ubuntu/project/retailer-backend
  mv /home/ubuntu/project/tmp/retailer-backend /home/ubuntu/project/retailer-backend
  sudo rm -R /home/ubuntu/project/tmp
fi