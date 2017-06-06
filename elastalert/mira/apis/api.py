from mira.protocols.http import MimeTypes, HttpProtocol, \
	UnknownProtocolError, HttpConnection, HttpsConnection


class Api:

	def __init__(
		self, host, port=None, key=None,
		accept=MimeTypes.JSON, protocol=HttpProtocol.HTTP
	):
		self.key = key
		self.port = port
		self.host = host
		self.accept = accept

		if protocol == HttpProtocol.HTTP:
			self.connection = HttpConnection(self.host, port=self.port)
		elif protocol == HttpProtocol.HTTPS:
			self.connection = HttpsConnection(self.host, port=self.port)
		else:
			raise UnknownProtocolError()

	@property
	def headers(self):
		return {"Accept": self.accept.value}

	def post(self, path, args=None):
		result = self.connection.post(
			path, data=args, headers=self.headers
		).response

		return self.respond(result)

	def delete(self, path, args=None):
		result = self.connection.delete(
			path, data=args, headers=self.headers
		).response

		return self.respond(result)

	def put(self, path, args=None):
		result = self.connection.put(
			path, data=args, headers=self.headers
		).response

		return self.respond(result)

	def upload(self, path, data):
		result = self.connection.upload(
			path, data=data
		).response

		return self.respond(result)

	def get(self, path, args=None):
		result = self.connection.get(
			path, params=args, headers=self.headers
		).response

		return self.respond(result)

	def respond(self, result):
		if self.accept == MimeTypes.JSON:
			return result.decode_json()
		elif self.accept == MimeTypes.XML:
			return result.decode_xml()
		else:
			return result.decode_text()
