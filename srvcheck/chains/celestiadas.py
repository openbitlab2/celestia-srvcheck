import time
import configparser
import re
from .chain import Chain
from ..utils import Bash
from ..notification import Emoji
from ..tasks import Task,  hours, minutes
from ..tasks.taskchainstuck import elapsedToString

class TaskCelestiaDasCheckSamplesHeight(Task):
	def __init__(self, services, checkEvery = minutes(5), notifyEvery=minutes(5)):
		super().__init__('TaskCelestiaDasCheckSamplesHeight', services, checkEvery, notifyEvery)	
		self.since = None
		self.oc = 0

	@staticmethod
	def isPluggable(services):
		return services.chain.ROLE == 'light' or services.chain.ROLE == 'full'

	def run(self):
		if not self.s.chain.isSynching():
			bh = int(self.s.chain.getNetworkHeight())
			bhSampled = self.s.chain.getSamplesHeight()

			if self.since is None:
				self.since = time.time()
				return False

			if bh > bhSampled:
				self.oc += 1
				elapsed = elapsedToString(self.since)
				return self.notify(f'is not sampling new headers, last block sampled is {bhSampled}, current block header is {bh} ({elapsed}) {Emoji.Stuck}')

			if self.oc > 0:
				elapsed = elapsedToString(self.since)
				self.notify (f'is back sampling new headers (after {elapsed}) {Emoji.SyncOk}')

			self.since = time.time()
			self.oc = 0
		return False
	
class TaskNodeIsSynching(Task):
	def __init__(self, services):
		super().__init__('TaskNodeIsSynching', services, minutes(5), minutes(5))
		self.prev = None
		self.since = None
		self.oc = 0

	@staticmethod
	def isPluggable(services):
		return True

	def run(self):
		bh = int(self.s.chain.getHeight())

		if self.prev is None:
			self.prev = bh
			self.since = time.time()
			return False

		nh = int(self.s.chain.getNetworkHeight())
		if bh > self.prev and abs(bh - nh) > 100:
			self.oc += 1
			return self.notify(f'chain is synching, last block stored is {bh}, current network height is {nh} {Emoji.Slow}')

		if self.oc > 0:
			elapsed = elapsedToString(self.since)
			self.notify (f'chain synched in {elapsed} {Emoji.SyncOk}')

		self.prev = bh
		self.since = time.time()
		self.oc = 0
		return False

class CelestiaDas(Chain):
	TYPE = ""
	ROLE = "light"
	NAME = ""
	BLOCKTIME = 60
	AUTH_TOKEN = None
	BIN = None
	EP = "http://localhost:26658/"
	CUSTOM_TASKS = [TaskCelestiaDasCheckSamplesHeight, TaskNodeIsSynching]

	def __init__(self, conf):
		super().__init__(conf)
		serv = self.conf.getOrDefault('chain.service')
		if serv:
			c = configparser.ConfigParser()
			c.read(f"/etc/systemd/system/{serv}")
			cmd = re.split(' ', c["Service"]["ExecStart"])
			self.BIN = cmd[0]
			self.ROLE = cmd[1]
			self.TYPE = self.ROLE.capitalize() + " node"

	@staticmethod
	def detect(conf):
		try:
			CelestiaDas(conf).getNetwork()
			return True
		except:
			return False

	def rpcCall(self, method, headers=None, params=[]):
		if not self.AUTH_TOKEN:
			self.AUTH_TOKEN = Bash(f"{self.BIN} {self.ROLE} auth admin --p2p.network blockspacerace").value()
		headers = { 'Authorization': 'Bearer ' + self.AUTH_TOKEN }
		return super().rpcCall(method, headers, params)
	
	def getNetwork(self):
		return self.rpcCall('header.NetworkHead')["header"]["chain_id"]

	def getVersion(self):
		ver = Bash(f"{self.BIN} version | head -n 1").value()
		return ver.split(" ")[-1]

	def getLocalVersion(self):
		try:
			return self.getVersion()
		except Exception as e:
			ver = self.conf.getOrDefault('chain.localVersion')
			if ver is None:
				raise Exception('No local version of the software specified!') from e
			return ver

	def getHeight(self):
		return self.rpcCall('header.LocalHead')['header']['height']
	
	def getNetworkHeight(self):
		return self.rpcCall('header.NetworkHead')['header']['height']

	def getBlockHash(self):
		return self.rpcCall('header.NetworkHead')['header']['last_block_id']['hash']

	def getPeerCount(self):
		return len(self.rpcCall('p2p.Peers'))

	def isSynching(self):
		return not self.rpcCall('das.SamplingStats')['catch_up_done']

	def getSamplesHeight(self):
		return self.rpcCall('das.SamplingStats')['head_of_sampled_chain']
