class ComputerParameters():
	"""
	Parameters describing the computer system.
	"""
	def __init__(
		self,
		name: str,
		os: str,
		data_path: str
	):
		"""
		:param name: Computer name.
		:param os: Operating system.
		:param data_path: Path to default data folder.
		"""
		self.name = name
		self.os = os
		self.data_path = data_path