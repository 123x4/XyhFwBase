# Windows 安装 Python 并运行 Lina H6 日志脚本

在**通过 USB 接 Lina 板的 Windows 电脑**上安装 Python。工程可以继续放在远程服务器。把 Windows 测试包下载到本机并解压，就可以在本机读取 H6 日志。 [Windows 测试包](Lina-H6-校频诊断-Windows.zip) · [日志脚本](../tools/h6_usb_log.py)

## 1. 让 PowerShell 能找到 Python

如果 `py` 报 `CommandNotFoundException`，先在本机 PowerShell 单独运行 `python --version`。若已显示 `Python 3.13.x` 或 `Python 3.14.x`，可以直接进入下一节。

如果找不到 `python`，或命令打开了 Microsoft Store，新装可选版本列表的 **3.14**。3.13 已进入安全维护阶段，后续发布主要提供源码。对于 Intel／AMD 64 位电脑，下载 Python 3.14.10 的 **Windows installer (64-bit)**。打开安装程序，勾选底部的 **Add python.exe to PATH**，上面一项 **Use admin privileges when installing py.exe** 保持未勾选，再点 **Install Now**。界面中的退役提示指将来的安装包发放方式，当前这个安装程序可以继续使用。 [Python 3.14.10 官方 EXE](https://www.python.org/ftp/python/3.14.10/python-3.14.10-amd64.exe) · [官网发布页](https://www.python.org/downloads/release/python-31410/#files) · [3.13 发布说明](https://www.python.org/downloads/release/python-31318/)

看到 **Setup was successful**，直接点 **Close**。按测试包的常规目录运行 H6 日志脚本，无需点 **Disable path length limit**。关闭原 PowerShell，重新在本机打开 PowerShell 并运行下面一行。按上述步骤新装时，应显示 `Python 3.14.10`。

```powershell
python --version
```

## 2. 安装 USB HID 依赖

在同一个 PowerShell 运行下面两行。第一行安装 `hidapi`，第二行验证脚本能导入它提供的 `hid` 模块。看到 `HID OK` 就可以继续。 `hidapi` 提供 Python 3.14 的 Windows x64 预编译包。 [hidapi 发布文件](https://pypi.org/project/hidapi/#files)

```powershell
python -m pip install hidapi
python -c "import hid; print('HID OK')"
```

新电脑的截图已确认 `Python 3.14.10`、`hidapi 0.15.0` 和 `HID OK`。终端中的 pip 版本提示可跳过，下一步是在解压目录里运行脚本并验证板子连接。

## 3. 在 Windows 上运行脚本

在资源管理器打开解压后的 `EM_HapticMouse` 文件夹，确认能看到 `tools` 目录。在地址栏输入 `powershell` 并回车，这样终端会直接打开在工程目录。

```powershell
python .\tools\h6_usb_log.py --once
```

看到 `Waiting for Lina USB HID 1A81:2071` 后，插上烧录了 H6 诊断固件的板子。脚本连接后打印日志，收到第一条 `H6_CAL` 就退出。持续看日志时去掉 `--once`，按 `Ctrl+C` 停止。 [脚本入口](../tools/h6_usb_log.py#L31)

| 现象 | 怎么处理 |
| --- | --- |
| `py` 找不到，但 `python --version` 有输出 | 后续用 `python` 即可。 |
| 安装后 `python` 仍找不到 | 重开 PowerShell。若仍失败，重新打开安装程序，选择 **Modify**，将 Python 加入 PATH。 |
| `No module named 'hid'` | 重新运行 `python -m pip install hidapi`，确保安装和运行脚本使用同一个 Python。 |
| `can't open file` | 核对当前文件夹里是否有 `tools\h6_usb_log.py`，并确认已解压 ZIP。 |
| 一直停在 `Waiting for Lina USB HID 1A81:2071` | Python 和依赖已经运行到设备查找。确认 USB 数据线接在这台 Windows 电脑上，板子已运行 H6 诊断固件。 |
