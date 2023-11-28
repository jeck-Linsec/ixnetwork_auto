### IXNetWork Test

## 安装📥
```shell
pip install -r requirements.txt -i https://pypi.tuna.tsinghua.edu.cn/simple
```

> **Warning**
>
> python版本=3.8


## 运行示例▶️
使用 pip 安装好 之后，可以尝试运行测试程序：
```python
python ixnetwork_test.py
```
可以使用 result_to_excel 一次性将结果导入到测试模板excl中
```python
python result_to_excel.py
```

## 使用需知📕
```shell
1.硬件限制，目前ixnetwork测试仪一次性最多可接6SFP+ 8GE,
2.需提前定义好ixncfg配置文件，例如2GE,8GE,4SFP+等，理论上首次配置无误后无需再变化，如需变化，优先变化防火墙配置,
3.ipsec配置因为需要两台设备并接线等，所以暂定是直接定义好IPSEC(并测试两台设备可以连接后，以保证有效)进行测试，
都配置好后，在IPSEC四种加密算法测试中无需手动干预，
4.使用前按照性能测试要求中，全部使用kong.cfg，并格式化进行。
```

## 演示视频📽️
参见目录下MP4演示视频 🎉

