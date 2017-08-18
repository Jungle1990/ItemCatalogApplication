Item Catalog Application
=============

# Overview
Item catalog application is a project form 'Full Stack Web Developer Nanodegree Program' of Udacity
It is mainly developed using flask, slqalchemy etc

# Folder structure
- vagrant/Vagrantfile
  vagrant configuration
- vagrant/catalog/setup_db.py
  database setup script
- vagrant/catalog/model.py
  define Catalog and Item model
- vagrant/catalog/data.py
  fake some data, used by setup_db.py to feed data into database
- vagrant/catalog/client_secrets.json
  google api client secrets file
- vagrant/catalog/application.py
  provide all api and logic for this project
- vagrant/catalog/templates/*
  html templates
- vagrant/catalog/css/*
  css files

# How to run this project
- Setup environment using vagrant vm by running `vagrant up` under vagrant directory
- Initialize and feed fake data into database by running `python setup_db.py`
- Start up this project by running `python application.py`
- Go to "http://localhost:8000" to view this item catalog application