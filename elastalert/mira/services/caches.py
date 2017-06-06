import redis
from redis.sentinel import Sentinel

from mira.services.aws import AwsMixin
from mira.util.algorithms import DoubleList
from mira.util.networking import resolve_dns


class InvalidRedisConfiguration(Exception):

	def __init__(self, msg):
		super(InvalidRedisConfiguration, self).__init__(msg)
		self.msg = msg


class BaseCacheService():

	def set(self, key, value):
		raise NotImplementedError()

	def get(self, key):
		raise NotImplementedError()

	def ping(self):
		raise NotImplementedError()

	def exists(self):
		raise NotImplementedError()

	def __contains__(self, key):
		return self.exists(key)

	def __getitem__(self, key):
		return self.get(key)

	def __setitem__(self, key, value):
		return self.set(key, value)


class InMemoryLruCache(BaseCacheService):

	def __init__(self, max_entries=1):
		self._queue = DoubleList()
		self._hash = {}
		self.max_entries = max_entries

	def set(self, key, value):
		node = self._queue.unshift((key, value))
		self._hash[key] = node

		if len(self._queue) > self.max_entries:
			last_key, _ = self._queue.pop().value
			del self._hash[last_key]

	def get(self, key):
		node = self._hash[key]
		_, value = node.value
		self._queue.remove(node)
		node = self._queue.unshift((key, value))
		self._hash[key] = node
		return value

	def ping(self):
		return True

	def exists(self, key):
		return key in self._hash


def generate_redis_sentinel_names(
	stateful_set_name, service_name, namespace, port, replicas
):
	sentinels = []
	for i in range(0, replicas):
		host = "{stateful_set}-{replica}.{service}.{namespace}".format(
			stateful_set=stateful_set_name,
			replica=i,
			service=service_name,
			namespace=namespace
		)

		sentinels.append((resolve_dns(host), port))

	return sentinels


class RedisCacheService(BaseCacheService):

	def __init__(
		self, host=None, port=6379, name=None, sentinels=None, db=0,
		socket_timeout=0.1
	):
		self.name = name
		self.db = db
		self.host = host
		self.port = port
		self.socket_timeout = socket_timeout

		self.master_host = None
		self.master_port = None

		self.sentinel = Sentinel(
			sentinels, socket_timeout=self.socket_timeout
		) if sentinels else None

		if not self.host and not (self.sentinel and self.name):
			raise InvalidRedisConfiguration()

	@property
	def redis(self):
		if self.host:
			if not hasattr(self, "_redis"):
				self._redis = redis.StrictRedis(
					host=self.host, port=self.port, db=self.db
				)
		elif self.sentinel and self.name:
			host, port = self.sentinel.discover_master(self.name)

			if(
				host != self.master_host or port != self.master_port
			) or (
				not hasattr(self, "_redis")
			):
				self._redis = self.sentinel.master_for(self.name, db=self.db)
		else:
			raise InvalidRedisConfiguration()

		return self._redis

	def set(self, key, value):
		self.redis.set(key, value)

	def expire(self, key, delta):
		self.redis.expire(key, delta)

	def get(self, key, encoding='utf-8'):
		value = self.redis.get(key)
		if encoding:
			return value.decode('utf-8') if value else None
		else:
			return value

	def ping(self):
		return self.redis.ping()

	def delete(self, key):
		return self.redis.delete(key)

	def ttl(self, key):
		return self.redis.ttl(key)

	def scan_all(self, match=None, encoding='utf-8'):
		for key in self.redis.scan_iter(match=match):
			yield key.decode(encoding) if encoding else key

	def get_all(self, match=None, encoding='utf-8'):
		for key in self.scan_all(match=match, encoding=encoding):
			value = self.get(key, encoding=encoding)
			if value:
				yield key, value

	def delete_all(self, match=None, encoding='utf-8'):
		for key in self.scan_all(match=match, encoding=encoding):
			self.delete(key)

	def exists(self, key):
		return self.redis.exists(key)


class DynamoDbCacheService(BaseCacheService, AwsMixin):

	def __init__(self, table, region='us-east-1'):
		self.table = table
		self.region = region

	@property
	def client(self):
		if not hasattr(self, "_client"):
			self._client = self.boto3_session.client(
				'dynamodb', region_name=self.region
			)

		return self._client

	def ping(self):
		if self.client.list_tables(Limit=1):
			return True
		else:
			return False

	def set(self, key, value, kind='S'):
		self.client.put_item(
			TableName=self.table,
			Item={key: {kind: value}}
		)

	def get(self, key):
		if type(key) is not dict:
			raise Exception("DynamoDB requires a dictionary for selection.")

		resp = self.client.get_item(TableName=self.table, Key=key)

		return {
			k: self._parse_value(v) for k, v in resp['Item'].items()
		} if "Item" in resp else None

	def exists(self, key):
		return self.get(key) is not None

	def _parse_value(self, value):
		if "S" in value:
			return str(value["S"])
		elif "N" in value:
			return float(value["N"])
		elif "B" in value:
			return value["B"]
		elif "SS" in value:
			return value["SS"]
		elif "NS" in value:
			return value["NS"]
		elif "BS" in value:
			return value["BS"]
		elif "M" in value:
			return value["M"]
		elif "L" in value:
			return value["L"]
		elif "NULL" in value:
			return None
		elif "BOOL" in value:
			return bool(value["M"])
		else:
			raise Exception("Unknown DynamoDB Types {}".format(value))
