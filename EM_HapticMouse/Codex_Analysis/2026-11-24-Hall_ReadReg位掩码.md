# Hall_ReadReg 的位掩码与参数

蓝框的 `reg & (~(0x01 << 7))` 把 bit7 清零，保留 bit6 到 bit0。对 `uint8_t reg` 来说，等价于 `reg & 0x7F`。H5 手册 §7.4 图 7 规定读请求首字节是最高位为 0 的读标志，加低 7 位寄存器地址。

```text
0x01 << 7          1000 0000
取反后只看低 8 位   0111 1111
reg = 0x14         0001 0100
按位与             0001 0100  → 0x14
```

红框把同一地址装入 tx[0]（右键 H2）和 tx[2]（左键 H1）。tx[1]、tx[3] 是线上占位字节，沿用已有值。源码的两个 0x55 写在 rx 中，随后被 SPI 接收覆盖。Hall_read_register() 执行两次 SPI 及中间长脉冲。最后 rx[1] 写到 rightValue 指向的变量，rx[3] 写到 leftValue 指向的变量。

例如 `Hall_ReadReg(0x14, &leftData, &rightData)` 读取两颗芯片各自的 0x14，调用方通过 leftData、rightData 取回两个值。

[实现](../app/button.c#L918) · [实际调用](../app/button.c#L415) · [H5 手册 §7.4](../Materials/GTRY154%20Magnetic%20Keyboard%20Sensor%20and%20LED%20Driver_V1.1_20240719%20%28For%20Corsiar%29.pdf#page=9)
