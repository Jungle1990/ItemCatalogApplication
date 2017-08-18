#!/usr/bin/env python

from flask import Flask, render_template, request, make_response, redirect, url_for
from flask import session as login_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, desc
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
from model import Catalog, Item
import httplib2, json, requests
import random, string

CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']

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
def index():
    return redirect(url_for('home')) 

@app.route('/catalog')
def home():
    username = login_session.get('username', None)
    state = ''.join(random.choice(string.ascii_uppercase + string.digits) for x in xrange(32))
    login_session['state'] = state

    connect_db()
    catalogs = session.query(Catalog).all()
    items = session.query(Item).order_by(desc(Item.date)).all()
    catalogs_display = [{'id' : catalog.id, 'name' : catalog.name} for catalog in catalogs]
    items_display = [{'id' : item.id, 'title' : item.title, 'catalog' : item.catalog.name} for item in items]
    items_summary = 'Latest Items'
    disconnect_db()
    return render_template('home.html', catalogs_display = catalogs_display, items_display = items_display, items_summary = items_summary, state = state, username = username)

@app.route('/gconnect', methods=['POST'])
def gconnect():
    # Validate state token
    if request.args.get('state') != login_session['state']:
        response = make_response(json.dumps('Invalid state parameter.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Obtain authorization code
    code = request.data
    try:
    # Upgrade the authorization code into a credentials object
        oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
        oauth_flow.redirect_uri = 'postmessage'
        credentials = oauth_flow.step2_exchange(code)
    except FlowExchangeError:
        response = make_response(json.dumps('Failed to upgrade the authorization code.'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = ('https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token)
    h = httplib2.Http()
    result = json.loads(h.request(url, 'GET')[1])
    # If there was an error in the access token info, abort.
    if result.get('error') is not None:
        response = make_response(json.dumps(result.get('error')), 500)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is used for the intended user.
    gplus_id = credentials.id_token['sub']
    if result['user_id'] != gplus_id:
        response = make_response(
        json.dumps("Token's user ID doesn't match given user ID."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
        json.dumps("Token's client ID does not match app's."), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(json.dumps('Current user is already connected.'), 200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token': credentials.access_token, 'alt': 'json'}
    answer = requests.get(userinfo_url, params=params)
    data = answer.json()
    login_session['username'] = data['name']

    return redirect(url_for('home'))

@app.route('/gdisconnect')
def gdisconnect():
    if login_session['access_token'] is None:
        response = make_response(json.dumps('User does not login'), 401)
        response.headers['Content-Type'] = 'application/json'
        return response

    url = 'https://accounts.google.com/o/oauth2/revoke?token=%s' % login_session['access_token']
    h = httplib2.Http()
    response = h.request(url, 'GET')
    result = response[0]
    content = response[1]
    if result['status'] == '200':
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        return redirect(url_for('home'))
    else:
        print result
        print content
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        response = make_response(json.dumps('Fail to logout', 400))
        response.headers['Content-Type'] = 'application/json'
        return response

@app.route('/catalog/<id>/')
def get_catalog_items(id):
    connect_db()
    catalogs = session.query(Catalog).all()
    selected_catalog = session.query(Catalog).filter_by(id = id).one()
    items = selected_catalog.items
    catalogs_display = [{'id' : catalog.id, 'name' : catalog.name} for catalog in catalogs]
    items_display = [{'id' : item.id, 'title' : item.title} for item in items]
    items_summary = '{0} Items ({1} items)'.format(selected_catalog.name, len(items_display))
    disconnect_db()
    return render_template('home.html', catalogs_display = catalogs_display, items_display = items_display, items_summary = items_summary)

@app.route('/item/<id>')
def read_item(id):
    connect_db()
    item = session.query(Item).filter_by(id = id).one()
    item_display = {'id' : item.id, 'title' : item.title, 'desc' : item.desc}
    disconnect_db()
    return render_template('read_item.html', item_display = item_display)

@app.route('/item/create', methods=['GET', 'POST'])
def create_item():
    if request.method == 'GET':
        connect_db()
        catalogs = session.query(Catalog).all()
        catalogs_display = [{'id' : catalog.id, 'name' : catalog.name} for catalog in catalogs]
        disconnect_db()
        return render_template('create_item.html', catalogs_display = catalogs_display)

    if request.method == 'POST':
        connect_db()
        title = request.form['title']
        results = session.query(Item).filter_by(title = title).all()
        if len(results) > 0:
            disconnect_db()
            return redirect(url_for('createItem'))

        catalog = session.query(Catalog).filter_by(id = request.form['catalog_id']).one()
        catalog.items.append(Item(title, request.form['desc']))
        session.add(catalog)
        session.commit()
        disconnect_db()
        return redirect(url_for('home'))

@app.route('/item/<id>/edit', methods=['GET', 'POST'])
def edit_item(id):
    connect_db()
    catalogs = session.query(Catalog).all()
    item = session.query(Item).filter_by(id = id).one()
    catalogs_display = [{'id' : catalog.id, 'name' : catalog.name} for catalog in catalogs]

    if request.method == 'POST':
        print '1'
        if request.form['title'] is not None:
            item.title = request.form['title']
        if request.form['desc'] is not None:
            item.desc = request.form['desc']
        if request.form['catalog_id'] is not None:
            item.catalog_id = request.form['catalog_id']
        print '2'
        session.add(item)
        session.commit()
        disconnect_db()
        return redirect(url_for('read_item', id = id))
    
    if request.method == 'GET':
        disconnect_db()
        username = login_session.get('username', None)
        item_display = {'id' : item.id, 'title' : item.title, 'desc' : item.desc, 'catalog_id' : item.catalog_id}
        return render_template('edit_item.html', item_display = item_display, catalogs_display = catalogs_display, username = username)

@app.route('/item/<id>/delete', methods=['GET', 'POST'])
def delete_item(id):
    connect_db()
    item = session.query(Item).filter_by(id = id).one()

    if request.method == 'POST':
        session.delete(item)
        session.commit()
        disconnect_db()
        return redirect(url_for('home'))

    if request.method == 'GET':
        disconnect_db()
        item_display = {'id' : item.id, 'title' : item.title}
        username = login_session.get('username', None)
        return render_template('delete_item.html', item_display = item_display, username = username)

if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    app.run(host='0.0.0.0', port=8000)
