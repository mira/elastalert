import os
import urllib

from mira.protocols.http import HttpConnection, HttpConnectionError
from mira.util.version import get_version


class Api:

	def __init__(self, host, port=80, key=None):
		self.key = key
		self.port = port
		self.host = host
		self.headers = {"Accept": "application/json"}
		self.connection = HttpConnection(self.host, port=self.port)

	def post(self, path, args=None):
		args = args or {}
		args["api_key"] = self.key
		return self.connection.post(
			path, data=args, headers=self.headers
		).response.decode_json()

	def upload(self, path, data):
		return self.connection.upload(
			path, data=data
		).response.decode_json()

	def get(self, path, args=None):
		args = args or {}
		args["api_key"] = self.key
		return self.connection.get(
			path, params=args, headers=self.headers
		).response.decode_json()

	def is_healthy(self):
		try:
			response = self.get("health")

			if self.host in response:
				return response
			else:
				return {
					"is_healthy": False,
					"message": "Response did not contain data"
				}
		except HttpConnectionError as e:
			return {
				"is_healthy": False,
				"message": e.response
			}


class DecisionsApi(Api):

	def decide(
		self, campaign_id, device_id=None, device_state_id=1, cache=True
	):
		params = {"api_key": self.key, "cache": cache}

		if device_id is not None:
			params["device_id"] = device_id

		if device_state_id is not None:
			params["device_state_id"] = device_state_id

		return self.get(
			os.path.join("campaigns", str(campaign_id), "decide"),
			params
		)


class ConfigRegistryApi(Api):

	def __init__(self, host, app, port=80, key=None):
		super(ConfigRegistryApi, self).__init__(host, port=port, key=key)
		self.version = get_version()
		self.app = app
		self.cache = {}

	def get_config(self, subject, version, cache=True):
		config = {}
		if cache and (subject, version) in self.cache:
			config = self.cache[(subject, version)]
		else:
			config = self.get(
				"apps/{app}/subjects/{subject}/configs/{version}".format(
					app=self.app, subject=subject, version=version
				)
			)

			if cache:
				self.cache[(subject, version)] = config

		return config


class FlightsApi(Api):

	def __init__(self, host, port=80, key=None):
		super(FlightsApi, self).__init__(host, port=port, key=key)
		self.version = get_version()

	def upload_decision_tree(
		self, decision_tree, version, name, description, bucket
	):
		params = urllib.parse.urlencode({
			"name": name,
			"version": self.version,
			"description": description,
			"bucket": bucket,
			"api_key": self.key
		})

		return self.upload(
			"decision_tree?{params}".format(params=params),
			decision_tree.pickle()
		)

	def get_decision_tree(self, decision_tree_id):
		return self.get(
			"decision_tree",
			{"id": decision_tree_id, "api_key": self.key}
		)

	def get_decision_tree_by_campaign(self, campaign_id):
		return self.get(
			os.path.join(
				"campaigns", str(campaign_id), "decision_trees",
				"versions", self.version
			),
			{"api_key": self.key}
		)

	def create_creative(
		self, campaign_id, line_item_id, label, uri
	):
		return self.post(
			os.path.join(
				"campaigns", str(campaign_id), "line_items", str(line_item_id),
				"creative"
			),
			{
				"uri": uri,
				"label": label
			}
		)['creative_id']

	def create_line_item(self, campaign_id, name, description=None):
		return self.post(
			os.path.join("campaigns", str(campaign_id), "line_item"),
			{
				'name': name,
				'description': description
			}
		)['line_item_id']

	def get_creatives(self, campaign_id, uuid=None):
		params = {
			'api_key': self.key
		}

		if uuid:
			params["uuid"] = uuid

		return self.get(
			os.path.join("campaigns", str(campaign_id), "creatives"),
			params
		)

	def get_groups(
		self, campaign_id, device_id=None, device_state_id=None, uuid=None
	):
		params = {
			'api_key': self.key
		}

		if uuid:
			params["uuid"] = uuid

		if device_id:
			params["device_id"] = device_id

		if device_state_id:
			params["device_state_id"] = device_state_id

		return self.get(
			os.path.join("campaigns", str(campaign_id), "groups"),
			params
		)

	def get_events(self, group_ids=None, start_date=None, end_date=None):
		params = {}

		if group_ids:
			params["group_ids"] = group_ids

		if start_date:
			params["start_date"] = start_date

		if end_date:
			params["end_date"] = end_date

		return self.get("events", params)

	def get_impressions(
		self, campaign_id=None, group_ids=None, start_date_time=None
	):
		params = {}

		if group_ids:
			params["group_ids"] = group_ids

		if start_date_time:
			params["start_date_time"] = start_date_time

		return self.get(
			os.path.join("campaigns", str(campaign_id), "impressions"),
			params
		)

	def get_day_parts(self, campaign_id):
		return self.get(
			os.path.join("campaigns", str(campaign_id), "day_parts")
		)

	def get_device_dimensions(self, device_id):
		results = self.get(
			os.path.join("devices", str(device_id), "dimensions")
		)
		return results["width"], results["height"]

	def get_devices(self, campaign_id, device_state_id=None):
		params = {}

		if device_state_id is not None:
			params['device_state_id'] = device_state_id

		return self.get(
			os.path.join("campaigns", str(campaign_id), "devices"),
			params
		)
