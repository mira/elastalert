import datetime
import rsa
from urllib.parse import urlparse

from botocore.signers import CloudFrontSigner

from mira.util.secrets import AwsSecrets


class BaseCdnService():

	def convert_uri(self, uri):
		raise NotImplementedError()


class CloudfrontCdnService(BaseCdnService):

	def __init__(self):
		self._signer = None

	@property
	def signer(self):
		if not self._signer:
			private_key = rsa.PrivateKey.load_pkcs1(
				AwsSecrets.get("cloudfront_private_key")
			)

			self._signer = CloudFrontSigner(
				AwsSecrets.get("cloudfront_key_id"),
				lambda x: rsa.sign(x, private_key, 'SHA-1')
			)

		return self._signer

	def convert_uri(self, uri, scheme='https'):
		url = "{scheme}://{dist_id}.cloudfront.net{path}".format(
			scheme=scheme,
			dist_id=AwsSecrets.get("cloudfront_distribution_id"),
			path=urlparse(uri).path
		)

		timestamp = (datetime.datetime.utcnow() + datetime.timedelta(1))

		return self.signer.generate_presigned_url(
			url, timestamp.replace(
				timestamp.year,
				timestamp.month,
				timestamp.day, 0, 0, 0, 0
			)
		)
