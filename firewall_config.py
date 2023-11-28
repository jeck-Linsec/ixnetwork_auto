# -----------------------------------------------------------------------------#
# Script Name: firewall_config.py
# Description: This script configures a firewall device through Telnet.
#
# Usage example:
#   1. Set the device configuration to an empty configuration.
#   2. Save the configuration.
#
# Requirements:
#   - Telnetlib library must be installed (use 'pip install telnetlib' if needed).
#   - Telnet access to the firewall device.
#
# Author: liuyupeng
# Date: November 2, 2023
# -----------------------------------------------------------------------------#

import telnetlib
import time
import logging


def configure_firew(host, port, commands, timeout=3, log_name='output.log'):
    # 配置日志记录
    logging.basicConfig(filename=log_name, level=logging.INFO,
                        format='%(asctime)s - %(levelname)s: %(message)s')
    print(f'\n** ** ** ** ** ** 命令配置 ** ** ** ** ** **')
    logging.info(f'** ** ** ** ** ** 命令配置 ** ** ** ** ** **')
    try:
        # 创建Telnet连接
        tn = telnetlib.Telnet(host, port, timeout)

        # 读取登录提示符
        tn.read_until(b"#", timeout)

        # 逐个执行命令
        for command in commands:
            try:
                # 发送命令
                tn.write(command.encode('utf-8') + b"\n")

                # 读取命令输出
                output = tn.read_until(b"#", timeout).decode('utf-8', 'ignore')
                logging.info(output)
                print(output)
            except Exception as inner_e:
                logging.error(f"Error executing command: {inner_e}")
                print(f"Error executing command: {inner_e}")

        # 关闭 Telnet 连接
        tn.close()
        time.sleep(0.5)

    except Exception as e:
        logging.error(f"Error: {e}")
        print(f"Error: {e}")
    print(f'** ** ** ** ** **  END  ** ** ** ** ** ** **\n')
    logging.info(f'** ** ** ** ** **  END  ** ** ** ** ** ** **\n')

def create_bridge_config(interfaces):
    config = ["u c", "zxas6cld", "return", "config"]
    for i, interface in enumerate(interfaces, start=1):
        if i % 2 == 1:
            bridge_name = f"Bridge {i // 2 + 1}"
            config.append(f"interface {bridge_name}")
        config.append(f"bind interface {interface}")
        if i % 2 == 0: config.append("return")
    config.append("save config")
    return config

def create_gateway_config(interfaces):
    config = ["u c", "zxas6cld", "return", "config"]
    i = 1
    for interface in interfaces:
        config.append(f"interface {interface}")
        config.append(f"ip add 100.{i}.0.1 24")
        config.append("return")
        i += 1
    config.append("save config")
    return config

def undo_bridge_config(interfaces):
    config = ["u c", "zxas6cld","return", "config"]
    for i, interface in enumerate(interfaces, start=1):
        if i % 2 == 1:
            bridge_name = f"Bridge {i // 2 + 1}"
            config.append(f"undo interface {bridge_name}")
    config.append("save config")
    return config

def undo_gateway_config(interfaces):
    config = ["return", "config"]
    i = 1
    for interface in interfaces:
        config.append(f"interface {interface}")
        config.append(f"undo ip add 100.{i}.0.1 24")
        config.append("return")
        i += 1
    config.append("save config")
    return config

def ipsec_config(key):
    config = ["u c", "zxas6cld","return", "config"]
    config.append(f"ipsec tunnel 1")
    config.append(f"active off")
    config.append(f"ipsec negotiation-policy 1")
    config.append(f"ike-encrypt {key}")
    config.append(f"protocol-nested 1 esp ipsec-encrypt {key} ipsec-authenticate hmac_md5 encap-type tunnel")
    config.append("return")
    config.append(f"ipsec tunnel 1")
    config.append(f"active online")
    config.append("return")
    config.append("save config")
    return config