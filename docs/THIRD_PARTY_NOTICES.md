# 第三方来源说明

## OpenCV 标定板工具

board/generate_pattern.py 与 board/test_charuco_board.py 来自 OpenCV 的 apps/pattern-tools 工具及测试代码，来源：

- https://github.com/opencv/opencv/tree/4.x/apps/pattern-tools
- https://github.com/opencv/opencv/blob/4.x/apps/pattern-tools/generate_pattern.py
- https://github.com/opencv/opencv/blob/4.x/apps/pattern-tools/test_charuco_board.py

这些是当前本机已有的副本，不是本次重新下载并与上游逐字比对的快照。generate_pattern.py 包含本地运行示例等内容。保留现有文件，不代表所有行为与上游最新版本完全一致。

OpenCV 4.x 的 Apache License 2.0 副本见 ../licenses/OpenCV-Apache-2.0.txt；该副本来自上述官方仓库的 LICENSE。

## svgfig

board/svgfig.py 自带 BSD 3-Clause 许可头，版权信息为 Copyright (c) 2022, Jim Pivarski。原文件中的声明保留，副本见 ../licenses/svgfig-BSD-3-Clause.txt。

Windows 下这份文件会将相对输出文件名放到默认桌面目录，使用完整输出路径可以避免意外位置。

## 项目范围

本次补充第三方来源和许可副本，不为整个项目另行指定新的总许可证，也不改变第三方文件原有声明。已有 calib.py 是本地学习项目程序，本次作为现状归档。

相机规格引用：https://www.hbvcamera.com/4-mega-pixel-usb-cameras/dual-lens-camera-module.html 。实际帧尺寸和左右映射以用户实机测试为准。

