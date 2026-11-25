# EM_HapticMouse 项目交接说明（给新加入的 AI）

最后更新：2026-11-25 14:20（Asia/Taipei）。当前 HEAD `3f3622d`，`main` 分支，本地提交、未推送。

## 1. 一句话目标

把 Lina T1A 鼠标（LPC11U35）的霍尔芯片从 **GTRY154（H5）** 迁移到 **GTRY164（H6）**，同时保留 H5 和其他 11 种存量板型固件不变；迁移分阶段：校频 → 寄存器读写 → 采样 → 上层按键/RT/触觉联调。

## 2. 硬件

- MCU：LPC11U35FHI33/501，系统 48 MHz，Cortex-M0。
- 霍尔：两颗 GTRY164 串联，H1 标注 `LB`（左）、H2 标注 `RB`（右），链路 **MCU → H1 → H2 → MISO**，共用时钟。
  - SCLK_0 → PIO1_15（SCK1），MOSI_0 → PIO0_21，MISO_0 → PIO0_22。
  - 供电使能 `Hall PWR EN` → PIO0_16，高电平经 Q5 + MOS1 打开 `HALL_VDD`（TP8 ≈3.3 V，TP11 为使能测试点）。
  - 上电时序：GPIO 初始化先拉低 50 ms，再拉高，之后 `TimerDelayMsec(500)` 才进霍尔初始化。
- 触觉：`HP_EN` → PIO1_19，`PWM1` → PIO0_13，`PWM2` → PIO0_14（阻塞式脉冲，`CT16B1_DelayUs` 定时）。
- 按键：前/后 PIO0_11 / PIO0_12，中键 PIO0_7，DPI PIO0_23。
- 光学传感器 PAW3950 走 SSP0（与霍尔 SSP1 无关）。
- 应用区：`0x4000` 起、大小 `0xC000`；`0x0000–0x3FFF` 是 MG380U Bootloader。`0x3F00` 有 `AA AA` 应用标记；应用请求升级时向 RAM `0x10001F00` 写 `0xAA` 后软复位。USB：应用 `1A81:2071`，Bootloader `17EF:6155`。

## 3. 代码地图

- 启动：`src/Main.c` → `Device_Init()`（`src/device.c#L273`）→ `Device_Active()` 主循环。
- 1 kHz 节拍：CT16B0 中断递减 `one_ms_cycle`，`Device_Scan()` 每次节拍执行一次按键/霍尔。
- 霍尔数据链：`Button_Scan → Button_GetState → LR_GetState → hall_get_sample()`（一次 GPIO 命令脉冲 + 4 字节 SSP1）→ `ProcessRecvSampleRawData()`。
  - **注意**：实现在 `src/my_misc.c#L418`；`src/my_hallkey_func.c` 里有同名函数但**不在 Keil 工程里**，加进去会重复定义。
- 采样处理：`bit_error[]` 查 CRC → `16383 - raw` 反转（Lina 的按下方向）→ 一阶滤波 → `Hall_CalculateNode`（top/bottom baseline → 0–100 分段）→ `Hall_HandleKeyRapidTrigger`（AP + RT 行程）→ `Ele_UpadteSegment`。
  - `gbKeyState[]` 回到 `Button_Scan` 的边沿检测，触发 `Ele_LeftKeyPressProcess()` 等阻塞式触觉脉冲。
  - 数组约定：`rx[0..1]` = 右键 H2，`rx[2..3]` = 左键 H1，低 8 位有效。
- 板型选择：`inc/my_board.h`，当前只启用 `GT_LINA_T1A_H6_PWM`（内部别名回 `GT_LINA_T1A_H5_PWM` → `GT_LINA_T1A_H5`，复用 Lina 的引脚/SSP1/触觉宏）。
- H6 诊断入口：`app/button.c` 的 `Hall_H6_Diagnostic()`，由 `HallSensor_INIT()` 直接进入且不返回；只跑校频 + 寄存器诊断 + USB 日志，`Device_Init()` 后半段（PAW3950、Profile、Custom、LED、BOD）**不会执行**，`PC_Communicate()` 被裁剪成只处理升级命令。
- 日志：`InfoLog` → `printf` → USB EP3（`my_debug.h`，H6 版型自动打开）；`tools/h6_usb_log.py` 收 HID 日志（`py -m pip install hidapi`）。

## 4. 当前进度

| 阶段 | 状态 |
| --- | --- |
| 校频 td10 | **完成并定版**：31 拍 NOP 尾、`126U/60U`、实测均值 127.9992 µs（15/16 条正好 128.0000），`H6_CAL PASS n=16` |
| 寄存器读 0x35 | **尚未指派**。工作区有一份未提交的实现（14:11 写入、未构建上板、未经确认） |
| 寄存器写 / 链序确认 | 未开始 |
| H6 配置表 + 采样 | 未开始 |
| 上层 baseline/RT/触觉联调 | 未开始 |

## 5. 时序基准与"传入值"映射

H6（GTRY164 V1.9 §7.8，第 12 页）：td1 5±5%、td2 连续 >4 / 单次 >24、td6 39±5%、td5 >3、td4（PWM）18±5%、td10 128±5%、td12 >50、td7 28±5%（睡眠）、td8 2±5%（唤醒）、td9 >50、td11 >1280。

当前 H6 脉冲实现（`app/button.c`）：复用 H5 的 `Hall_CLK_Command_SET()`，高电平 = `CT16B1_DelayUs(high)` + **31 条字面 NOP**（每拍 20.83 ns，共 646 ns），高电平期间用 **PRIMASK 临界区**屏蔽中断；低电平仍用 `CT16B1_DelayUs(low)`。

实测映射（同一个 build 内极差仅 0.0125 µs）：

```
高电平 ≈ 传入值 + 2.0 µs      （126 → 127.999）
低等待 ≈ 传入值 + 2.8 µs      （60  → 62.8）
```

因此各命令的 `high` 参数：

| 用途 | 目标 | 传值 |
| --- | ---: | ---: |
| 校频 td10 | 128.00 | **126** |
| 读写寄存器 td6 | 39.00 | **37** |
| 采样 td1 | 5.00 | **3**（待实测确认） |

低等待 `low` 只要满足最小值，传 4–60 即可（td5 传 4 → 约 6.8 µs）。

## 6. H6 帧格式与寄存器

- **读寄存器**（图 7）：先移 32 clocks（两颗各 16 位），帧 = `bit15=0`、`bits13:8=addr(6 位)`、`bits7:0` 任意；再发长脉冲；再移 32 clocks 读回，**低 8 位有效**。
  - 按当前代码：`tx = {0x35, 0x00, 0x35, 0x00}`；回读 `rx[1]`（右）、`rx[3]`（左）。
- **写寄存器**：帧 = `bit15=1`、`bit14=CRC_WR`、`bits13:8=addr`、`bits7:0=data`；`CRC_WR = A5^A4^A3^A2^A1^A0^D7^…^D0`，**必须含地址位**。
  - 现有 `bit_crc_write_reg[256]` 只异或数据位（H5 规则），直接拿来写 H6 会被判无效帧。
- **采样**：16 位，高 2 位 CRC1/CRC0 + 14 位数据，CRC 定义与 H5 相同，`bit_error[]` 可继续用；`0xC000`/`0x3FFF` 是异常返回。
- **校频判据**：两颗回读低字节都在 `0x7C–0x84`（含边界）；失败最多重试 128 次；通过后等 20 ms。
- 关键寄存器（H6 与 H5 地址含义完全不同，**不能照抄 H5 的 25 项初始化表**）：`0x0B` 增益、`0x0C=0x83`、`0x0F/0x10` 采样间隔（0x1F/0x20 → 124 µs，对齐 H5）、`0x1B` SCK 空闲、`0x26/0x27/0x28` 固定值、`0x29/0x2A` 随 LNA 联动、`0x2B/0x2C` 阈值、`0x2D/0x2E` 初始 baseline、`0x2F=0x14`、`0x30/0x31` baseline 偏差、`0x32` 极性/按键类型、`0x33=0x84`（连续 + baseline）、`0x35` SDO 驱动（默认 **0x27**）、`0x3C` 实时 baseline。
- XENO 参考工程还用了手册未公开的 `0x13/0x15/0x16/0x18/0x1C/0x1E/0x20/0x25`，以及偏移校准的 `0x36/0x37/0x3B`；`0x29` 16× 手册写 0x50、XENO 用 0x4E。

## 7. 已经踩过的坑（别重复）

1. **计数式脉冲的轮询量化**：用 CT16B1 计数 + 轮询 TC，退出延迟被量化到约 0.2 µs，trim 改 33 拍实测位移 43 拍，128 附近只能落在 127.79/128.03 这类格点。已放弃。
2. **MR0 + IR 中断标志**：到期由硬件判定，但检测仍靠轮询，量化不消失，还要处理 `TIMER_16_1_IRQn` 的 NVIC 使能状态。已放弃。
3. **NOP 尾必须字面展开**：改成 `for` 循环每轮多 3–4 拍，标定会失效。
4. **只关 USB 中断不够**：H5 路径原本只 `NVIC_DisableIRQ(USB_IRQn)`，1 ms tick 会把 128 µs 拉长 ~2.3 µs（td10 尚可，td1 必挂）。现在高电平用 PRIMASK。
5. **`DELAY_OUT(x)=x-1` 是给旧 GPIO 开销的补偿**，与现在的"NOP 尾"语义不同，别混用。
6. **H5 的 TD 宏不能直接给 H6**：调用点用的是 td4/td7/td10 等旧编号，而 H6 的读写是 td6、校频是 td10+td12，宏替换会静默用错时序。
7. **H6 写寄存器 CRC 含地址**（见 §6）。
8. **链序未验证**：`rx[0..1]=右` 只有移位分析支撑；两颗同值回读（如 0x35 默认 0x27）无法区分左右，要用写互异值确认。
9. **冷启动前两次校频必失败**：四次冷启动都是第 1、2 次不通过、第 3 次起通过（`minimumAttempts=16` 正好覆盖），中途偶发只见过一次。
10. **`my_hallkey_func.c` 不在工程里**，别为省事加进去。
11. **ROM 余量约 3.4 KB（45.7/48 KB）**；RAM 需用 Keil 的 `Program Size` 行确认，MSP 已因 USB 日志队列抬高 464 字节。

## 8. 构建与验证

- 编译：`Sample.uvproj` 的 `Target 1`，ARMCC **5.06 update 7 (build 960)**，C99，`<Define>` 为空，输出 `output/Sample.hex`；应用区从 `0x4000` 开始，烧录时按扇区擦除保留 Bootloader。
- 板型：`inc/my_board.h` 只启用 `GT_LINA_T1A_H6_PWM`。
- Windows 测试包：`Codex_Analysis/Lina-H6-校频诊断-Windows.zip`（含工程、源码、`tools/h6_usb_log.py`）。
- 日志：`py .\tools\h6_usb_log.py --once`（HID `1A81:2071`，usage page 0xFF01）。
- 逻辑分析仪：CH1 接 `SCLK_0`，80 MS/s，1–2 s；校频用高脉宽触发 **80–200 µs**，td6 用 **20–60 µs**；先 Start 再上电。
- 波形分析脚本：`DeepSeek_Analysis/h6_sclk_analyze.py <csv>`，输出逐条高宽/低等待/时钟数/周期与 PASS/FAIL。

## 9. 协作约定

- 每次答复都落一份带日期的 Markdown：Codex 写 `Codex_Analysis/`，DeepSeek 写 `DeepSeek_Analysis/`；改代码前先说明改哪个文件，同一文件避免两人同时写。
- 提交风格：英文、祈使句标题（如 `Use the H5 delay with a NOP tail for H6 command pulses`），正文写"改了什么 / 为什么 / 数据依据 / 还差什么验证"。代码与文档分开提交。
- 只把实际构建并上板测过的组合记为"通过"；未测的写"预期值"并注明。

## 10. 立刻要做的下一步

这一步**还没有正式指派给任何一方**。工作区里有一份未提交、未构建、未经确认的实现（`app/button.c` 在 `Hall_H6_Diagnostic()` 里校频通过后读 3 次 0x35，日志 `H6_REG35 R= L= R2= L2= R3= L3=`，`Codex_Analysis/2026-11-25-H6寄存器35读回诊断.md` 是对应笔记）。接手方可以先决定沿用、修改还是重写，再执行：

1. 在 Windows 重建 `Target 1`、烧录。
2. CH1 接 `SCLK_0`，触发改 **20–60 µs**，抓 1–2 s，先 Start 再上电。
3. 检查：三条 39 µs 命令的高宽在 **37.05–40.95**、下降沿到第一枚回读短时钟 **>3 µs**、每段 32 个短时钟；CSV + `H6_REG35` 与 `H6_CAL` 两行日志一起回传。
4. 期望 `H6_REG35 ... = 0x27`（`0x35` 上电默认值）。若是 `0x00`/`0xFF`，先抓 MOSI/MISO 判断是帧格式还是链路问题，不要先改代码。

之后：用 `0x05`（PWM0 电流，默认 0）写两个互异值再读回，确认 H1/H2 与左右的对应；再写 `0x35` 改 SDO 驱动电流并读回，验证写命令与含地址 CRC；然后进入配置表与采样。

## 11. 未决问题

- H1/H2 与左右键的对应（需写互异值验证）。
- 按下时原始值的方向（决定 `0x32` bit6/bit7）。
- 增益档位：H5 是 64× LNA，H6 没有该档，需按原始值幅度/饱和重选，`0x29/0x2A` 随之联动。
- baseline 策略：用自动填充还是固化，`0x30/0x31` 偏差取值。
- RAM 实际余量（等 Keil `Program Size`）。
- 采样阶段 td1 的最终传值与是否单独标定尾部。
