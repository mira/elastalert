import boto3

from mira.util.secrets import AwsSecrets


class AwsMixin:

	@property
	def boto3_session(self):
		if not hasattr(self, "_boto3_session"):
			self._boto3_session = boto3.session.Session(
				aws_access_key_id=AwsSecrets.get("access_key_id"),
				aws_secret_access_key=AwsSecrets.get("secret_access_key")
			)

		return self._boto3_session
