

class ReflectionHelper:

	@classmethod
	def get_class(cls, class_name, module=None):
		module = __import__(module, globals(), locals(), fromlist=[class_name])
		return getattr(module, class_name)

	@classmethod
	def get_method(cls, method_name, module=None):
		module = __import__(module, globals(), locals(), fromlist=[method_name])
		return getattr(module, method_name)
