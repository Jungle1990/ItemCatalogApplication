#!/usr/bin/env python

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy import ForeignKey, Column, Integer, String, DateTime, create_engine
from datetime import datetime
from data import fake_data

Base = declarative_base()

class Catalog(Base):
	"""Define category schema"""

	__tablename__ = 'catalog'

	id = Column(Integer, primary_key=True)
	name = Column(String)
	date = Column(DateTime, default=datetime.now(), onupdate=datetime.now())

	items = relationship("Item", back_populates="catalog")

	def __init__(self, name):
		self.name = name

class Item(Base):
	"""Define item schema"""

	__tablename__ = 'item'

	id = Column(Integer, primary_key=True)
	title = Column(String)
	desc = Column(String)
	date = Column(DateTime, default=datetime.now(), onupdate=datetime.now())

	catalog_id = Column(Integer, ForeignKey('catalog.id'))
	catalog = relationship("Catalog", back_populates="items")

	def __init__(self, title, desc):
		self.title = title
		self.desc = desc

def create_catalog_with_items(catalog_name, items):
	catalog = Catalog(catalog_name)
	for item_name, item_desc in items.items():
		catalog.items.append(Item(item_name, item_desc))

	return catalog

def setup_db():
	# Create engine
	engine = create_engine('sqlite:///catalog.db')
	# Create catalog and item table
	Base.metadata.create_all(engine)
	# Create session
	Session = sessionmaker(bind=engine)
	session = Session()
	# Clear catalog and item in database
	session.query(Catalog).delete()
	session.query(Item).delete()
	# Get fake catalog and add to database
	for catalog, items in fake_data().items():
		session.add(create_catalog_with_items(catalog, items))
	# Commit the change
	session.commit()
	# Close session
	session.close()
	# Dispose engine
	engine.dispose()

if __name__ == '__main__':
	setup_db()