

class FunctionHelper:

	@classmethod
	def flat_map(cls, lists):
		return [_item for _list in lists for _item in _list]
