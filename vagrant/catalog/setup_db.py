#!/usr/bin/env python

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from model import Base, Catalog, Item, create_catalog_with_items
from data import fake_data


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
