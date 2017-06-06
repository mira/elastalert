import datetime
import functools
import json
import re
import sys
import traceback
import yaml

from flask import Response

from mira.util.log import get_logger
from mira.protocols.http import MimeTypes, HttpConnectionError

log = get_logger(__name__)


class BadRequestException(Exception):
	def __init__(self, message, status_code=400):
		super(BadRequestException, self).__init__(message)
		self.message = message
		self.status_code = status_code


class ServerHelper:

	def __init__(self, error_handler=None):
		self.error_handler = error_handler

	def parse_raw_value(self, value, _type=None):

		if value is None:
			return None

		def get_value(value):
			value = str(value)

			if re.match(r'^\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}$', value):
				return datetime.datetime.strptime(value, "%Y-%m-%d %H:%M:%S")
			elif re.match(r'^\d{4}-\d{2}-\d{2}$', value):
				return datetime.datetime.strptime(value, "%Y-%m-%d").date()
			elif re.match(r'^\d{2}:\d{2}:\d{2}$', value):
				return datetime.datetime.strptime(value, "%H:%M:%S").time()
			elif re.match(r'^\-?\d+$', value):
				return int(value)
			elif re.match(r'^\-?\d*\.\d+$', value):
				return float(value)
			elif re.search(r',', value):
				return [get_value(val) for val in value.split(",")]
			else:
				return value

		value = get_value(value)
		if _type == list:
			return [value] if type(value) is not list else value
		else:
			return value

	def handle_general_error(self, error, params):
		if self.error_handler:
			self.error_handler.handle_error(error, params)


class FlaskHelper(ServerHelper):

	def __init__(self, request, cache=None, error_handler=None):
		super(FlaskHelper, self).__init__(error_handler=error_handler)
		self.request = request
		self.cache = cache

	@property
	def content_type(self):
		return self.request.headers.get("Content-Type", None)

	@property
	def accept(self):
		return self.request.headers.get("Accept", None)

	def is_yaml(self):
		return MimeTypes.is_yaml(self.content_type)

	def is_json(self):
		return MimeTypes.is_json(self.content_type)

	def is_form_data(self):
		return MimeTypes.is_form_data(self.content_type)

	def accepts_yaml(self):
		return MimeTypes.is_yaml(self.accept)

	def accepts_json(self):
		return MimeTypes.is_json(self.accept)

	@property
	def data(self):
		if self.is_yaml():
			return yaml.load(self.request.data)
		elif self.is_form_data():
			return self.request.form.items()
		else:
			return self.request.get_json()

	@property
	def args(self):
		args = self.request.get_json() or {}

		for key, value in self.request.args.items():
			args[key] = value

		for key, value in self.request.form.items():
			args[key] = value

		return args

	def authenticate_request(self, function):
		@functools.wraps(function)
		def wrapper(*vargs, **kwargs):
			api_key = self.args.get("api_key", None)

			cache_key = {'apiKey': {'S': api_key}}

			if not api_key or not self.cache.get(cache_key):
				raise BadRequestException(
					"Invalid API Key!", status_code=403
				)

			return function(*vargs, **kwargs)

		return wrapper

	def parse_args(self, args, opts=None, types=None):
		types = types or {}

		def decorator(function):
			@functools.wraps(function)
			def wrapper(*vargs, **kwargs):
				vargs = list(vargs)

				for key in args:
					if key in self.args:
						_type = types[key] if key in types else None
						vargs.append(
							self.parse_raw_value(
								self.args[key], _type=_type
							)
						)
					else:
						raise BadRequestException(
							"A {key} must be specified!".format(key=key)
						)

				for key in opts or []:
					_type = types[key] if key in types else None
					value = self.parse_raw_value(
						self.args[key], _type=_type
					) if key in self.args else None

					if value is not None:
						kwargs[key] = value

				return function(*vargs, **kwargs)

			return wrapper

		return decorator

	def respond(self, values):
		def parse_values(value):
			if type(value) is datetime.datetime:
				return value.strftime("%Y-%m-%d %H:%M:%S")
			elif type(value) is datetime.date:
				return value.strftime("%Y-%m-%d")
			elif type(value) is datetime.time:
				return value.strftime("%H:%M:%S")
			elif type(value) is list:
				return parse_list(value)
			elif type(value) is dict:
				return parse_dict(value)
			else:
				return value

		def parse_list(values):
			return [parse_values(value) for value in values]

		def parse_dict(values):
			return {key: parse_values(value) for key, value in values.items()}

		parsed_values = parse_values(values)
		response = None

		if self.accepts_yaml():
			response = Response(yaml.dumps(parsed_values))
			response.headers['Content-Type'] = MimeTypes.YAML.value
		else:
			response = Response(json.dumps(parsed_values))
			response.headers['Content-Type'] = MimeTypes.JSON.value

		return response

	def respond_on_fail(self, function):
		@functools.wraps(function)
		def wrapper(*vargs, **kwargs):
			log = get_logger(__name__)
			try:
				return function(*vargs, **kwargs)
			except BadRequestException as e:
				_, _, tb = sys.exc_info()

				msg = "{type}: {msg}\n\t{tb}".format(
					type=type(e),
					msg=e.message,
					tb="\t".join(traceback.format_list(
						traceback.extract_tb(tb))
					)
				)

				log.error(msg)

				return Response(status=e.status_code, response=msg)
			except HttpConnectionError as e:
				_, _, tb = sys.exc_info()

				msg = "Connection Error {status} ({uri}): {resp}\n\t{tb}".format(
					status=e.status_code,
					uri=e.uri,
					resp=e.response,
					tb="\t".join(traceback.format_list(traceback.extract_tb(tb)))
				)

				log.error(msg)

				return Response(status=e.status_code, response=msg)
			except Exception as e:
				_, _, tb = sys.exc_info()

				msg = "{type}: {msg}\n\t{tb}".format(
					type=type(e),
					msg=e,
					tb="\t".join(traceback.format_list(
						traceback.extract_tb(tb))
					)
				)

				log.error(msg)

				return Response(status=500, response=msg)

		return wrapper
