from mira.services.messengers import SnsMessagingService
import json


class ErrorHandler:

	def handle_error(self, error, params):
		raise NotImplementedError()


class AwsSnsErrorHandler(ErrorHandler):

	def __init__(self, topic, subject):
		self.messenger = SnsMessagingService()
		self.topic = topic
		self.subject = subject

	def handle_error(self, error, params):
		msg = (
			"Errored while trying to process request\n"
			"{error}\n"
			"{params}"
		).format(error=error, params=json.dumps(params, indent=2))

		self.messenger.publish(
			topic=self.topic,
			subject=self.subject,
			message=msg
		)
