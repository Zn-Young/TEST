# Fcode：双目相机标定学习项目

保存当前双目标定程序、相机配置和标定板生成工具，并记录 HBVCAM 单 USB 双摄的后续适配要求。

**当前版本是修改前的基线：calib.py 仍按两台独立相机编写，尚未适配单 USB 左右拼接输出。** calibration_settings.yaml 中仍有未填写的参数，不能直接用于完整标定。本次归档保留程序和配置原值，未宣称已经完成真实相机标定。

## 目录

~~~text
.
├── calib.py                         # 双独立设备标定程序及立体校正参数计算
├── calibration_settings.yaml        # 原始工作配置，仍有空值
├── requirements.txt                 # 依赖版本范围
├── requirements-verified.txt        # 本机归档时已安装的依赖版本
├── environment.yml                  # 可选的 Conda 环境创建文件
├── board/
│   ├── generate_pattern.py          # 标定板 SVG 生成工具
│   ├── svgfig.py                    # 配套 SVG 工具，必须保留
│   ├── checkerboard_landscape.svg   # 当前已有棋盘格：9 列×6 行方格，25 mm/格
│   ├── pattern.png                  # 已有图案文件，保留供复习
│   ├── charuco_board_pattern.png    # 已有 ChArUco 图案文件
│   └── test_charuco_board.py        # 上游测试脚本，依赖额外测试资源
├── docs/
│   ├── HARDWARE.md                  # 相机实际测试结果、读取与分割方法
│   ├── BASELINE.md                  # 本次基线状态及验证范围
│   ├── DEVELOPMENT.md               # Git 提交、分支、恢复与同步
│   ├── SINGLE_USB_HANDOFF.md         # 提供给下一位 Agent 的改造要求
│   └── THIRD_PARTY_NOTICES.md        # 第三方文件来源说明
└── licenses/                        # 第三方许可证副本
~~~

## 1. 环境准备

推荐 Python 3.11，并使用带 GUI 的 opencv-contrib-python。本项目会调用 imshow，不能仅安装 headless 版本。避免同时安装多个提供 cv2 的 OpenCV 发行包。

已有 stereo-vision 环境时，在 PowerShell 中执行：

~~~powershell
conda activate stereo-vision
cd D:/Code/Fcode
python -c "import sys; print(sys.executable)"
python -m pip install -r requirements.txt
~~~

如果已有依赖且可以正常导入，不必重复安装。新电脑可以先克隆项目，再在项目根目录执行：

~~~powershell
git clone https://github.com/Zn-Young/TEST.git Fcode
cd Fcode
conda env create -f environment.yml
conda activate stereo-vision
~~~

environment.yml 创建同名环境；已存在 stereo-vision 时不要重复创建。requirements-verified.txt 记录本机版本，仅在需要复现这组依赖时使用；不同平台的二进制包可用性需另行确认。

如果 PowerShell 不认识 conda activate，可先在普通 PowerShell 设置当前用户的脚本策略，然后初始化：

~~~powershell
Set-ExecutionPolicy -Scope CurrentUser -ExecutionPolicy RemoteSigned
& 'D:/Anaconda/Scripts/conda.exe' init powershell
~~~

关闭并重新打开终端后再激活。路径按本机安装位置调整。若初始化报告安装目录 needs sudo，可能需要管理员权限完成一次初始化；用户 profile 已修改也不等于全部步骤成功。

## 2. 先确认当前硬件与代码是否匹配

本项目实际使用 HBVCAM-4M2142HD V22，双 OV4689、一根 USB。用户已验证：

- OpenCV 设备编号 1 可以读取该板；编号不是永久不变的硬件标识。
- 请求 MJPEG、3840×1080 后，实际 frame.shape 为 (1080, 3840, 3)。
- 左半幅对应物理左镜头，右半幅对应物理右镜头，已分别遮挡确认。
- 两幅单目图像各为 1920×1080。

**现有 calib.py 不能直接按上述方式采集：它会打开两个独立设备。不要将 camera0 和 camera1 都填成 1 来替代适配，也不要将整幅拼接图作为一台相机的标定图。**

相机测试代码和改造说明见 [硬件说明](docs/HARDWARE.md) 与 [单 USB 适配交接](docs/SINGLE_USB_HANDOFF.md)。

## 3. 现有 calibration_settings.yaml 参数

YAML 使用 UTF-8，程序明确以 utf-8-sig 读取，兼容可选 BOM。空值会读取成 None，不代表 0，也不会自动补全。

| 参数 | 当前值 | 在现有程序中的含义 |
|---|---:|---|
| camera0 | 未填 | 第一台独立相机的设备编号 |
| camera1 | 1 | 第二台独立相机的设备编号 |
| frame_width | 1920 | 每台独立相机请求的采集宽度，像素 |
| frame_height | 1080 | 每台独立相机请求的采集高度，像素 |
| mono_calibration_frames | 10 | 每台相机在单目阶段保存的张数 |
| stereo_calibration_frames | 10 | 双目阶段保存的图像对数 |
| view_resize | 1 | 预览缩小除数，宽高分别乘以 1/view_resize |
| checkerboard_box_size_scale | 未填 | 相邻内角点间的实际距离，即单个方格边长 |
| checkerboard_rows | 未填 | 代码传入 patternSize 的第一项：每行内角点数 |
| checkerboard_columns | 未填 | 第二项：每列内角点数 |
| cooldown | 100 | 每次保存之间的采集循环次数，非秒数 |

对当前已有的 9 列×6 行方格、25 mm/格的 SVG，未缩放打印且实测尺寸正确时，角点参数示例为：

~~~yaml
checkerboard_rows: 8
checkerboard_columns: 5
checkerboard_box_size_scale: 25
~~~

这个示例不代表已修改配置，也不代表正在使用的实物必然具有上述尺寸。长度单位由边长数值决定；按毫米填写，外参 T 的单位就是毫米。

## 4. 现有程序的运行流程

仅在使用两台独立相机、配置完整且图像尺寸一致时，现有入口适用：

~~~powershell
cd D:/Code/Fcode
python calib.py calibration_settings.yaml
~~~

1. 先打开 camera0，按空格启动，自动每隔 cooldown 次循环保存一张，共 mono_calibration_frames 张。
2. 再打开 camera1，同样需要按空格启动。
3. 分别检测两组图像的完整棋盘格，执行 cornerSubPix 并显示结果；小写 s 跳过，其他键接受。
4. 计算并保存左右相机内参、畸变系数。
5. 再次打开两台相机采集图像对，按空格启动，保存 stereo_calibration_frames 对。
6. 左右都检测成功的图像对进入人工检查；小写 s 排除整对，其他键接受。
7. 固定内参，以 stereoCalibrate 求 camera0 到 camera1 的 R、T。
8. 以 camera0 为世界坐标系保存外参，计算并保存立体校正参数。

采集阶段按 Esc 会退出程序；角点检查阶段代码没有单独处理 Esc，会将其当作接受按键。按键作用于获得焦点的 OpenCV 图像窗口。

当前两个 read() 依次执行，不保证两台独立设备曝光同步。采集没有实时棋盘格筛选；筛选后不足不会自动补拍，也没有最少有效样本数检查。

输出均相对于**启动时的当前工作目录**：

| 路径 | 内容 |
|---|---|
| frames/ | 单目采集图像 |
| frames_pair/ | 双目配对图像 |
| camera_parameters/camera0_intrinsics.dat | 第一台相机内参和畸变 |
| camera_parameters/camera1_intrinsics.dat | 第二台相机内参和畸变 |
| camera_parameters/camera0_rot_trans.dat | 世界到 camera0 的外参，当前为 I 和 0 |
| camera_parameters/camera1_rot_trans.dat | 世界到 camera1 的外参 |
| camera_parameters/stereo_rectification.dat | rect_R0、rect_R1、P0、P1、Q、ROI、图像尺寸 |

R、T 满足 X1 = R X0 + T；T 不是第二台相机在第一台相机坐标系中的位置，该位置为 -R.T @ T。立体校正阶段目前只保存参数，不会生成校正图像或深度图。

## 5. 生成棋盘格

脚本默认图案类型是 circles；普通棋盘格必须显式指定 checkerboard。

在项目根目录运行以下 PowerShell 命令，输出使用绝对路径，避免 Windows 下 svgfig 将相对路径写到桌面：

~~~powershell
$outputPath = Join-Path (Get-Location).Path 'board/checkerboard_custom.svg'
python board/generate_pattern.py -o "$outputPath" -T checkerboard -c 9 -r 6 -s 25 -u mm -w 297 -h 210
~~~

-c、-r 表示方格列数、行数，而标定配置使用内角点数，两者各差 1。-s 25 表示边长 25 mm，页面为 297×210 mm。查看参数帮助使用大写 -H；小写 -h 是页面高度。

输出是 SVG，不会自动弹出预览，也不会通过修改扩展名变成 PNG。可用浏览器查看，或使用 Inkscape 按页面范围导出白色不透明背景的 PNG。打印按 100%/实际大小，实测方格边长后填写配置。

ChArUco 生成还需要匹配的字典 JSON/JSON.GZ，本目录没有这些字典。test_charuco_board.py 还依赖 OpenCV 上游 tests_common、字典资源及可选 CairoSVG，不是直接在此仓库就能完整运行的自包含测试。

## 6. 后续修改与版本保存

先提交当前能工作的阶段，再创建单 USB 适配分支。完整命令见 [开发与版本管理](docs/DEVELOPMENT.md)。

采集图像、标定输出和 Python 缓存默认由 .gitignore 排除；现有 board 图案文件保留在仓库。需要归档某次标定结果时，另行整理数据、参数和说明，不要依赖被忽略的目录自动上传。

当前已知问题和实际验证边界见 [基线记录](docs/BASELINE.md)。第三方来源见 [来源说明](docs/THIRD_PARTY_NOTICES.md)。

