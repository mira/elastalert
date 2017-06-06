import os.path


class Secrets:
	_cache = {}

	@classmethod
	def get(cls, name):
		pathname = os.path.join("/etc", cls.path, name)
		if pathname not in cls._cache:
			with open(pathname) as f:
				cls._cache[pathname] = f.read().strip()
		return cls._cache[pathname]


class InternalSecrets(Secrets):
	path = "internal"


class AwsSecrets(Secrets):
	path = "aws"


class SlackSecrets(Secrets):
	path = "slack"


class ElasticsearchSecrets(Secrets):
	path = "elasticsearch"
