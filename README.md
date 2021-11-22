# GramFactory
This repo includes Django Backend. 
# Installation

  - Copy the env.sample file to .env and add credentials.
  - Activate a new virtualenv and install the required packages using:
  - ```$ pip install -r requirements.txt```
  
# Errors and Solutions
 If you are facing the following error while installation:
 ```python setup.py egg_info" failed with error code 1```
 On Linux:
 ```sudo apt-get install libmysqlclient-dev```
 On Mac:
 ```brew install mysql```
 
 # How to run db_script for cart update


create database mydb;
create user myuser;
GRANT permissions ON DATABASE dbname TO username;
 
 python manage.py shell or ./manage.py shell
 exec(open('db_changes/order_history_db_changes.py').read())

