import os

from mira.apis.api import Api


class NeustarApi(Api):

	def __init__(self, subdomain, client_id, version="v2"):
		self.client_id = client_id
		self.version = version
		super(NeustarApi, self).__init__(
			"{subdomain}.adadvisor.net".format(subdomain=subdomain)
		)

	def get_segment(
		self, device_id, latitude=None, longitude=None, device_os=None,
		ip_address=None
	):
		args = {"deviceid": device_id}

		if latitude is not None:
			args["lat"] = latitude

		if longitude is not None:
			args["lon"] = longitude

		if device_os is not None:
			args["os"] = device_os

		if ip_address is not None:
			args["ip"] = ip_address

		return self.get(
			os.path.join(self.version, "seglookup", str(self.client_id)),
			args
		)

	def get_e1_segment(
		self, device_id, latitude=None, longitude=None, device_os=None,
		ip_address=None
	):
		result = self.get_segment(
			device_id, latitude=latitude, longitude=longitude,
			device_os=device_os, ip_address=ip_address
		)

		if result and len(result) > 0:
			return result["e1"][0]
		else:
			return result
