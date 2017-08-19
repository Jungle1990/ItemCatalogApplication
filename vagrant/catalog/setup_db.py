#!/usr/bin/env python

from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine
from model import Base, Catalog, Item, User
from data import fake_catalog, fake_user


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
    session.query(User).delete()
    # Get fake catalog and user, then add to database
    user_info = fake_user()
    user = User(user_info['name'], user_info['email'], user_info['gplus_id'])
    session.add(user)
    session.commit()
    for catalog, items in fake_catalog().items():
        catalog = Catalog(catalog)
        session.add(catalog)
        session.commit()
        for item_title, item_desc in items.items():
            item = Item(item_title, item_desc)
            item.catalog_id = catalog.id
            item.user_id = user.id
            session.add(item)
            session.commit()
    # Close session
    session.close()
    # Dispose engine
    engine.dispose()

if __name__ == '__main__':
    setup_db()
