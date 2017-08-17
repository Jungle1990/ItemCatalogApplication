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

#CLIENT_ID = json.loads(open('client_secrets.json', 'r').read())['web']['client_id']

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

@app.route('/logout')
def logout():
	return

@app.route('/catalog', methods=['GET', 'POST'])
def home():
	if request.method == 'GET':
		print 'in home get'
		if 'username' in login_session:
			username = login_session['username']
		else:
			username = None
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

	if request.method == 'POST':
		print 'in home post'
		# Validate state token
		if request.args.get('state') != login_session['state']:
			response = make_response(json.dumps('Invalid state parameter.'), 401)
			response.headers['Content-Type'] = 'application/json'
			return response

		print 'get auth code'
		# Obtain authorization code
		code = request.data
		try:
		# Upgrade the authorization code into a credentials object
			oauth_flow = flow_from_clientsecrets('client_secrets.json', scope='')
			oauth_flow.redirect_uri = 'postmessage'
			credentials = oauth_flow.step2_exchange(code)
		except FlowExchangeError:
			print 'error'
			response = make_response(json.dumps('Failed to upgrade the authorization code.'), 401)
			response.headers['Content-Type'] = 'application/json'
			return response

		print 'checkout token'
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

		print 'verify token 1'
		# Verify that the access token is used for the intended user.
		gplus_id = credentials.id_token['sub']
		if result['user_id'] != gplus_id:
			response = make_response(
			json.dumps("Token's user ID doesn't match given user ID."), 401)
			response.headers['Content-Type'] = 'application/json'
			return response

		print 'verify token 2'
		# Verify that the access token is valid for this app.
		if result['issued_to'] != CLIENT_ID:
			response = make_response(
			json.dumps("Token's client ID does not match app's."), 401)
			print "Token's client ID does not match app's."
			response.headers['Content-Type'] = 'application/json'
			return response

		print 'verify token 3'
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

		print 'redirect to home get'

		return redirect(url_for('home'))

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
def get_item(id):
	connect_db()
	item = session.query(Item).filter_by(id = id).one()
	item_display = {'id' : item.id, 'title' : item.title, 'desc' : item.desc}
	disconnect_db()
	return render_template('item_detail.html', item_display = item_display)

@app.route('/item/create', methods=['GET', 'POST'])
def createItem():
	if request.method == 'GET':
		connect_db()
		catalogs = session.query(Catalog).all()
		catalogs_display = [{'id' : catalog.id, 'name' : catalog.name} for catalog in catalogs]
		disconnect_db()
		return render_template('edit_item.html', catalogs_display = catalogs_display)

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

if __name__ == '__main__':
	app.secret_key = 'super_secret_key'
	app.debug = True
	app.run(host='0.0.0.0', port=8000)
