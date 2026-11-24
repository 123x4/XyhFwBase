# Windows 上用 Keil 重建 Lina 应用

从 Windows 上准备要测的完整工程副本，确认 `Sample.uvproj` 和源文件来自同一工作版本。如果要与当前工作区逐文件一致，注意当前 `app/button.c` 有未提交改动，仅拉取提交会漏掉它。

1. 在 Keil µVision 打开 `Sample.uvproj`，选中 `Target 1`。
2. 打开 **Project → Options for Target 'Target 1' → Target**，核对 **ARM Compiler** 为 **V5.06 update 7 (build 960)**。
3. 选择 **Project → Rebuild all target files**。看 Build Output 的编译器版本和最后的 Error(s)/Warning(s) 摘要。成功后，确认 `output/Sample.hex` 与 `output/Sample.axf` 的修改时间是这次重建的时间。
4. 回传 Build Output 第一段的编译器版本、末尾的摘要，以及出现错误时的第一条完整报错。完整日志可优先用下方命令生成。当前这一步做编译验证，完成后再根据测试目的选烧录文件。

[Keil 重建说明](https://www.keil.com/support/man/docs/uv4cl/uv4cl_ca_buildproject.htm)

## PowerShell 命令行方式

在 `Sample.uvproj` 所在目录执行。若 Keil 装在其他位置，调整第一行路径。

```powershell
$keil = 'C:\Keil_v5\UV4\UV4.exe'
$build = Start-Process -FilePath $keil -ArgumentList '-r ".\Sample.uvproj" -t"Target 1" -o"build-armcc5.log"' -Wait -PassThru
$build.ExitCode
Get-Content .\build-armcc5.log -Tail 30
```

Keil 退出码 0 表示无错误和警告，1 表示只有警告，2 或 3 表示构建发生错误。 [Keil 命令行和退出码](https://www.keil.com/support/man/docs/uv4/uv4_commandline.asp)
