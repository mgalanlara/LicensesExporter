"""
licenses_exporter: A prometheus client to export lsmon & lmutil licenses
Tonin 2018. University of Cordoba
"""

import subprocess
from prometheus_client import Gauge, start_http_server, REGISTRY, PROCESS_COLLECTOR, PLATFORM_COLLECTOR, GC_COLLECTOR
from selenium import webdriver
from datetime import datetime
import time
import sys
import os
import re
import ruamel.yaml as yaml
import requests
import pandas as pd
import socket

#unregister default metrics
REGISTRY.unregister(PROCESS_COLLECTOR)
REGISTRY.unregister(PLATFORM_COLLECTOR)
REGISTRY.unregister(GC_COLLECTOR)

#Licenses & config file
CONFIG_FILE = 'config.yml'
WRITEHTML = False
DEBUG = False
TRACE = False
VERBOSE = False
SUMMARY = True

if DEBUG: VERBOSE = True

driver = None

def appendFeature(feature_list,feature):
	if feature.name == "NULL":
		return
	else:
		feature_list.append(feature)

def isWindows():
	ret = True if os.name == 'nt' else False
	return ret

def isDocker():
	path = '/proc/self/cgroup'
	return (
		os.path.exists('/.dockerenv') or
		os.path.isfile(path) and any('docker' in line for line in open(path))
	)

def isNan(num):
	return num != num

def value(row,label):
	if type(label) is int:
		return row[int(label)]
	else:
		return row[label]

def trace(label,msg):
	print("TRACE:",label," ",msg)

class User(object):
	def __init__(self, name):
		self.name = name
		self.hostName = None
		self.device = None
		self.date = None

	def printUser(self):
		print("\t",self.name," ",self.hostName," ",self.device," ",self.date)

	def printUserToError(self):
		print("\t",self.name," ",self.hostName," ",self.device," ",self.date, file=sys.stderr)

class Feature(object):
	def __init__(self, name, app, parent):
		self.name = name
		self.maxLicenses = 0
		self.inUse = 0
		self.app = app
		self.parent = parent
		self.userList = []

		#Vemos si tenemos translaciones de etiquetes de features
		try:
			dummy = parent.features['translate']
			self.translatable = True
		except:
			self.translatable = False
			return

		#Realizamos la traduccion del self.name
		if parent.features['translate']['at_stage'] == 1:
			self.translate()

	def translate(self):
			r = re.search(self.parent.features['translate']['search'],self.name)
			if r is not None:
				self.name = self.parent.features['translate']['translations'][r.group('feature_name')] + " " + r.group('feature_suffix')
			else:
				#Si no encontramos traslacion debemos marcarla para borrar
				self.name = "NULL"

	def isUsing(self):
		if self.inUse > 0.0:
			return True
		else:
			return False

	def printFeature(self):
		if not VERBOSE:
			return
		print("app=",self.app," feature=",self.name," max=",self.maxLicenses," current=",self.inUse)
		for user in self.userList:
			user.printUser()

class App(object):
	def __init__(self, parent, argsDict):
		self.parent = parent
		for key,value in argsDict.items():
			setattr(self,key,value)
		#Hacemos lista los strings separados por comas
		try:
			self.features['include'] =  str(self.features['include']).split(",")
		except:
			pass
		try:
			self.users['url']['index'] = str(self.users['url']['index']).split(",")
		except:
			pass
		try:
			self.label['item'] = self.label['item'].split(",")
		except:
			pass

		self.featureList = []
		if(self.type == 'lsmon'):
			self.parse = self.parseLsmon
		elif(self.type == 'lmutil'):
			self.parse = self.parseLmutil
		elif(self.type == 'rlmutil'):
			self.parse = self.parseRlmutil
		elif(self.type == 'web'):
			self.parse = self.parseWeb
		elif(self.type == 'webtable'):
			self.parse = self.parseWebTable
		elif(self.type == 'webtablejs'):
			self.parse = self.parseWebTableJs
		elif(self.type == 'rawsocket'):
			self.parse = self.parseRawSocket
		self.online = False
		driver = None

	def df_parse_features(self,feature_tbl):
		has_features = False
		if DEBUG: print("DEBUG: features_to_include: ",self.features['include'])
		if not feature_tbl.empty:
			#Hemos encontrado cosas
			for index,row in feature_tbl.iterrows():
				if TRACE: trace(self.name,"En bucle iterrows de df_parse_features")
				if not isNan(row[self.features['label']['name']]):
					if TRACE: trace(self.name,"not isNan en  df_parse_features")
					#No siempre tiene que estar product definido, lo ponemos en un try
					try:
						if self.product['include'] is not None:
							if not str(self.product['include']) in str(row[self.product['label']]):
								continue
					except:
						pass
					if DEBUG: print("DEBUG: row[self.feature_label_name: ",row[self.features['label']['name']])
					if row[self.features['label']['name']] in self.features['include'] or self.features['include'][0] == 'ALL':
						if DEBUG:
							print("DEBUG: ",row[self.features['label']['name']]," Total: ",row[self.features['label']['total']]," Usadas: ",row[self.features['label']['used']])
						self.online = True
						feature = Feature(row[self.features['label']['name']],self.name,self)
						appendFeature(self.featureList,feature)
						feature.maxLicenses = float(row[self.features['label']['total']])
						feature.inUse = float(row[self.features['label']['used']])
						if isNan(feature.inUse):
							feature.inUse = 0;
						if self.used_as_free:
							feature.inUse = feature.maxLicenses - feature.inUse
						has_features = True
		return has_features

	def df_parse_users(self,users_tbl,current_feat):
		if not users_tbl.empty:
			for index,row in users_tbl.iterrows():
				if index == self.users['table']['skip_header']:
					continue
				if self.users['table']['method'] == 'search':
					#TODO: En base a codemeter solo sacamos info del hostname, ya lo iremos ampliando
					for feat in self.featureList:
						if feat.name in row[self.users['label']['featurename']]:
							user = User(value(row,self.users['label']['username'])) if self.users['label']['username'] is not None else "None"
							feat.userList.append(user)
							user.hostName = value(row,self.users['label']['hostname']) if self.users['label']['hostname'] is not None else "None"
							user.date = value(row,self.users['label']['date']) if self.users['label']['date'] is not None else "None"
				if self.users['table']['method'] == 'index':
					user = User(value(row,self.users['label']['username']) if self.users['label']['username'] is not None else "None")
					current_feat.userList.append(user)
					user.hostName = value(row,self.users['label']['hostname']) if self.users['label']['hostname'] is not None else "None"
					user.date = value(row,self.users['label']['date']) if self.users['label']['date'] is not None else "None"

	def parseWebFeaturesUrl(self):
		url_range  = self.features['url']['index'] if self.features['url']['index'] is not None else 2
		for i in range(1,url_range):
			if TRACE: trace(self.name," En bucle parseweburl")
			#Componemos la url
			if url_range == 2:
				url = self.features['url']['prefix']
			else:
				url = self.features['url']['prefix'] + str(i) + self.features['url']['suffix']
			if DEBUG: print("URL: ",url)
		return url

	def parseWebUsersUrl(self,i):
		passFeature = False
		#Me salto los features que no se esten usando
		for current_feat in self.featureList:
			if current_feat.name == self.features['include'][self.users['url']['index'].index(i)]:
				if current_feat.isUsing() is False:
					passFeature = True
				else:
					break
		if passFeature:
			return None,None
		if self.users['url']['suffix'] is not None:
			url = self.users['url']['prefix'] + str(i) + self.users['url']['suffix']
		else:
			url = self.users['url']['prefix']
		return current_feat,url

	def parseWebTableJs(self):
		if TRACE: trace(self.name," Entrando en parseWebJS")
		self.featureList = []
		self.online = False

		#Parse features
		url = self.parseWebFeaturesUrl()
		driver = self.parent.driver
		try:
			driver.get(url)
		except:
			#Si se produce una excepcion retornamos
			print("Excepcion en driver.get de pwtJs")
			return
		try:
			table = driver.find_element_by_id(self.features['js']['id'])
		except:
			print("Excepción en driver.find de PwtJS")
			return
		try:
			table_html = table.get_attribute(self.features['js']['attr'])
		except:
			print("Excepción en table.get_attribute de PwtJS")
			return
		try:
			feature_tbl = pd.read_html(table_html)[0]
		except:
			print("Excepcion en read_html de pwtJs")
			return
		if self.features['js']['iloc'] is not None:
			feature_tbl.columns = feature_tbl.iloc[int(self.features['js']['iloc'])]
			feature_tbl.drop([int(self.features['js']['iloc'])],inplace=True)
		has_features = self.df_parse_features(feature_tbl)
		if DEBUG: print("Has features: ",has_features)
		if not has_features:
			if DEBUG: print("Salgo por not has features")
			return
		#Parse users
		#Lo meto todo en un try por si falla
		try:
			if has_features and self.users['monitor']:
				for i in self.users['url']['index']:
					current_feat,url = self.parseWebUsersUrl(i)
					if url is not None:
						driver.get(url)
						table = driver.find_element_by_id(self.users['js']['id'])
						table_html = table.get_attribute(self.users['js']['attr'])
						users_tbl = pd.read_html(table_html)[0]
						if self.users['js']['iloc'] is not None:
							users_tbl.columns = users_tbl.iloc[int(self.users['js']['iloc'])]
							users_tbl.drop([int(self.users['js']['iloc'])],inplace=True)
						self.df_parse_users(users_tbl,current_feat)
		except:
			print("Excepcion en parse users de pwtJs")
			return

	def parseWebTable(self):
		if TRACE: trace(self.name," Entrando en parseWebTable")
		self.featureList = []
		self.online = False

		url = self.parseWebFeaturesUrl()
		#Aquí puede fallar, controlamos el error
		try:
			all_feature_tables = pd.read_html(url)
		except Exception as exc:
			print("Excepción en pd.read_html de parseWebTable")
			print("Excepción: ",exc)
			return

		feature_tbl = all_feature_tables[self.features['table']['index']]
		#monitorizamos las licencias
		has_features = self.df_parse_features(feature_tbl)
		#monitorizamos los usuarios:
		if has_features and self.users['monitor']:
			for i in self.users['url']['index']:
				current_feat,url = self.parseWebUsersUrl(i)
				if url is not None:
					all_users_table = pd.read_html(url)
					users_tbl = all_users_table[self.users['table']['index']]
					self.df_parse_users(users_tbl,current_feat)

	def parseWeb(self):
		if TRACE: trace(self.name," Entrando en parseweb")
		self.featureList = []
		self.online = False

		url = self.parseWebFeaturesUrl()
		if DEBUG: print("URL: ",self.name," ",url)
		#Realizamos el request
		Response = requests.get(url)
		if TRACE: print("TRACE: ",self.name," parseweb despues de request")
		content = Response.content

		if WRITEHTML:
			name = str(i) + ".web"
			file = open(name,"wb")
			file.write(content)
			file.close()
			print("DEBUGURL: ",self.name," ",url)
			print("DEBUGREGEX: ",self.match_exist)

		#Vemos si existe algo para este parametro
		match = re.findall(self.features['match']['exist'], str(content), re.MULTILINE)
		if DEBUG: print("PARSEWEBMATCH: ",self.name," ",match)
		if match:
			if TRACE: trace(self.name,"En if match parseweb")
			feature = Feature(match[0],self.name,self)
			self.online = True
			appendFeature(self.featureList,feature)
			#Existe luego leemos el numero total de licencias y las que estan en uso
			total = re.findall(self.features['match']['total'], str(content), re.MULTILINE)
			inUse = re.findall(self.features['match']['used'], str(content), re.MULTILINE)
			feature.maxLicenses = float(total[0])
			feature.inUse = float(inUse[0])
			if self.used_as_free:
				feature.inUse = feature.maxLicenses - feature.inUse
				if DEBUG:
					print("Total ",feature.name,": ",feature.maxLicenses)
					print("Inuse ",feature.name,": ",feature.inUse)
			else:
				if DEBUG: print("DEBUG: ",self.name," ",i,"nomatch. Pattern ",self.features['match']['exist'])

	def parseLsmon(self):
		self.featureList = []
		self.online = False
		p = subprocess.Popen([self.parent.LSMONCMD,self.license_server],stdin=subprocess.PIPE,stdout=subprocess.PIPE,universal_newlines=True)
		output = p.stdout
		p.stdin.close()
		for _output in output:
			if type(_output) == type(''):
				lines = _output.split('\n')
				for line in lines:
					if 'Feature name' in line:
						aux = line.split(":",1)[1][1:-3].replace('"','')
						if aux in self.features['include'] or self.features['include'][0] == "ALL":
							feature = Feature(aux, self.name,self)
							self.online = True
							appendFeature(self.featureList,feature)
						else:
							feature = None
					if 'Maximum concurrent user' in line and feature:
						feature.maxLicenses = float(line.split(":",1)[1][1:])
					if 'Unreserved tokens in use' in line and feature:
						feature.inUse = float(line.split(":",1)[1][1:])
					if  'Feature version' in line and feature:
						feature.name = feature.name + line.split(":",1)[1][1:].strip('"')
						if feature.translatable:
							if self.features['translate']['at_stage'] == 2:
								feature.translate()
					if 'User name' in line and feature and self.users['monitor']:
						user = User(line.split(":",1)[1][1:])
						feature.userList.append(user)
					if 'Host name' in line and feature and self.users['monitor']:
						user.hostName =  line.split(":",1)[1][1:]

	def parseLmutil(self):
		self.featureList = []
		self.online = False
		feature = None
		output = subprocess.getstatusoutput(self.parent.LMUTILCMD + ' ' + self.license_server)
		for _output in output:
			if type(_output) == type(''):
				lines = _output.split('\n')
				for line in lines:
					if 'Users of' in line:
						r = re.search('Users of (.*):  \(Total of (.*)licenses? issued;  Total of (.*) licenses? in use\)',line)
						if r is not None:
							if r.group(1) in self.features['include'] or self.features['include'][0] == "ALL":
								feature = Feature(r.group(1), self.name,self)
								self.online = True
								feature.maxLicenses = float(r.group(2))
								feature.inUse = float(r.group(3))
								appendFeature(self.featureList,feature)
							else:
								feature = None
					if ', start' in line and feature and self.users['monitor']:
						r = re.search('^\s+(.*) (.*) (.*) \((.*)\) \((.*)/(.*) (.*)\), start (.*)',line)
						user = User(r.group(1))
						user.hostName = r.group(2)
						user.device = r.group(3)
						user.date = r.group(8)
						feature.userList.append(user)

	def parseRlmutil(self):
		self.featureList = []
		self.online = False
		output = subprocess.getstatusoutput(self.parent.RLMUTILCMD + ' ' + self.license_server)
		for _output in output:
			if type(_output) == type(''):
				lines = _output.split('\n')
				for line in lines:
					feature = None
					if any(label in line for label in self.label['item']):
						feat_name = line.strip().split(" ")[0]
					#monitor features
					if self.label['count'] in line:
						r = re.search('.+count: (.*), (.*) inuse: (.*),',line)
						if r is not None:
							if r.group(1) in self.features['include'] or self.features['include'][0] == "ALL":
									feature = Feature(feat_name, self.name,self)
									self.online = True
									feature.maxLicenses = float(r.group(1))
									feature.inUse = float(r.group(3))
									appendFeature(self.featureList,feature)
							else:
									feature = None
					#monitor users
					if 'handle' in line  and self.users['monitor']:
						r = re.search('^\s+(.*) (.*): (.*)@(.*) (.*) at (.*)  \(handle.*',line)
						user = User(r.group(3))
						user.hostName = r.group(4)
						user.device = r.group(4)
						user.date = r.group(6)
						#tenemos que averiguar a que feature se refiere
						for feat in self.featureList:
							if r.group(1) == feat.name:
								feat.userList.append(user)
	def parseRawSocket(self):
		self.featureList = []
		self.online = False

		host = socket.gethostbyname(self.license_server)
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.settimeout(self.timeout)
		try:
			sock.connect((host, self.license_port))
			if hasattr(self,'connect_only'):
				pass
			else:
				a = sock.recv(self.recv_bytes)
			feature = Feature(self.name,self.name,self)
			self.online = True
			feature.maxLicenses = 999
			feature.inUse = 888
			appendFeature(self.featureList,feature)
		except:
			pass
		sock.close()

	def printFeatures(self):
		for feature in self.featureList:
			feature.printFeature()
		if self.featureList:
			return True
		else:
			return False

	def updateMetric(self):
		self.parse()
		self.parent.license_server_status.labels(app=self.name,fqdn=self.license_server,
												master='true',port='port',
												version='version').set(self.online)
		for feature in self.featureList:
			self.parent.license_feature_issued.labels(app=feature.app,name=feature.name).set(feature.maxLicenses)
			self.parent.license_feature_used.labels(app=feature.app,name=feature.name).set(feature.inUse)
			for user in feature.userList:
				try:
					self.parent.license_feature_used_users.labels(app=feature.app,name=feature.name,user=user.name,
																host=user.hostName,device=user.device).set(1)
				except:
					print("Error en used_users.label", file=sys.stderr)
					user.printUserToError()

class Apps(object):
	def __init__(self,cfgFile):
		self.appList = []
		with open(cfgFile, 'r') as yamlFile:
			self.cfg = yaml.safe_load(yamlFile)
		for appCfg in self.cfg['licenses']:
			if self.cfg['onlythis'] is None:
				if not appCfg['skip']:
					app = App(self, appCfg)
					self.appList.append(app)
			else:
				if isinstance(self.cfg['onlythis'],str):
					self.cfg['onlythis'] = self.cfg['onlythis'].split(",")
				if appCfg['name'] in self.cfg['onlythis']:
					app = App(self, appCfg)
					self.appList.append(app)

		self.license_feature_used = Gauge('license_feature_used','number of licenses used',['app','name'])
		self.license_feature_issued = Gauge('license_feature_issued','max number of licenses',['app','name'])
		self.license_feature_used_users = Gauge('license_feature_used_users','license used by user',['app','name','user','host','device'])
		self.license_server_status = Gauge('license_server_status','status of the license server',['app','fqdn','master','port','version'])
		self.PORT = self.cfg['config']['port']
		self.SLEEP = self.cfg['config']['sleep']
		self.LSMONCMD = self.cfg['config']['lsmon_cmd'] if not isWindows() else self.cfg['config']['lsmon_cmd'].replace('/','\\')
		self.LMUTILCMD = self.cfg['config']['lmutil_cmd'] if not isWindows() else self.cfg['config']['lmutil_cmd'].replace('/','\\')
		self.RLMUTILCMD = self.cfg['config']['rlmutil_cmd'] if not isWindows() else self.cfg['config']['rlmutil_cmd'].replace('/','\\')
		self.WEBDRIVER_TYPE = self.cfg['config']['webdriver']['type']
		self.WEBDRIVER_URL = self.cfg['config']['webdriver']['private-url'] if  isDocker() else self.cfg['config']['webdriver']['public-url']

		if self.WEBDRIVER_TYPE == 'local':
			self.driver = webdriver.Chrome()
		elif self.WEBDRIVER_TYPE == 'remote':
			driver_options = webdriver.ChromeOptions()
			self.driver = webdriver.Remote( 
				command_executor=f"{self.WEBDRIVER_URL}",
				options=driver_options
			)
			self.driver.set_page_load_timeout(10)

	def parse(self):
		for app in self.appList:
			app.parse()

	def printApps(self):
		totalOnline = 0
		totalOffline = 0
		for app in self.appList:
			if app.printFeatures():
				totalOnline = totalOnline + 1
			else:
				totalOffline = totalOffline + 1
		if SUMMARY:
			now = datetime.now()
			dt_string = now.strftime("%d/%m/%Y %H:%M:%S")
			print(dt_string," TOTAL ONLINE: ",totalOnline," TOTAL OFFLINE: ",totalOffline)

	def updateMetric(self):
		self.license_feature_used_users._metrics.clear()
		for app in self.appList:
			app.updateMetric()


if __name__ == '__main__':
	apps = Apps(CONFIG_FILE)
	start_http_server(apps.PORT)
	while True:
		#try:
			apps.updateMetric()
			if VERBOSE or SUMMARY:
				apps.printApps()
			sys.stdout.flush()
		#except Exception as exc:
			#print("EXCEPCION: ",exc),
			time.sleep(apps.SLEEP)
