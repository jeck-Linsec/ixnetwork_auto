# -----------------------------------------------------------------------------#
# Script Name: rfc2544_test.py
# Description: This script performs RFC 2544 testing using Ixnerwork test equipment.
#
# Usage example:
#   1.Import configuration.
#   2.Perform a quick test
#   3.The test is complete and the result is exported
#
# Requirements:
#   - Needs to work with IxNet.py
#
# Author: liuyupeng
# Date: November 2, 2023
# -----------------------------------------------------------------------------#

from IxNet import ixNet_run
import requests
import json
import time
import sys
import os
import re
import datetime
import yaml
import logging

class configs():
    # ixNetworkApiServer = '10.10.3.225'
    # ixNetworkPort = '8009'
    userSelectQuickTestList = 'all'
    copyResultFileToLocalLinuxPath = 'result/resulcsv/'
    quickTestCsvResultFile = 'AggregateResults.csv'
    #quickTestCsvResultFile = 'results.csv'
    #quickTestConfigFile = 'test.ixncfg'

def loadConfigFile(sessionUrl, configFile):
    """
    从Linux文件系统加载保存的配置文件。

    Args:
        sessionUrl (str): IxNetwork会话的URL，例如：http://10.219.x.x:11009/api/v1/sessions/1/ixnetwork。
        configFile (str): 包含保存的配置文件的完整路径。

    Returns:
        int: 如果成功返回0，如果失败返回1。
    """
    # 定义HTTP请求头
    urlHeadersJson = {'content-type': 'application/json'}
    urlHeadersData = {'content-type': 'application/octet-stream'}

    try:
        # 1> 读取配置文件内容
        print('\n读取保存的配置文件')
        with open(configFile, mode='rb') as file:
            configContents = file.read()

        # 提取文件名
        fileName = configFile.split('/')[-1]

        # 2> 上传文件到服务器，并为其指定任意文件名
        uploadFile = f"{sessionUrl}/files?filename={fileName}"
        print('\n上传文件到服务器:', uploadFile)
        response = requests.post(uploadFile, data=configContents, headers=urlHeadersData)

        if response.status_code != 201:
            return 1

        # 3> 设置载入配置文件的payload
        payload = {'arg1': f'/api/v1/sessions/1/ixnetwork/files/{fileName}'}

        loadConfigUrl = f"{sessionUrl}/operations/loadconfig"

        # 4> 告诉服务器载入配置文件
        print('\n载入配置文件:', loadConfigUrl)
        print('Payload', payload)
        response = requests.post(url=loadConfigUrl, data=json.dumps(payload), headers=urlHeadersJson)
        operationId = response.json()["id"]
        print(operationId)

        if response.status_code != 202:
            return 1

        # 使用IxNet的waitForComplete方法等待操作完成
        if ixNet.waitForComplete(response, f"{loadConfigUrl}/{operationId}") == 1:
            return 1
        else:
            return 0
    except Exception as e:
        print(f"加载配置文件失败：{str(e)}")
        return 1

def VerifyPortState(portList='all', expectedPortState='up'):
    """
    验证端口状态是否符合预期。

    Args:
        portList (str, optional): 要验证的端口列表，格式为 '1/2'，而不是 '1/1/2'。默认为 'all'，表示所有端口。
        expectedPortState (str, optional): 期望的端口状态，可以是 'up' 或 'down'。默认为 'up'。

    Returns:
        int: 如果成功返回0，如果失败返回1。
    """
    print('\n验证端口状态 ...', end=' ')
    allVports = ixNet.getList(ixNet.getRoot(), 'vport')

    if portList == 'all':
        vportList = allVports
    else:
        vPortList = []
        for vport in allVports:
            # 解析端口连接信息，例如: ::ixNet::OBJ-/availableHardware/chassis:"10.205.4.35"/card:1/port:1
            connectedTo = ixNet.getAttribute(vport, 'connectedTo')
            connectedTo = connectedTo.split('/')[-2:]
            card = connectedTo[0].split(':')[-1]
            port = connectedTo[1].split(':')[-1]
            port = card + '/' + port

            if port in portList:
                vPortList.append(vport)

    portsAllUpFlag = 0

    for vport in vPortList:
        for timer in range(60 + 1):
            # 获取端口状态
            portState = ixNet.getAttribute(vport, 'state')

            if expectedPortState == 'up':
                if portState != 'up' and timer != 60:
                    print('\nVerifyPortState: %s 仍然是 %s。期望端口为 up。%s/60 秒。' % (
                        vport, portState, timer))
                    time.sleep(2)
                    continue

                if portState != 'up' and timer == 60:
                    print('\n错误 VerifyPortState: %s 似乎卡在 %s 状态上。期望端口为 up。\n' % vport, portState)
                    portsAllUpFlag = 1

                if portState == 'up':
                    print('\nVerifyPortState: %s 状态为 %s' % (vport, portState))
                    break

            if expectedPortState == 'down':
                if portState != 'down' and timer != 60:
                    print('\nVerifyPortState: %s 仍然是 %s。期望端口为 down。%s/60 秒。' % (
                        vport, portState, timer))
                    time.sleep(2)
                    continue

                if portState == 'up' and timer != 60:
                    print('\n错误 VerifyPortState: %s 似乎卡在 %s 状态上。期望端口为 down' % (
                        vport, portState))
                    portsAllUpFlag = 1

                if portState == 'down':
                    print('\nVerifyPortState: %s 状态为 %s，符合预期' % (vport, portState))
                    break

    if portsAllUpFlag == 1:
        return 1
    else:
        time.sleep(3)
        return 0

def GetConfiguredQuickTests():
    """
    获取已配置的快速测试的名称列表。

    Returns:
        list: 包含已配置快速测试名称的列表。
    """
    allConfiguredQuickTestNames = []
    allConfiguredQuickTestHandles = ixNet.getAttribute(ixNet.getRoot() + '/quickTest', 'testIds')
    for qtHandle in allConfiguredQuickTestHandles:
        allConfiguredQuickTestNames.append(ixNet.getAttribute(qtHandle, 'name'))
    return allConfiguredQuickTestNames

def VerifyAllQuickTestNames(quickTestNameList):
    """
    验证所有指定的快速测试名称是否都存在于配置中。

    Args:
        quickTestNameList (list): 要验证的快速测试名称列表。

    Returns:
        int: 如果所有名称都存在则返回0，否则返回1。
    """
    noSuchQuickTestName = []
    allConfiguredQuickTestNames = []
    allConfiguredQuickTestHandles = ixNet.getAttribute(ixNet.getRoot() + '/quickTest', 'testIds')
    for qtHandle in allConfiguredQuickTestHandles:
        allConfiguredQuickTestNames.append(ixNet.getAttribute(qtHandle, 'name'))

    print('\n所有配置的快速测试名称:', allConfiguredQuickTestNames, end=' ')

    for userDefinedQuickTestName in quickTestNameList:
        if userDefinedQuickTestName not in allConfiguredQuickTestNames:
            noSuchQuickTestName.append(userDefinedQuickTestName)

    if noSuchQuickTestName:
        for noSuchTestName in noSuchQuickTestName:
            print('\n错误: 不存在的快速测试名称:', noSuchTestName)
        return 1
    else:
        print(0)
        return 0

def GetAllQuickTestHandles():
    """
    获取所有快速测试的句柄列表。

    Returns:
        list: 包含所有快速测试句柄的列表。
    """
    return ixNet.getAttribute(ixNet.getRoot() + '/quickTest', 'testIds')

def ApplyQuickTestHandle(quickTestHandle):
    """
    应用指定的快速测试句柄。

    Args:
        quickTestHandle: 要应用的快速测试句柄。

    Returns:
        None
    """
    print('\n应用快速测试句柄:', quickTestHandle)
    ixNet.execute('apply', quickTestHandle)

def VerifyQuickTestApply(quickTestHandle):
    """
    验证快速测试的应用状态。

    Args:
        quickTestHandle: 要验证的快速测试句柄。

    Returns:
        int: 如果验证成功则返回0，否则返回1。
    """
    currentAction = GetQuickTestCurrentAction(quickTestHandle).strip(' ')
    print('\nVerifyQuickTestApply currentAction:', currentAction)
    if currentAction == 'TestEnded' or currentAction == 'None':
        for timer in range(1, 20+1):  # 只等待1秒，根据需要调整
            currentAction = GetQuickTestCurrentAction(quickTestHandle).strip(' ')
            if currentAction == 'TestEnded' or currentAction == 'None':
                print('\n当前状态 = %s : 等待 %s/20 秒以更改状态' % (currentAction, timer))
                time.sleep(1)
                continue
            else:
                break

    ixNetworkVersion = ixNet.getAttribute(ixNet.getRoot() + '/globals', 'buildNumber')
    ixNetworkVersionNumber = re.match('^[^ ]+ *([0-9]+)\.[^ ]+ *', ixNetworkVersion)
    if ixNetworkVersionNumber:
        version_string = ixNetworkVersionNumber.group(1)  # 获取匹配的数字文本
        ixNetworkVersionNumber = int(version_string)  # 将文本转换为整数
    else:
        ixNetworkVersionNumber = 0  # 如果无法匹配版本号，可以设置默认值为0或者其他合适的值

    print(ixNetworkVersionNumber)

    applyQuickTestCounter = 60  # 设置等待次数，根据需要调整
    for counter in range(1, applyQuickTestCounter + 1):
        #quickTestApplyStates = ['InitializingTest', 'ApplyFlowGroups', 'SetupStatisticsCollection']
        currentAction = GetQuickTestCurrentAction(quickTestHandle).strip(' ')
        if currentAction == None:
            currentAction = 'ApplyingAndInitializing'

        print('\nVerifyQuickTestApply: %s : 等待 %s/%s 秒' % (currentAction, counter, applyQuickTestCounter))
        if int(ixNetworkVersionNumber) >= 8:
            if counter < applyQuickTestCounter and currentAction != 'TransmittingFrames':
                time.sleep(1)
                continue

        if int(ixNetworkVersionNumber) < 8:
            if counter < applyQuickTestCounter and currentAction == 'ApplyingAndInitializing':
                time.sleep(1)
                continue

        if int(ixNetworkVersionNumber) >= 8:
            if counter < applyQuickTestCounter and currentAction == 'TransmittingFrames':
                print('\nVerifyQuickTestApply 已完成配置并开始传输帧')
                break
            break

        if int(ixNetworkVersionNumber) < 8:
            if counter < applyQuickTestCounter and currentAction == 'ApplyingAndInitializing':
                print('\nVerifyQuickTestApply 已完成配置并开始传输帧')
                break
            break

        if counter == applyQuickTestCounter:
            if int(ixNetworkVersionNumber) >= 8 and currentAction != 'TransmittingFrames':
                print('\nVerifyQuickTestApply 在 %s 上卡住了。等待 %s/%s 秒' % (
                    currentAction, counter, applyQuickTestCounter))
                return 1
            if int(ixNetworkVersion) < 8 and currentAction != 'Trial':
                print('\nVerifyQuickTestApply 在 %s 上卡住了。等待 %s/%s 秒' % (
                    currentAction, counter, applyQuickTestCounter))
                return 1

    return 0

def StartQuickTest(quickTestHandle):
    """
    启动指定的快速测试。

    Args:
        quickTestHandle: 要启动的快速测试句柄。

    Returns:
        None
    """
    print('\n启动快速测试\n')
    ixNet.execute('start', quickTestHandle)

def GetQuickTestHandleByName(quickTestName):
    """
    根据名称获取快速测试的句柄。

    Args:
        quickTestName: 要查找的快速测试名称。

    Returns:
        int: 如果找到匹配的句柄则返回句柄，否则返回0。
    """
    for quickTestHandle in GetAllQuickTestHandles():
        currentQtName = ixNet.getAttribute(quickTestHandle, 'name')
        if (bool(re.match(quickTestName, currentQtName, re.I))):
            return quickTestHandle

    return 0

def GetQuickTestDuration(quickTestHandle):
    """
    获取快速测试的持续时间。

    Args:
        quickTestHandle: 要查询的快速测试句柄。

    Returns:
        int: 快速测试的持续时间（以秒为单位）。
    """
    return ixNet.getAttribute(quickTestHandle + '/testConfig', 'duration')

def GetQuickTestTotalFrameSizesToTest(quickTestHandle):
    """
    获取快速测试要测试的总帧大小数。

    Args:
        quickTestHandle: 要查询的快速测试句柄。

    Returns:
        int: 要测试的帧大小数。
    """
    return ixNet.getAttribute(quickTestHandle + '/testConfig', 'framesizeList')

def GetQuickTestCurrentAction(quickTestHandle):
    """
    获取当前快速测试的执行状态。

    Args:
        quickTestHandle: 要查询的快速测试句柄。

    Returns:
        str: 当前执行状态。
    """
    ixNetworkVersion = ixNet.getAttribute(ixNet.getRoot() + '/globals', 'buildNumber')

    match = re.match('^[^ ]+ *([0-9]+)\.[^ ]+ *', ixNetworkVersion)
    if int(match.group(1)) >= 8:
        return ixNet.getAttribute(quickTestHandle + '/results', 'currentAction')
    else:
        return ixNet.getAttribute(quickTestHandle + '/results', 'progress')


def CopyFileWindowsToLocalLinux(ixNetworkApiServer, ixNetworkPort, currentQtTestName, windowsPath, localPath):
    fileName = os.path.basename(windowsPath.replace('\\', '/'))  # 提取文件名并替换目录分隔符
    print(fileName)
    localDir = os.path.dirname(localPath)
    print(currentQtTestName)

    # 确保本地目录存在，如果不存在则创建
    if not os.path.exists(localDir):
        os.makedirs(localDir)

    destinationPath = '/api/v1/sessions/1/ixnetwork/files/' + fileName
    currentTimestamp = datetime.datetime.now().strftime('%Y-%m-%d_%H-%M-%S')

    requests.post('http://%s:%s/api/v1/sessions/1/ixnetwork/operations/copyfile' % (
        ixNetworkApiServer, ixNetworkPort),
                  data=json.dumps({"arg1": windowsPath, "arg2": destinationPath}),
                  headers={'content-type': 'application/json'})
    url = 'http://%s:%s/api/v1/sessions/1/ixnetwork/files/%s' % (ixNetworkApiServer, ixNetworkPort, fileName)
    print(url)
    requestStatus = requests.get('http://%s:%s/api/v1/sessions/1/ixnetwork/files/%s' % (ixNetworkApiServer, ixNetworkPort, fileName),
                                 stream=True)
    if requestStatus.status_code == 200:
        contents = requestStatus.raw.read()
        localPath = os.path.join(localDir,currentTimestamp + '_' + fileName)
        localPath = localPath.replace("\\", "/")
        print(localPath)
        print(f"windows文件路径:{windowsPath}, 保存到本地: {localPath}")
        logging.info(f"windows文件路径:{windowsPath}, 保存到本地: {localPath}")
        with open(localPath, 'wb') as downloadedFileContents:
            downloadedFileContents.write(contents)
        return windowsPath, localPath
    else:
        print('\nError: Failed to get %s from %s' % (fileName, configs.ixNetworkApiServer))


def MonitorQuickTestRunProgress(quickTestHandle):
    counter = 1
    while True:
        isRunning = ixNet.getAttribute(quickTestHandle + '/results', 'isRunning')

        if isRunning == True:
            currentRunningProgress = ixNet.getAttribute(quickTestHandle + '/results', 'progress')
            print('\n%s 秒: %s' % (counter, currentRunningProgress))
            logging.info(f'{counter} 秒: {currentRunningProgress}')
            counter += 1
            time.sleep(10)
            continue
        else:
            break

    time.sleep(2)

# 读取配置文件
with open('config.yaml', 'r', encoding='utf-8') as file:
    config = yaml.safe_load(file)

ixNetworkApiServer = config['ixNetworkApiServer']
ixNetworkPort = config['ixNetworkPort']
#quickTestConfigFile = config['quickTestConfigFile']

# 创建 ixNet 实例并连接到服务器
ixNet = ixNet_run(ixNetworkApiServer, ixNetworkPort)
ixNet.connect()

def Rfc2544_run(ixNetworkApiServer, ixNetworkPort, quickTestConfigFile, log_name='output.log'):

    logging.basicConfig(filename=log_name, level=logging.INFO,
                        format='%(asctime)s - %(levelname)s: %(message)s')
    print(f'\n** ** ** ** ** ** 开始测试 ** ** ** ** ** **')
    logging.info(f'** ** ** ** ** ** 开始测试 ** ** ** ** ** **')
    print(f'测试配置：{quickTestConfigFile}')
    logging.info(f'测试配置：{quickTestConfigFile}')

    # 检查配置文件是否存在
    if not os.path.exists(quickTestConfigFile):
        sys.exit('\nNo such config file: {0}'.format(quickTestConfigFile))
        logging.info('\nNo such config file: {0}'.format(quickTestConfigFile))

    # 加载配置文件
    if loadConfigFile(ixNet.getIxNetSessionUrl(), quickTestConfigFile) == 1:
        sys.exit()

    # 获取用户选择的快速测试列表
    #print(configs.userSelectQuickTestList, "**************")
    if configs.userSelectQuickTestList == 'all':
        configuredQuickTestList = GetConfiguredQuickTests()
        if configuredQuickTestList:
            quickTestNameList = configuredQuickTestList
            print(quickTestNameList)
            logging.info(f'quickTestNameList:{quickTestNameList}')
        else:
            sys.exit('\nError: No Quick Test configured found')
    else:
        if VerifyAllQuickTestNames(configs.userSelectQuickTestList) == 0:
            sys.exit()
        quickTestNameList = configs.userSelectQuickTestList
        #print(quickTestNameList)

    print('\nList of Quick Test to run ...')
    logging.info('List of Quick Test to run ...')
    for quickTestToRun in quickTestNameList:
        print('\t', quickTestToRun)
        logging.info(f'quickTestToRun:{quickTestToRun}')

    time.sleep(60)
    # 遍历运行快速测试
    for quickTestName in quickTestNameList:
        quickTestHandle = GetQuickTestHandleByName(quickTestName)
        currentQuickTestName = ixNet.getAttribute(quickTestHandle, 'name')
        print('\nStarting QuickTest name:', currentQuickTestName)
        logging.info(f'Starting QuickTest name:{currentQuickTestName}')

        # 获取测试持续时间和总帧大小
        testDuration = GetQuickTestDuration(quickTestHandle)
        totalFrameSizesToTest = GetQuickTestTotalFrameSizesToTest(quickTestHandle)
        logging.info(f'duration:{testDuration}')
        logging.info(f'totalFrameSizesToTest:{totalFrameSizesToTest}')

        ApplyQuickTestHandle(quickTestHandle)

        # 必须等待 8 秒以确保应用程序同步
        print('\nWait 8 seconds for Quick Test to apply to hardware ...')
        time.sleep(8)

        #启动快速测试
        if StartQuickTest(quickTestHandle) == 1:
            sys.exit()

        # 验证应用状态
        if VerifyQuickTestApply(quickTestHandle) == 1:
            sys.exit()

        # 监控快速测试运行进度
        MonitorQuickTestRunProgress(quickTestHandle)
        time.sleep(120)

        # 获取结果文件路径并复制到本地 Linux
        resultPath = ixNet.getAttribute(quickTestHandle + '/results', 'resultPath')
        resultPath = resultPath + '\\' + configs.quickTestCsvResultFile
        #print(resultPath)

        #print(configs.copyResultFileToLocalLinuxPath)
        logging.info(f'copyResultFileToLocalLinuxPath:{configs.copyResultFileToLocalLinuxPath}')

        windowsPath, localPath = CopyFileWindowsToLocalLinux(ixNetworkApiServer, ixNetworkPort, currentQuickTestName, resultPath, configs.copyResultFileToLocalLinuxPath)
        return windowsPath, localPath

        print(f'** ** ** ** ** ** 结束测试 ** ** ** ** ** **\n')
        logging.info(f'** ** ** ** ** ** 结束测试 ** ** ** ** ** **\n')

