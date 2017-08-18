#!/usr/bin/env python

from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import ForeignKey, Column, Integer, String, DateTime
from datetime import datetime

Base = declarative_base()

class Catalog(Base):
    """Define category schema"""

    __tablename__ = 'catalog'

    id = Column(Integer, primary_key = True)
    name = Column(String)
    date = Column(DateTime, default = datetime.now(), onupdate = datetime.now)

    items = relationship("Item", back_populates = "catalog")

    def __init__(self, name):
        self.name = name

class Item(Base):
    """Define item schema"""

    __tablename__ = 'item'

    id = Column(Integer, primary_key = True)
    title = Column(String)
    desc = Column(String)
    date = Column(DateTime, default = datetime.now(), onupdate = datetime.now)

    catalog_id = Column(Integer, ForeignKey('catalog.id'))
    catalog = relationship("Catalog", back_populates = "items")

    def __init__(self, title, desc):
        self.title = title
        self.desc = desc

def create_catalog_with_items(catalog_name, items):
    catalog = Catalog(catalog_name)
    for item_title, item_desc in items.items():
        catalog.items.append(Item(item_title, item_desc))

    return catalog