import tempfile

import botocore.exceptions

from mira.services.aws import AwsMixin


class BaseStorageService():
	def __init__(self):
		raise NotImplementedError()

	def upload_data(self, bucket, key, data):
		raise NotImplementedError()

	def download_data(self, bucket, key, filename=None):
		raise NotImplementedError()

	def fetch_data(self, bucket, key):
		raise NotImplementedError()

	def create_bucket(self, bucket):
		raise NotImplementedError()

	def bucket_exists(self, bucket):
		raise NotImplementedError()


class S3StorageService(BaseStorageService, AwsMixin):

	def __init__(self):
		self.s3 = self.boto3_session.resource('s3')
		self.client = self.boto3_session.client('s3')

	def upload_data(self, bucket, key, data):
		self.s3.Bucket(bucket).put_object(Key=key, Body=data)
		return "s3://{bucket}/{key}".format(bucket=bucket, key=key)

	def fetch_data(self, bucket, key):
		response = self.s3.Bucket(bucket).Object(key=key).get()
		return response['Body'].read()

	def download_data(self, bucket, key, filename=None):
		if not filename:
			download_file = tempfile.NamedTemporaryFile(delete=False)
			filename = download_file.name
			download_file.close()

		self.s3.Bucket(bucket).Object(key=key).download_file(filename)

		return filename

	def create_bucket(self, bucket):
		self.client.create_bucket(Bucket=bucket)

	def bucket_exists(self, bucket):
		try:
			self.client.head_bucket(Bucket=bucket)
			return True
		except botocore.exceptions.ClientError:
			return False
