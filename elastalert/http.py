import enum
import json
import xml.etree.ElementTree

import requests


def parse_uri(uri):
	protocol, url = uri.split("://")
	url_parts = url.split("/")
	host = url_parts[0]
	path = "/".join(url_parts[1:]).split("?")

	if len(path) == 2:
		args = path[1]
		args = {arg.split("=")[0]: arg.split("=")[1] for arg in args.split("&")}
	else:
		args = {}

	path = path[0]

	return protocol, host, path, args


def get_response(uri):
	protocol, host, path, args = parse_uri(uri)

	if protocol == "https":
		return HttpsConnection(host).get(path, params=args).response
	elif protocol == "http":
		return HttpConnection(host).get(path, params=args).response
	else:
		raise HttpConnectionError("Bad Protocol")


class HttpConnectionError(Exception):
	def __init__(self, response, uri=None, status_code=400):
		super(HttpConnectionError, self).__init__(
			"{status}: Could not connect to '{uri}'".format(
				status=status_code, uri=uri
			)
		)
		self.uri = uri
		self.status_code = status_code
		self.response = response

	def to_json(self):
		return json.dumps({
			"uri": self.uri,
			"status_code": self.status_code,
			"response": self.response
		})


class UnknownProtocolError(Exception):
	def __init__(self, protocol):
		self.protocol = protocol
		super(UnknownProtocolError, self).__init__(
			"Unknown protocol '{protocol}'".format(protocol=self.protocol)
		)


class HttpConnection():
	protocol = "http"
	default_port = 80

	def __init__(self, url, port=None):
		self.request = None
		self.url = url
		self.port = port or self.default_port
		self.uri = None

	def _clean_param(self, param):
		if type(param) is list or type(param) is set:
			return ",".join([str(item) for item in param])
		else:
			return param

	def get(self, path, params=None, headers=None):
		params = params or {}
		params = {k: self._clean_param(v) for k, v in params.items()}
		self.set_uri(path)

		self.request = requests.get(self.uri, params=params, headers=headers)
		return self

	def upload(self, path, data=None):
		headers = {}
		headers['Content-Type'] = "application/octet-stream"
		self.set_uri(path)

		self.request = requests.post(self.uri, data=data, headers=headers)
		return self

	def post(self, path, data=None, headers=None):
		headers = headers or {}
		headers['Content-Type'] = "application/x-www-form-urlencoded" if \
			"Content-Type" not in headers else headers['Content-Type']
		self.set_uri(path)

		self.request = requests.post(self.uri, data=data, headers=headers)
		return self

	def delete(self, path, data=None, headers=None):
		headers = headers or {}
		self.set_uri(path)

		self.request = requests.delete(self.uri, data=data, headers=headers)
		return self

	def put(self, path, json=None, data=None, headers=None):
		headers = headers or {}
		self.set_uri(path)

		self.request = requests.put(
			self.uri, data=data, json=json, headers=headers
		)
		return self

	def set_uri(self, path):
		self.uri = "{protocol}://{url}:{port}/{path}".format(
			protocol=self.protocol, url=self.url, path=path, port=self.port
		)

	@property
	def response(self):
		return HttpResponse(self.request, self.uri)


class HttpsConnection(HttpConnection):
	protocol = "https"
	default_port = 443


class HttpResponse():

	def __init__(self, response, uri):
		self.response = response
		self.status = response.status_code
		self.uri = uri

		if self.status != 200:
			raise HttpConnectionError(
				self.decode_text(), uri=self.uri, status_code=self.status
			)

	def decode_text(self):
		return self.response.text

	def decode_json(self):
		return self.response.json()

	def decode_xml(self):
		return xml.etree.ElementTree.fromstring(self.response.text)


class HttpProtocol(enum.Enum):
	HTTP = "http"
	HTTPS = "https"


class MimeTypes(enum.Enum):
	YAML = "application/x-yaml"
	JSON = "application/json"
	HTML = "text/html"
	TEXT = "text/plain"
	FORM_DATA = "multipart/form-data"
	XML = "application/xml"

	@classmethod
	def is_xml(cls, mime_type):
		return mime_type in [cls.XML.value, "text/xml"]

	@classmethod
	def is_yaml(cls, mime_type):
		return mime_type in [cls.YAML.value, "text/yaml"]

	@classmethod
	def is_json(cls, mime_type):
		return mime_type == cls.JSON.value

	@classmethod
	def is_form_data(cls, mime_type):
		return mime_type == cls.FORM_DATA.value
