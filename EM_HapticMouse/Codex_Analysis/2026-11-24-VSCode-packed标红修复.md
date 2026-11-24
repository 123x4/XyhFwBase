# VS Code 的 ARMCC __packed 标红

`inc/device.h` 中的 `__packed` 是 ARMCC 5 的关键字，远程 VS Code 当前使用 `linux-gcc-x64` 解析配置。已在 [C/C++ 工作区配置](../.vscode/c_cpp_properties.json) 中加入 IntelliSense 专用定义 `__packed=`，让编辑器按普通结构体语法解析该声明。编辑器解析不模拟 ARMCC 的打包布局，Keil 编译仍使用源码里的原生关键字。

已验证配置 JSON 和标红声明加上该定义后的语法。未直接查看远程 VS Code 的刷新结果。若红线仍显示，执行 **Developer: Reload Window** 重新加载配置。
