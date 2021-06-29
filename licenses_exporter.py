"""
licenses_exporter: A prometheus client to export lsmon & lmutil licenses
Tonin 2018. University of Cordoba
"""

#Develop or Production
DEV = False

import subprocess
if not DEV: from prometheus_client import Gauge, start_http_server
import time
import sys
import re
import ruamel.yaml as yaml
import requests
import pandas as pd

#Licenses & config file
CONFIG_FILE = 'config.yml'
WRITEHTML = False
DEBUG = False
TRACE = False
VERBOSE = True

if DEBUG: VERBOSE = True

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
        print >> sys.stderr, "\t",self.name," ",self.hostName," ",self.device," ",self.date

class Feature(object):
    def __init__(self, name, app):
        self.name = name
        self.maxLicenses = 0
        self.inUse = 0
        self.app = app
        self.userList = []

    def isUsing(self):
        if self.inUse > 0.0:
            return True
        else:
            return False
        
    def printFeature(self):
        print("app=",self.app," feature=",self.name," max=",self.maxLicenses," current=",self.inUse)
        for user in self.userList:
            user.printUser()

class App(object):
    def __init__(self, parent, argsDict):
        self.parent = parent
        for key,value in argsDict.items():
            if key in ['features_to_include','users_index_url','rlm_item_label']:
                setattr(self,key,str(value).split(","))
            else:    
                setattr(self,key,value)
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
        self.online = False

    def parseWebTable(self):
        if TRACE: trace(self.name," Entrando en parseWebTable")
        self.featureList = []
        self.online = False

        #Bucle para iterar segun el parametro
        #Si el parametro es null no hay sufijo
        url_range  = self.fature_max_url_param if self.feature_max_url_param is not None else 2

        for i in range(1,url_range):
            if TRACE: trace(self.name," En bucle parseweb")
            #Componemos la url
            if url_range == 2:
                url = self.feature_prefix_url
            else:
                url = self.feature_prefix_url + str(i) + self.feature_suffix_url

        all_feature_tables = pd.read_html(url)
        feature_tbl = all_feature_tables[self.feature_table_index]
        #monitorizamos las licencias
        if not feature_tbl.empty:
            #Hemos encontrado cosas
            for index,row in feature_tbl.iterrows():
                if not isNan(row[self.feature_label_name]):
                    if row[self.feature_label_name] in self.features_to_include:
                        if DEBUG:
                            print(row[self.feature_label_name]," Total: ",row[self.feature_label_total]," Usadas: ",row[self.feature_label_in_use])
                        self.online = True
                        feature = Feature(row[self.feature_label_name],self.name)
                        self.featureList.append(feature)
                        feature.maxLicenses = float(row[self.feature_label_total])
                        feature.inUse = float(row[self.feature_label_in_use])
                        if self.used_as_free:
                            feature.inUse = feature.maxLicenses - feature.inUse
        #monitorizamos los usuarios:
            if self.monitor_users:
                for i in self.users_index_url:
                    passFeature = False
                    #Me salto los features que no se esten usando
                    for current_feat in self.featureList:
                        if current_feat.name == self.features_to_include[self.users_index_url.index(i)]:
                            if current_feat.isUsing() is False: 
                                passFeature = True
                            else:
                                break
                    if passFeature: 
                        continue        

                    if self.users_suffix_url is not None:
                        url = self.users_prefix_url + str(i) + self.users_suffix_url
                    else:
                        url = self.users_prefix_url

                    all_users_table = pd.read_html(url)
                    users_tbl = all_users_table[self.users_table_index]

                    if not users_tbl.empty:
                        for index,row in users_tbl.iterrows():
                            if index == self.users_table_skip_header:
                                continue
                            if self.users_search_feature:                            
                                #TODO: En base a codemeter solo sacamos info del hostname, ya lo iremos ampliando
                                for feat in self.featureList:
                                    if feat.name in row[self.users_label_feature_name]:
                                        user = User(value(row,self.users_label_username) if self.users_label_username is not None else "None")
                                        feat.userList.append(user)
                                        user.hostName = value(row,self.users_label_hostname) if self.users_label_hostname is not None else "None"
                                        user.date = value(row,self.users_label_date) if self.users_label_date is not None else "None" 
                            if self.users_index_feature:
                                user = User(value(row,self.users_label_username) if self.users_label_username is not None else "None")
                                current_feat.userList.append(user)
                                user.hostName = value(row,self.users_label_hostname) if self.users_label_hostname is not None else "None"
                                user.date = value(row,self.users_label_date) if self.users_label_date is not None else "None" 

    def parseWeb(self):
        if TRACE: trace(self.name," Entrando en parseweb")
        self.featureList = []
        self.online = False
        try:
            #Bucle para iterar segun el parametro
            #Si el parametro es 0 no hay sufijo
            if self.max_url_param == 0:
                self.max_url_param = 2
                NoSuffix = True
            else:
                NoSuffix = False

            for i in range(1,self.max_url_param):
                if TRACE: trace(self.name," En bucle parseweb")
                #Componemos la url
                if not NoSuffix:
                    url = self.prefix_url + str(i) + self.suffix_url
                else:
                    url = self.prefix_url
                        
                if DEBUG: print("URL: ",self.name," ",url)
                #Realizamos el request
                Response = requests.get(url)
                if TRACE: print("TRACE: ",self.name," parseweb despues de request")
                content = Response.content
            
                if WRITEHTML:
                    name = str(i) + ".web"
                    file = open(name,"w")
                    file.write(content)
                    file.close()
                    print("DEBUGURL: ",self.name," ",url)
                    print("DEBUGREGEX: ",self.match_exist)

                #Vemos si existe algo para este parametro
                match = re.findall(self.match_exist, str(content), re.MULTILINE)
                if DEBUG: print("PARSEWEBMATCH: ",self.name," ",match)
                if match:
                    if TRACE: trace(self.name,"En if match parseweb")
                    feature = Feature(match[0],self.name)
                    self.online = True
                    self.featureList.append(feature)
                    #Existe luego leemos el numero total de licencias y las que estan en uso
                    if TRACE: trace("PARSEWEBMATCH1: ",self.name)
                    total = re.findall(self.match_total, str(content), re.MULTILINE)
                    if TRACE: trace("PARSEWEBMATCH2: ",self.name)
                    inUse = re.findall(self.match_used, str(content), re.MULTILINE)
                    if TRACE: trace("PARSEWEBMATCH3: ",self.name)
                    feature.maxLicenses = float(total[0])
                    if TRACE: trace("PARSEWEBMATCH4: ",self.name)
                    feature.inUse = float(inUse[0])
                    if self.used_as_free:
                        feature.inUse = feature.maxLicenses - feature.inUse
                        if DEBUG:            
                            print("Total ",feature.name,": ",feature.maxLicenses)
                            print("Inuse ",feature.name,": ",feature.inUse)
                    else:
                        if DEBUG: print("DEBUG: ",self.name," ",i,"nomatch. Pattern ",self.match_exist)
        except  Exception as e:
            if VERBOSE: print("EXC_PARSEWEB: ",self.name," ",e)

    def parseLsmon(self):
        self.featureList = []
        self.online = False
        output = subprocess.getstatusoutput(self.parent.LSMONCMD + ' ' + self.license_server)
        for _output in output:
            if type(_output) == type(''):
                lines = _output.split('\n')
                for line in lines:
                    if 'Feature name' in line:
                        aux = line.split(":",1)[1][1:-3].replace('"','')
                        if aux in self.features_to_include.split(","):
                            feature = Feature(aux, self.name)
                            self.online = True
                            self.featureList.append(feature)
                        else:
                            feature = None
                    if 'Maximum concurrent user' in line and feature:
                        feature.maxLicenses = float(line.split(":",1)[1][1:])
                    if 'Unreserved tokens in use' in line and feature:
                        feature.inUse = float(line.split(":",1)[1][1:])
                    if 'User name' in line and feature and self.monitor_users:
                        user = User(line.split(":",1)[1][1:])
                        feature.userList.append(user)
                    if 'Host name' in line and feature and self.monitor_users:
                        user.hostName =  line.split(":",1)[1][1:]

    def parseLmutil(self):
        self.featureList = []
        self.online = False
        output = subprocess.getstatusoutput(self.parent.LMUTILCMD + ' ' + self.license_server)
        for _output in output:
            if type(_output) == type(''):
                lines = _output.split('\n')
                for line in lines:
                    feature = None
                    if 'Users of' in line:
                        r = re.search('Users of (.*):  \(Total of (.*)licenses? issued;  Total of (.*) licenses? in use\)',line)
                        if r is not None:
                        	if r.group(1) in self.features_to_include.split(","):
                            		feature = Feature(r.group(1), self.name)
                            		self.online = True
                            		feature.maxLicenses = float(r.group(2))
                            		feature.inUse = float(r.group(3))
                            		self.featureList.append(feature)
                        	else:
                            		feature = None
                    if ', start' in line and feature and self.monitor_users and r is not None:
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
                    if any(label in line for label in self.rlm_item_label):
                        feat_name = line.strip().split(" ")[0]
                    #monitor features
                    if self.rlm_count_label in line:
                        r = re.search('.+count: (.*), (.*) inuse: (.*),',line)
                        if r is not None:
                        	if r.group(1) in self.features_to_include or self.features_to_include[0] == "ALL":
                            		feature = Feature(feat_name, self.name)
                            		self.online = True
                            		feature.maxLicenses = float(r.group(1))
                            		feature.inUse = float(r.group(3))
                            		self.featureList.append(feature)
                        	else:
                            		feature = None
                    #monitor users
                    if 'handle' in line  and self.monitor_users:
                        r = re.search('^\s+(.*) (.*): (.*)@(.*) (.*) at (.*)  \(handle.*',line)
                        user = User(r.group(3))
                        user.hostName = r.group(4)
                        user.device = r.group(4)
                        user.date = r.group(6)
                        #tenemos que averiguar a que feature se refiere
                        for feat in self.featureList:
                            if r.group(1) == feat.name:
                                feat.userList.append(user)

    def printFeatures(self):
        for feature in self.featureList:
            feature.printFeature()

    def updateMetric(self):
        self.parse()
        if not DEV:
            self.parent.license_server_status.labels(app=self.name,fqdn=self.license_server,
                                                    master='true',port='port',
                                                    version='version').set(self.online)
        for feature in self.featureList:
            if not DEV:
                self.parent.license_feature_issued.labels(app=feature.app,name=feature.name).set(feature.maxLicenses)
                self.parent.license_feature_used.labels(app=feature.app,name=feature.name).set(feature.inUse)
            for user in feature.userList:
                try:
                    if not DEV:
                        self.parent.license_feature_used_users.labels(app=feature.app,name=feature.name,user=user.name,
                                                                    host=user.hostName,device=user.device).set(1)
                except:
                    print >> sys.stderr, "Error en used_users.label"
                    user.printUserToError()

class Apps(object):
    def __init__(self,cfgFile):
        self.appList = []
        with open(cfgFile, 'r') as yamlFile:
            self.cfg = yaml.safe_load(yamlFile)
        for appCfg in self.cfg['licenses']:
            app = App(self, appCfg)
            self.appList.append(app)

        if not DEV:
            self.license_feature_used = Gauge('license_feature_used','number of licenses used',['app','name'])
            self.license_feature_issued = Gauge('license_feature_issued','max number of licenses',['app','name'])
            self.license_feature_used_users = Gauge('license_feature_used_users','license used by user',['app','name','user','host','device'])
            self.license_server_status = Gauge('license_server_status','status of the license server',['app','fqdn','master','port','version'])
        self.PORT = self.cfg['config']['port']
        self.SLEEP = self.cfg['config']['sleep']
        self.LSMONCMD = self.cfg['config']['lsmon_cmd']
        self.LMUTILCMD = self.cfg['config']['lmutil_cmd']
        self.RLMUTILCMD = self.cfg['config']['rlmutil_cmd']

    def parse(self):
        for app in self.appList:
            app.parse()

    def printApps(self):
        for app in self.appList:
            app.printFeatures()

    def updateMetric(self):
        if not DEV:
            self.license_feature_used_users._metrics.clear()
        for app in self.appList:
            app.updateMetric()

if __name__ == '__main__':
    apps = Apps(CONFIG_FILE)
    if not DEV:
        start_http_server(apps.PORT)
    while True:
        apps.updateMetric()
        if VERBOSE:
            apps.printApps()
            sys.stdout.flush()
            time.sleep(apps.SLEEP)