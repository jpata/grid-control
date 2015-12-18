#-#  Copyright 2014-2015 Karlsruhe Institute of Technology
#-#
#-#  Licensed under the Apache License, Version 2.0 (the "License");
#-#  you may not use this file except in compliance with the License.
#-#  You may obtain a copy of the License at
#-#
#-#      http://www.apache.org/licenses/LICENSE-2.0
#-#
#-#  Unless required by applicable law or agreed to in writing, software
#-#  distributed under the License is distributed on an "AS IS" BASIS,
#-#  WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#-#  See the License for the specific language governing permissions and
#-#  limitations under the License.

from grid_control.datasets.modifier_base import DatasetModifier
from grid_control.datasets.provider_base import DataProvider, DatasetError
from grid_control.exceptions import AbstractError

class NickNameProducer(DatasetModifier):
	def __init__(self, config, name):
		DatasetModifier.__init__(self, config, name)
		# Ensure the same nickname is used consistently in all blocks of a dataset
		self._checkConsistency = config.getBool('nickname check consistency', True)
		self._checkConsistencyData = {}
		# Check if two different datasets have the same nickname
		self._checkCollision = config.getBool('nickname check collision', True)
		self._checkCollisionData = {}

	# Get nickname and check for collisions
	def processBlock(self, block):
		blockDS = block[DataProvider.Dataset]
		oldNick = block.get(DataProvider.Nickname, '')
		newNick = self.getName(oldNick, blockDS, block)
		# Check if nickname is used consistenly in all blocks of a datasets
		if self._checkConsistency:
			if self._checkConsistencyData.setdefault(blockDS, newNick) != newNick:
				raise DatasetError('Different blocks of dataset "%s" have different nicknames: "%s" != "%s"' % (
					blockDS, self._checkConsistencyData[blockDS], newNick))
		if self._checkCollision:
			if self._checkCollisionData.setdefault(newNick, blockDS) != blockDS:
				raise DatasetError('Multiple datasets use the same nickname "%s": "%s" != "%s"' % (
					newNick, self._checkCollisionData[newNick], blockDS))
		block[DataProvider.Nickname] = newNick
		return block

	# Overwritten by users / other implementations
	def getName(self, oldnick, dataset, block):
		raise AbstractError


class SimpleNickNameProducer(NickNameProducer):
	def getName(self, oldnick, dataset, block):
		if oldnick == '':
			return dataset.replace('/PRIVATE/', '').lstrip('/').split('#')[0].replace('/', '_').replace('__', '_')
		return oldnick


class InlineNickNameProducer(NickNameProducer):
	def __init__(self, config, name):
		NickNameProducer.__init__(self, config, name)
		self._expr = config.get('nickname expr', 'oldnick')

	def getName(self, oldnick, dataset, block):
		return eval(self._expr)
