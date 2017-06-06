import os


class Environment:

	@classmethod
	def get_list(cls, name, default=None, var_type=str, delimiter=","):
		return [var_type(i) for i in os.getenv(name, default).split(delimiter)]

	@classmethod
	def get_int(cls, name, default=0):
		try:
			return int(os.getenv(name, default))
		except:
			return int(default)

	@classmethod
	def get_str(cls, name, default=""):
		try:
			return str(os.getenv(name, default))
		except:
			return str(default)

	@classmethod
	def get_float(cls, name, default=0.0):
		try:
			return float(os.getenv(name, default))
		except:
			return float(default)
