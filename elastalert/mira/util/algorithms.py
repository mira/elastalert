

class DoubleListNode(object):
	def __init__(self, value, prev, next):
		self.value = value
		self.prev = prev
		self.next = next


class DoubleList(object):

	def __init__(self):
		self.head = None
		self.tail = None
		self.length = 0

	def append(self, value):
		node = DoubleListNode(value, None, None)
		if self.head is None:
			self.head = self.tail = node
		else:
			node.prev = self.tail
			node.next = None
			self.tail.next = node
			self.tail = node

		self.length += 1
		return node

	def unshift(self, value):
		node = DoubleListNode(value, None, None)
		if self.head is None:
			self.head = self.tail = node
		else:
			node.prev = None
			node.next = self.head
			self.head.prev = node
			self.head = node

		self.length += 1
		return node

	def remove(self, node):
		if node.prev is None:
			self.head = node.next
			if node.next:
				node.next.prev = None
		else:
			if node.next:
				node.next.prev = node.prev

		if node.next is None:
			self.tail = node.prev
			if node.prev:
				node.prev.next = None
		else:
			if node.prev:
				node.prev.next = node.next

		self.length -= 1
		return node

	def pop(self):
		return self.remove(self.tail)

	def shift(self):
		return self.remove(self.head)

	def __len__(self):
		return self.length
