#!/usr/bin/env python

from flask import Flask, render_template, request
from flask import make_response, redirect, url_for, jsonify
from flask import session as login_session
from sqlalchemy.orm import sessionmaker
from sqlalchemy import create_engine, desc
from oauth2client.client import flow_from_clientsecrets
from oauth2client.client import FlowExchangeError
from time import strftime
from model import Catalog, Item, User
from functools import wraps
import httplib2
import json
import requests
import random
import string

CLIENT_ID = json.loads(
    open('client_secrets.json', 'r').read())['web']['client_id']

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


def save_user_if_not_exist(name):
    user = get_user(name)
    if user is None:
        user = User(name)
        session.add(user)
        session.commit()

def get_user(name):
    try:
        user = session.query(User).filter_by(name=name).one()
        return user
    except:
        return None


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'username' in login_session:
            return f(*args, **kwargs)
        else:
            return redirect(url_for('home'))
    return decorated_function


@app.route('/')
def index():
    return redirect(url_for('home'))


@app.route('/catalog')
def home():
    """Display all catalogs and all items order by adding time"""

    username = login_session.get('username', None)
    state = ''.join(
        random.choice(string.ascii_uppercase + string.digits)
        for x in xrange(32))
    login_session['state'] = state

    catalogs = session.query(Catalog).all()
    items = session.query(Item).order_by(desc(Item.date)).all()
    catalogs_display = [{'id':  catalog.id, 'name':  catalog.name}
                        for catalog in catalogs]
    items_display = [
        {
            'id':  item.id,
            'title':  item.title,
            'catalog':  item.catalog.name
        } for item in items]
    items_summary = 'Latest Items'
    return render_template(
        'home.html',
        catalogs_display=catalogs_display,
        items_display=items_display,
        items_summary=items_summary,
        state=state,
        username=username)


@app.route('/gconnect', methods=['POST'])
def gconnect():
    """Connect to google api"""

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
        response = make_response(
            json.dumps('Failed to upgrade the authorization code.'),
            401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Check that the access token is valid.
    access_token = credentials.access_token
    url = 'https://www.googleapis.com/oauth2/v1/tokeninfo?access_token=%s' % access_token
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
            json.dumps("Token's user ID doesn't match given user ID."),
            401)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Verify that the access token is valid for this app.
    if result['issued_to'] != CLIENT_ID:
        response = make_response(
            json.dumps("Token's client ID does not match app's."),
            401)
        response.headers['Content-Type'] = 'application/json'
        return response

    stored_access_token = login_session.get('access_token')
    stored_gplus_id = login_session.get('gplus_id')
    if stored_access_token is not None and gplus_id == stored_gplus_id:
        response = make_response(
            json.dumps('Current user is already connected.'),
            200)
        response.headers['Content-Type'] = 'application/json'
        return response

    # Store the access token in the session for later use.
    login_session['access_token'] = credentials.access_token
    login_session['gplus_id'] = gplus_id

    # Get user info
    userinfo_url = "https://www.googleapis.com/oauth2/v1/userinfo"
    params = {'access_token':  credentials.access_token, 'alt':  'json'}
    answer = requests.get(userinfo_url, params=params)
    data = answer.json()
    login_session['username'] = data['name']

    # Save user info into db if not exist
    save_user_if_not_exist(login_session['username'])

    return redirect(url_for('home'))


@app.route('/gdisconnect')
def gdisconnect():
    """Disconnect to google api"""

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
        del login_session['access_token']
        del login_session['gplus_id']
        del login_session['username']
        response = make_response(json.dumps('Fail to logout', 400))
        response.headers['Content-Type'] = 'application/json'
        return response


@app.route('/catalog/<id>/')
def get_catalog_items(id):
    """Get all items belonging to the selected catalog"""

    username = login_session.get('username', None)
    catalogs = session.query(Catalog).all()
    selected_catalog = session.query(Catalog).filter_by(id=id).one()
    items = selected_catalog.items
    catalogs_display = [
        {
            'id': catalog.id,
            'name': catalog.name
        } for catalog in catalogs]
    items_display = [{'id': item.id, 'title': item.title} for item in items]
    items_summary = '{0} Items ({1} items)'.format(
        selected_catalog.name,
        len(items_display))
    return render_template(
        'home.html',
        catalogs_display=catalogs_display,
        items_display=items_display,
        items_summary=items_summary,
        username=username)


@app.route('/item/create', methods=['GET', 'POST'])
@login_required
def create_item():
    """Create item"""

    username = login_session.get('username', None)

    if request.method == 'GET':
        catalogs = session.query(Catalog).all()
        catalogs_display = [
            {
                'id': catalog.id,
                'name': catalog.name
            } for catalog in catalogs]
        return render_template(
            'create_item.html',
            catalogs_display=catalogs_display,
            username=username)

    if request.method == 'POST':
        title = request.form['title']
        results = session.query(Item).filter_by(title=title).all()
        if len(results) > 0:
            return redirect(url_for('createItem'))

        user = session.query(User).filter_by(name=username).one()
        item = Item(title, request.form['desc'])
        item.catalog_id = request.form['catalog_id']
        item.user_id = user.id
        session.add(item)
        session.commit()
        return redirect(url_for('home'))


@app.route('/item/<id>')
def read_item(id):
    """Get tile and description of the selected item"""

    username = login_session.get('username', None)
    item = session.query(Item).filter_by(id=id).one()
    item_display = {'id':  item.id, 'title':  item.title, 'desc':  item.desc}
    return render_template(
        'read_item.html',
        item_display=item_display,
        username=username)


@app.route('/item/<id>/edit', methods=['GET', 'POST'])
@login_required
def edit_item(id):
    """Edit item"""

    username = login_session.get('username', None)
    catalogs = session.query(Catalog).all()
    item = session.query(Item).filter_by(id=id).one()
    # Check if current user is the creator of the item
    user = get_user(username)
    if user.id != item.user_id:
        return redirect(url_for('home'))

    catalogs_display = [
        {
            'id': catalog.id,
            'name': catalog.name
        } for catalog in catalogs]

    if request.method == 'POST':
        if request.form['title'] is not None:
            item.title = request.form['title']
        if request.form['desc'] is not None:
            item.desc = request.form['desc']
        if request.form['catalog_id'] is not None:
            item.catalog_id = request.form['catalog_id']
        session.add(item)
        session.commit()
        return redirect(url_for('read_item', id=id))

    if request.method == 'GET':
        item_display = {
            'id': item.id,
            'title': item.title,
            'desc': item.desc,
            'catalog_id': item.catalog_id}
        return render_template(
            'edit_item.html',
            item_display=item_display,
            catalogs_display=catalogs_display,
            username=username)


@app.route('/item/<id>/delete', methods=['GET', 'POST'])
@login_required
def delete_item(id):
    """Delete item"""

    username = login_session.get('username', None)
    item = session.query(Item).filter_by(id=id).one()
    # Check if current user is the creator of the item
    user = get_user(username)
    if user.id != item.user_id:
        return redirect(url_for('home'))

    if request.method == 'POST':
        session.delete(item)
        session.commit()
        return redirect(url_for('home'))

    if request.method == 'GET':
        item_display = {'id':  item.id, 'title': item.title}
        username = login_session.get('username', None)
        return render_template(
            'delete_item.html',
            item_display=item_display,
            username=username)


@app.route('/catalog/json')
def get_jsonified_catalogs():
    """Returns jsonified catalogs and items"""

    json = []
    catalogs = session.query(Catalog).all()

    for catalog in catalogs:
        catalog_json = {}
        catalog_json["id"] = catalog.id
        catalog_json["name"] = catalog.name
        catalog_json["date"] = catalog.date.strftime("%d %b %Y %H: %M: %S")
        catalog_json["items"] = []
        for item in catalog.items:
            item_json = {}
            item_json["id"] = item.id
            item_json["title"] = item.title
            item_json["desc"] = item.desc
            item_json["date"] = item.date.strftime("%d %b %Y %H: %M: %S")
            item_json["catalog_id"] = item.catalog_id
            catalog_json["items"].append(item_json)
        json.append(catalog_json)
    return jsonify(Catalogs=json)


if __name__ == '__main__':
    app.secret_key = 'super_secret_key'
    app.debug = True
    connect_db()
    app.run(host='0.0.0.0', port=8000)
    disconnect_db()
