import logging
from http.server import HTTPServer, BaseHTTPRequestHandler
from collections import defaultdict, namedtuple
import json
import datetime
import os.path
import os
from uuid import uuid4
import re
import urllib.parse as urlparse
import base64 
# Configuration

# Insert your configuration here
USER_CONFIG = {
			'logging': {
				'loglvl': 'debug'
					},
			'port': 8081,
			'data_dir': '.notes'
}

# These can be overridden in APP_CONFIG. They are just here so that you don't HAVE to define them and the module still works
BUILT_IN_DEFAULTS = { 
			'meta':{
				"version": "dev_build",
				"app" : "notes.py",
				},
			'logging': {
				"logfile" : None,
				"loglvl" : "info",
				"log_rotation": False,
				"logfmt" : '%(asctime)s %(name)s %(levelname)s: %(message)s',
				"datefmt" : '%Y/%m/%d %H:%M:%S',
				"debugging" : False,
				}
}

# Page template definitions
# APP_TMPL = ${app_tmpl}
# BUNDLE_JS = ${js_bundle} 

# To make better use of service worker caches 
# we define a list of virtual 'static' files to make available
STATIC_ASSETS = {}

# Utility Functions
def recursivelyUpdateDict(orig, new):
	updated = orig.copy()
	updateFrom = new.copy()
	for key, value in updated.items():
		if key in new:
			if not isinstance(value, dict):
				updated[key] = updateFrom.pop(key)
			else:
				updated[key] = recursivelyUpdateDict(value, updateFrom.pop(key))
	for key, value in updateFrom.items():
		updated[key] = value
	return updated
	
def createNamespace(mapping, name = 'config'):
	data = {}
	for key, value in mapping.items():
		if not isinstance(value, dict):
			data[key] = value
		else:
			data[key] = createNamespace(value, key)
	nt = namedtuple(name, list(data.keys()))
	return nt(**data)

def parseLogLevel(text, default = logging.WARNING):
	text = text.lower()
	levelValues = {
			'critical' : logging.CRITICAL,
			'error' : logging.ERROR,
			'warning' : logging.WARNING,
			'info' : logging.INFO,
			'debug' : logging.DEBUG
	}
	return levelValues.get(text, default)

def parseBool(text):
	return text.lower() in ('true', 'on', 'yes', 'y')

def create_dir(path):
	if not os.path.isdir(path):
		os.makedirs(path)

def limit_list(iterable, limit):
	'''
		returns a list of at most limit len
		from iterable
	'''
	l = []
	for x in iterable:
		l.append(x)
		limit -= 1
		if limit <= 0:
			break
	return l

# Functions handling configuration loading and logging setup
def load_config(config_dict):
	config = loadFromEnv(config_dict)

	config['logging']['loglvl'] = parseLogLevel(config['logging']['loglvl']) # Parse the loglvl
	if config['logging']['loglvl'] <= 10:
		config['logging']['debugging'] = True
	return createNamespace(config) # Return the config for good measure

def loadFromEnv(config, namespace = []):
	newConfig = config.copy()
	for key, value in config.items():
		if not isinstance(value, dict):
			configVar = '_'.join(namespace + [key.upper()])
			env = os.getenv(configVar, None)
			if env:
				newConfig[key] = parseBool(env)
		else:
			newConfig[key] = loadFromEnv(value, namespace=namespace + [key.upper()])
	return newConfig

def setup_logging():
	rootLogger = logging.getLogger()
	rootLogger.setLevel(config.logging.loglvl)

	formatter = logging.Formatter(fmt=config.logging.logfmt, datefmt=config.logging.datefmt)

	streamHandler = logging.StreamHandler()
	streamHandler.setFormatter(formatter)

	rootLogger.addHandler(streamHandler)

	if config.logging.logfile:
		if config.logging.log_rotation:
			handler = logging.handlers.RotatingFileHandler(
				config.logging.logfile, maxBytes=10*1024*1024, backupCount=2)
		else:
			handler = logging.FileHandler(config.logging.logfile)

		handler.setFormatter(formatter)
		rootLogger.addHandler(handler)

	# for handler in logging.root.handlers:
	# 	handler.addFilter(Blacklist('etcd', 'urllib3', 'smokesignal'))
	baseLogger = logging.getLogger(config.meta.app)
	baseLogger.info('Starting %s: version %s'%(config.meta.app, config.meta.version))
	return baseLogger

# A Base json backed file object
class File:
	def __init__(self, path = None):
		self._path = path
		if self._path and os.path.isfile(self._path):
			self._read()
		if not getattr(self, '_attr', False):
			self._attr = dict()
		if not self._attr.get('id', False):
			self._set_attr('id', uuid4().hex) 

	def commit(self):
		current_time = datetime.datetime.utcnow().isoformat()
		if not self._attr.get('created', False):
			self._set_attr('created', current_time)
		self._set_attr('modified', current_time)
		return self._write()

	def _write(self):
		with open(self._path, 'w') as f:
			json.dump(self._attr, f)
		return True

	def _read(self):
		with open(self._path) as f:
			self._attr = json.load(f)

	def _get_attr(self, key):
		return self._attr.get(key, None)

	def _set_attr(self, key, value):
		self._attr[key] = value

	@property
	def attr(self):
		return self._attr.copy()

	@property
	def created(self):
		return self._get_attr('created')

	@property
	def modified(self):
		return self._get_attr('modified')

	@property
	def id(self):
		return self._get_attr('id')

	@property
	def path(self):
		return getattr(self, 'path', None)

	@path.setter
	def path(self, value):
		self._path = value

# A Note
class Note(File):
	def __init__(self, path = None, **kwargs):
		self._attr = dict(title = None, body = None, tags = [])
		super().__init__(path)
		self._attr.update(kwargs)

	@property
	def id(self):
		return self._attr.get('id')
	
	@property
	def title(self):
		return self._get_attr('title')

	@title.setter
	def title(self, value):
		self._set_attr('title', value)
	
	@property
	def body(self):
		return self._get_attr('body')

	@body.setter
	def body(self, value):
		self._set_attr('body', value)

	@property
	def tags(self):
		return self._get_attr('tags')

	@tags.setter
	def tags(self, value):
		if isinstance(value, list):
			self._set_attr('tags', value)
		elif isinstance(value, str):
			current = self.tags
			current.append(value)
			self._set_attr('tags', current)

# Object to manage loading and storing notes
class NoteStore:
	def __init__(self):
		self._rootDir = config.data_dir
		self._noteDir = self._rootDir + '/notes'
		self._tagDir = self._rootDir + '/tags'
		self._clear_changes()
		self._init_directories()

	def _init_directories(self):
		create_dir(self._rootDir)
		create_dir(self._noteDir)
		create_dir(self._tagDir)

	def _clear_changes(self):
		self._changes = defaultdict(list)

	def _update_ledger(self):
		if self._changes:
			loaded = self._load_ledger()
			for id, info in self._changes['added']:
				loaded[id] = info
			for id in self._changes['removed']:
				loaded.pop(id)
			self._clear_changes()
			return self._save_ledger(loaded)
		else:
			return None
		return False

	def _load_ledger(self):
		if os.path.isfile(self._rootDir + '/ledger.json'):
			with open(self._rootDir + '/ledger.json') as f:
				return json.load(f)
		return dict()

	def _save_ledger(self, ledger):
		with open(self._rootDir + '/ledger.json', 'w') as f:
			json.dump(ledger, f, indent=1)
		return True

	def _get_note_path(self, id):
		return self._noteDir + '/{}.json'.format(id)
		
	def get(self, id):
		note = Note(self._get_note_path(id))
		if not note.created:
			return None
		return note

	def create(self, title = None, body = None, tags = []):
		note = Note(title = title, body = body, tags = tags)
		note.path = self._get_note_path(note.id)
		note.commit()
		self._changes['added'].append((note.id, dict(title=note.title, tags=note.tags)))
		self._update_ledger()
		return note

	def delete(self, id):
		note_path = self._get_note_path(id)
		if os.path.isfile(note_path):
			os.remove(path)
			self._changes['removed'].append(id)
			self._update_ledger()
	
	def update(self, id = None, title = None, body = None, tags = None):
		if not id:
			return False
		note = self.get(id)
		note.title = title if title else note.title
		note.body = body if body else note.body
		note.tags = tags if tags else note.tags
		note.commit()
		self._changes['added'].append((id, dict(title=title, tags=tags)))
		self._update_ledger()
		return note

	def search(self, title = None, tags = None, search = None):
		ledger = self._load_ledger()
		for id, note in ledger.items():
			if title and title in note['title']:
				yield self.get(id)
			elif tags:
				for tag in tags:
					if tag in note.get['tags:']:
						yield self.get(id)
						break


class Stack:
	def __init__(self, *args):
		self._notes = args
	
	def __iter__(self):
		for note in self._notes:
			yield note

# A Micro^2 http framework
class Routes:
	def __init__(self):
		self._routes = defaultdict(list)

	@staticmethod
	def build_route_pattern(route):
		route_regex = re.sub(r'(<\w+>)', r'(?P\1.+)', route)
		return re.compile("^{}$".format(route_regex))

	@staticmethod
	def _parse_query_params(path):
		parsed = urlparse.urlparse(path)
		params = urlparse.parse_qs(parsed.query)
		return {k:v[0] for k,v in params.items()}

	@staticmethod
	def _remove_query_params(path):
		return path.split('?')[0]

	def get_route_match(self, path, method):
		path = self._remove_query_params(path)
		for route in self._routes[method]:
			m = route['pattern'].match(path)
			if m:
				return m.groupdict(), route

		return None

	def route(self, uri, methods=['GET'], params = False):
		if not 'OPTIONS' in methods:
			methods.append('OPTIONS') 
		_log.debug('Registering route %s , methods: %s, params: %s'%(uri, methods, params))
		route_pattern = self.build_route_pattern(uri)
		def decorator(f):
			for method in methods:
				self._routes[method].append(dict(pattern = route_pattern,
												 func = f,
												 params = params))
			return f

		return decorator
	
	def handle(self, method, path, data = None):
		print(method, path, data)
		route_match = self.get_route_match(path, method)
		if route_match:
			kwargs, route = route_match
			view = route['func']
			if route['params']:
				kwargs['params'] = self._parse_query_params(path)
			if method in ['POST', 'PATCH', 'PUT']:
				kwargs["data"] = data

			resp = view(**kwargs)
		else:
			raise ValueError('Route "{}" has not been registered'.format(path))
		
		if isinstance(resp, int):
			return resp, None
		elif not resp:
			return 500, None
		else:
			return 200, resp

class Request(BaseHTTPRequestHandler):
	def __init__(self, *args, **kwargs):
		self._routes = defaultdict(dict)
		super().__init__(*args, **kwargs)

	def _write_resp(self, resp):
		if isinstance(resp, dict):
			resp = json.dumps(resp)
		if not isinstance(resp, bytes):
			resp = resp.encode()
		
		self.wfile.write(resp)

	def _load_req(self):
		length = int(self.headers.get('Content-Length', 0))
		if length:
			blob = self.rfile.read(length)
			return json.loads(blob.decode())
		return None

	def _handle_resp(self, code, resp):
		self.send_response(code)
		self.send_header('Access-Control-Allow-Origin', '*')
		self.end_headers()
		if resp:
			self._write_resp(resp)
		 	
	def _handle(self, method):
		code, resp = app.handle(method, self.path, self._load_req())
		self._handle_resp(code, resp)

	def do_GET(self):
		self._handle('GET')

	def do_POST(self):
		self._handle('POST')

	def do_PATCH(self):
		self._handle('PATCH')

	def do_PUT(self):
		self._handle('PUT')

	def do_OPTIONS(self):
		self.send_response(200, "ok")
		self.send_header('Access-Control-Allow-Origin', '*')                
		self.send_header('Access-Control-Allow-Methods', 'PATCH, PUT, OPTIONS')
		self.send_header("Access-Control-Allow-Headers", "Content-Type")
		self.end_headers()
		
def init(port):
	return HTTPServer(('', port), Request)

def get_embedded_file(path):
	encoded = STATIC_ASSETS.get(path, None)
	if encoded:
		return base64.b64decode(encoded).decode('utf-8')
	return None
# Load the configuration
APP_CONFIG = recursivelyUpdateDict(BUILT_IN_DEFAULTS, USER_CONFIG)
config = load_config(APP_CONFIG)
_log = setup_logging()

# Create application
app = Routes()

# Create NoteStore
store = NoteStore()

# Add Routes
# Serve app page
@app.route('/')
def server_home():
	f = get_embedded_file('/index.html')
	if f:
		return f
	raise Exception('No bundled index.html')

# Serve static files under /static/
@app.route('/static/<path>')
def get_static(path):
	f = get_embedded_file(path)
	if f:
		return f
	raise Exception('No bundled file:%s'%path)


@app.route('/favicon.ico')
def fav():
	with open("favicon.png", 'rb') as f:
		return f.read()

@app.route('/bundle.js')
def js():
	with open("bundle.js",encoding='utf-8') as f:
		return f.read()

## Add Note
@app.route('/note', methods=['PUT'])
def create_note(data):
	note = store.create(data['title'], data['body'], data['tags'])
	if note:
		return dict(success=True, results=note.attr)
	return dict(success=False, results=None)		

## Get Notes
@app.route('/note/<id>', params = True)
def get_note(id, params):
	note = store.get(id)
	if note:
		ret = dict(success=True, results=note.attr)
		print(ret)
		return ret
	return dict(success=False, results=None)

## Search notes
@app.route('/note', params = True)
def search_notes(params):
	print(params)
	limit = int(params.get('limit', 25))
	res = [n.attr for n in limit_list(store.search(
					title = params.get('title'),
					tags = params.get('tags', []),
					search = params.get('search')
				), limit)]
	return dict(success=True, results=res)
	
## Update Note
@app.route('/note', methods=['PATCH'])
def update_note(data):
	note = store.update(**data)
	if note:
		ret = dict(success=True, results=note.attr)
		print(ret)
		return ret
	return dict(success=False, results=None)

## Get Stack
@app.route('/stack/<id>', methods=['GET'])
def get_stack(id):
	return dict(success=True, results=[
		store.get('5db04689ee944e43941dd25f817a59a2').id,
		store.get('364ad8e11bac458b96aadbcaba7afe49').id,
	])

## Push to Stack
@app.route('/stack/<id>', methods=['PUT'])
def push_to_stack(id):
	return 



httpd = init(config.port)
httpd.serve_forever()