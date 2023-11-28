import time
import requests
import json
import pprint

class ixNet_run:
    def __init__(self, server, port, version='v1'):
        # 定义请求头
        self.urlHeadersJson = {'content-type': 'application/json'}
        self.urlHeadersData = {'content-type': 'application/octet-stream'}
        self.server = server
        self.port = port
        self.version = version
        # 构建基础URL
        self.baseUrl = f"http://{server}:{port}/api/{version}"
        self.srvUrl = f"http://{self.server}:{self.port}"
        self.sessionId = None
        self.response = None
        self.debug = False

    def connect(self, timeout=60):
        # 获取IXNetwork会话并设置会话ID
        res = self.getIxNetSessions()
        self.sessionId = str(res[0]['id'])
        self.ixNetUrl = f"{self.baseUrl}/sessions/{self.sessionId}/ixnetwork"
        self._root = self.ixNetUrl
        self.execDict = self.getOptions(self.ixNetUrl, 'operations')
        self.execstatisticsViewDict = self.getOptions(f"{self.ixNetUrl}/statistics/view", 'operations')

    def waitForComplete(self, response, sessionUrl, timeout=90):
        # 等待操作完成
        if 'errors' in response.json():
            print(response.json()["errors"][0])
            raise Exception('失败：需要退出')
        #print(response.json())
        print("\t状态", "\t", response.json()["state"])
        state = self.getAttribute(sessionUrl, "state")
        while response.json()["state"] == "IN_PROGRESS" and state == "IN_PROGRESS":
            if timeout == 0:
                break
            time.sleep(1)
            state = self.getAttribute(sessionUrl, "state")
            print("\t\t", state)
            timeout = timeout - 1

    # def waitForComplete(self, sessionUrl, timeout=90):
    #     if 'errors' in self.response.json():
    #         print(self.response.json()["errors"][0])  # 输出错误信息
    #         raise Exception('执行失败：需要退出')  # 抛出异常，表示执行失败
    #     print("\t状态", "\t", self.response.json()["state"])  # 打印当前状态
    #
    #     while self.response.json()["state"] == "IN_PROGRESS":
    #         if timeout == 0:
    #             break
    #         time.sleep(1)  # 暂停1秒，等待进度更新
    #         state = self.getAttribute(self.response.json()["url"], "state")  # 获取进度状态
    #         print("\t\t", state)  # 打印进度状态
    #         timeout = timeout - 1  # 减少超时时间

    def getRoot(self):
        return self._root

    def commit(self):
        pass

    def remapIds(self, localIdList):
        if type(localIdList) == list:
            return localIdList
        else:
            return [localIdList]

    def checkError(self):
        if not self.response.ok:
            raise TestFailedError(self.response.text)

    def getList(self, objRef, child):
        # 获取对象列表
        if self.debug:
            print("GetList: %s/%s/" % (objRef, child))
        baseUrl = objRef
        if self.srvUrl not in objRef:
            baseUrl = self.srvUrl + objRef
        try:
            self.response = requests.get(f"{baseUrl}/{child}", headers=self.urlHeadersJson)
        except Exception as e:
            raise Exception('发生错误：', e)
        self.checkError()
        objs = [f"{objRef}/{child}/{str(i['id'])}" for i in self.response.json()]
        return objs

    def getIxNetSessions(self):
        # 获取IXNetwork会话列表
        if self.debug:
            print(f"{self.baseUrl}/sessions")
        try:
            self.response = requests.get(f"{self.baseUrl}/sessions", headers=self.urlHeadersJson)
        except Exception as e:
            raise Exception('发生错误：', e)
        self.checkError()
        sessions = [i for i in self.response.json() if i['state'] == 'ACTIVE']
        return sessions

    def add(self, objRef, child, *args):
        # 添加对象
        try:
            data = args[0]
        except:
            data = [{}]
        if self.debug:
            print("ADD:", f"{objRef}/{child}/", data)
        try:
            self.response = requests.post(f"{objRef}/{child}/", data=json.dumps(data),
                                          headers=self.urlHeadersJson)
        except Exception as e:
            raise Exception('发生错误：', e)
        self.checkError()
        return [f"http://{self.server}:{self.port}{i['href']}" for i in self.response.json()['links']]

    def remove(self, objRef):
        # 删除对象
        try:
            self.response = requests.delete(objRef)
        except Exception as e:
            raise Exception('发生错误：', e)
        self.checkError()
        return self.response.json()

    def execute(self, *args):
        args = list(args)
        if self.debug:
            print("执行参数:", args)
        execName = args[0]
        posturl = ''
        # posturl = self.execDict[execName]
        print("执行命令: ", execName)
        try:
            posturl = self.srvUrl + self.execDict[execName]
        except:
            pass
        if self.debug:
            print("初始POST URL", posturl)

        if execName == "loadConfig" and self._loadConfig(args[1]):
            data = {'filename': self.ixncfgname}
            try:
                self.response = requests.post(url=posturl, data=json.dumps(data), headers=self.urlHeadersJson)
            except Exception as e:
                raise Exception('发生错误: ', e)
            self.waitForComplete(posturl)
            self.checkError()
            return self.response.json()

        elif execName == "importBgpRoutes":
            argx = ['arg%d' % (i + 1,) for i in range(len(args[1:]))]
            tmp = []
            for i in args[1:]:
                try:
                    tmp.append(i.replace(self.srvUrl, ""))
                except:
                    tmp.append(i)

            data = dict(zip(argx, tmp))
            posturl = self.srvUrl + data['arg1']

        else:
            argx = ['arg%d' % (i + 1,) for i in range(len(args[1:]))]
            argsv = args[1:]
            tmp_values = []
            for val in argsv:
                if isinstance(val, (list, tuple)):
                    if all(isinstance(elem, (list, tuple)) for elem in val):
                        kstruct = []
                        for elm in val:
                            if self.debug:
                                print("嵌套值: ", elm)
                            argxy = ['arg%d' % (i + 1,) for i in range(len(elm))]
                            v = dict(zip(argxy, elm))
                            kstruct.append(v)
                        tmp_values.append(kstruct[:])
                    else:
                        tmp_values.append([v for v in val])
                else:
                    tmp_values.append(val)
            if self.debug:
                print("临时值: ", tmp_values)
            data = dict(zip(argx, tmp_values))
        if data:
            if isinstance(data['arg1'], list):
                if isinstance(data['arg1'][0], dict):
                    pass
                else:
                    obj = data['arg1'][0].replace(self.srvUrl, "")
                    posturl = self.srvUrl + obj + "/operations/" + execName
            else:
                obj = data['arg1'].replace(self.srvUrl, "")
                posturl = self.srvUrl + obj + "/operations/" + execName
        print("执行POST:->", posturl)
        print("数据:->", data)

        # self.response = requests.post(url=posturl, data=json.dumps(data), headers=self.urlHeadersJson)
        print('\n执行命令: ', posturl, data)
        # if execName == "start":
        #     pass
        try:
            self.response = requests.post(url=posturl, data=json.dumps(data), headers=self.urlHeadersJson)
            if execName == "apply":
                posturl = self.response.json()['url']
        except Exception as e:
            raise Exception('发生错误: ', e)
        if execName != "start":
            self.waitForComplete(self.response, posturl)
        self.checkError()
        return self.response.json()

    def setAttribute(self, objRef, name, value):
        if "http://" not in objRef:
            objRef = f"{self.srvUrl}{objRef}"
        name = name.lstrip("-")
        if self.debug:
            print("设置属性数据", {name: value})
        try:
            self.response = requests.patch(url=objRef, data=json.dumps({name: value}), headers=self.urlHeadersJson)
        except Exception as e:
            raise Exception('发生错误：', e)
        self.checkError()

    def getOptions(self, objRef, nodetype="attributes", editable=True):
        if "http://" not in objRef:
            objRef = f"{self.srvUrl}{objRef}"
        try:
            self.response = requests.options(url=objRef)
        except Exception as e:
            raise Exception('发生错误：', e)
        self.checkError()
        childrenList = self.response.json()['custom']['children']
        attributes = self.response.json()['custom']['attributes']
        operationsList = self.response.json()['custom']['operations']
        attributesList = []
        for attr in attributes:
            if attr['type']['name'] == "href":
                attributesList.append(attr)
            elif not attr['readOnly']:
                attributesList.append(attr)
            if editable:
                attributesList.append(attr)

        operationsDict = {}
        for attr in operationsList:
            operationsDict[attr['operation']] = attr['href']
        if nodetype == "children":
            returnvalues = childrenList
        elif nodetype == "operations":
            returnvalues = operationsDict
        else:
            returnvalues = attributesList
        return returnvalues

    def setMultiAttribute(self, objRef, *args):
        if self.srvUrl not in objRef:
            objRef = self.srvUrl + objRef
        names = [name.lstrip("-") for name in args[0::2]]
        values = args[1::2]
        data = dict(list(zip(names, values)))
        if self.debug:
            print("设置多个属性:url", objRef)
            pprint.pprint(data)
        try:
            self.response = requests.patch(url=objRef, data=json.dumps(data), headers=self.urlHeadersJson)
        except Exception as e:
            raise Exception('发生错误：', e)
        self.checkError()

    def getAttribute(self, objRef, name):
        if "http://" not in objRef:
            objRef = self.srvUrl + objRef
        name = name.lstrip("-")
        #print(objRef, name)
        #print(name + "*******")
        try:
            self.response = requests.get(objRef)
        except Exception as e:
            raise Exception('发生错误：', e)
        self.checkError()
        if name == "all":
            return self.response.json()
        else:
            #print(self.response.json()[name])
            return self.response.json()[name]

    def getIxNetSessionUrl(self, sessionId=None):
        if sessionId:
            return
        else:
            return "%s/sessions/%s/ixnetwork" % (self.baseUrl, str(self.sessionId))

    def readFrom(self, filename, *args):
        # 以二进制形式读取配置文件
        self.ixncfgname = filename
        with open(filename, mode='rb') as file:
            configContent = file.read()
        return configContent

    def _assignPorts(self, *args):
        realPorts = args[0]
        vports = args[2]
        from copy import deepcopy
        data = {"arg1": [], "arg2": [], "arg3": [], "arg4": True}
        try:
            [data["arg1"].append({"arg1": chassis, "arg2": str(card), "arg3": str(port)}) for chassis, card, port in
             realPorts]
        except Exception as e:
            raise Exception(str(e))
        data["arg3"] = vports
        return data

    #@staticmethod
    def ixNetExec(self, objUrl, execName, payload=None):
        try:
            stateURL_ = objUrl + "/operations/" + execName
            _stateURL = stateURL_.replace('//', '/')
            urlString = _stateURL.replace('http:/', 'http://')
            urlHeadersJson = {'content-type': 'application/json'}
            if payload is None:
                print("POST: " + urlString)
                response = requests.post(url=urlString, headers=urlHeadersJson)
            else:
                print("POST: " + urlString + "  <-- Payload: " + str(payload))
                response = requests.post(url=urlString, headers=urlHeadersJson, data=json.dumps(payload))
            a = response.json()
            if a["id"] != "":
                self.waitForComplete(objUrl, response)
            else:
                return response
        except Exception as e:
            raise Exception('发生错误：', e)
        if not response.ok:
            raise TestFailedError(response.text)
        return response

class TestFailedError(Exception):
    pass

