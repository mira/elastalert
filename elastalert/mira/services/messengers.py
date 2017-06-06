import base64

from mira.services.aws import AwsMixin
import mira.protocols.http as http
import mira.util.crypto as crypto
from mira.util.log import get_logger

log = get_logger(__name__)


class BaseMessageService():

	def publish(self, topic, subject, message):
		raise NotImplementedError()


class SnsMessagingService(BaseMessageService, AwsMixin):
	subscription_xml_ns = "{http://sns.amazonaws.com/doc/2010-03-31/}"

	def __init__(self):
		self.sns = self.boto3_session.client('sns', region_name="us-east-1")

	def publish(self, topic, subject, message):
		self.sns.publish(TopicArn=topic, Message=message, Subject=subject)

	@classmethod
	def subscription_is_verified(
		cls,
		message=None,
		message_id=None,
		timestamp=None,
		token=None,
		topic_arn=None,
		signature=None,
		subscribe_url=None,
		signing_cert_url=None
	):
		canonical_string = cls._get_canonical_string(
			('Message', message),
			('MessageId', message_id),
			('SubscribeURL', subscribe_url),
			('Timestamp', timestamp),
			('Token', token),
			('TopicArn', topic_arn),
			('Type', "SubscriptionConfirmation")
		)

		return cls.message_is_verified(
			canonical_string, signature, signing_cert_url
		)

	@classmethod
	def notification_is_verified(
		cls,
		message=None,
		message_id=None,
		timestamp=None,
		subject=None,
		topic_arn=None,
		signature=None,
		signing_cert_url=None
	):
		canonical_string = cls._get_canonical_string(
			('Message', message),
			('MessageId', message_id),
			('Subject', subject),
			('Timestamp', timestamp),
			('TopicArn', topic_arn),
			('Type', "Notification")
		)

		return True
		return cls.message_is_verified(
			canonical_string, signature, signing_cert_url
		)

	@classmethod
	def message_is_verified(cls, canonical_string, signature, signing_cert_url):
		cert_text = http.get_response(signing_cert_url).decode_text()
		public_key = crypto.get_public_key(cert_text)

		return crypto.signature_is_verified(
			base64.b64decode(signature),
			public_key.encode('utf-8'),
			canonical_string.encode('utf-8')
		)

	@classmethod
	def confirm_subscription(cls, uri):
		root = http.get_response(uri).decode_xml()

		subscription_arn = root.find(
			"{ns}ConfirmSubscriptionResult".format(ns=cls.subscription_xml_ns)
		).find(
			"{ns}SubscriptionArn".format(ns=cls.subscription_xml_ns)
		).text

		request_id = root.find(
			"{ns}ResponseMetadata".format(ns=cls.subscription_xml_ns)
		).find(
			"{ns}RequestId".format(ns=cls.subscription_xml_ns)
		).text

		return {
			"subscription_arn": subscription_arn,
			"request_id": request_id
		}

	@classmethod
	def _get_canonical_string(cls, *vargs):
		signature_string = ""
		for key, value in vargs:
			signature_string += "{key}\n{value}\n".format(key=key, value=value)

		return signature_string
