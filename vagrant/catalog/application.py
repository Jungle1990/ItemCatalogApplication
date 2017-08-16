#!/usr/bin/env python

from flask import Flask, render_template
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, desc
from model import Catalog, Item

app = Flask(__name__)

engine = None
session = None

def connect_db():
	global engine, session
	engine = create_engine('sqlite:///catalog.db')
	Session = sessionmaker(bind=engine)
	session = Session()

def disconnect_db():
	session.close()
	engine.dispose()

@app.route('/')
def home():
	connect_db()
	catalogs = session.query(Catalog).all()
	items = session.query(Item).order_by(desc(Item.date)).all()
	catalogs_display = [{'id' : catalog.id, 'name' : catalog.name} for catalog in catalogs]
	items_display = [{'id' : item.id, 'title' : item.title, 'catalog' : item.catalog.name} for item in items]
	disconnect_db()
	return render_template('home.html', catalogs_display = catalogs_display, items_display = items_display)

if __name__ == '__main__':
	app.run(host='0.0.0.0', port=8000)