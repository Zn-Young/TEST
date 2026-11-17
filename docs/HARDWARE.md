# HBVCAM 单 USB 双摄说明

## 用户已经确认的设备行为

- 型号：HBVCAM-4M2142HD V22；厂商页面表中写作 4M2142HD-2 V22。
- 两颗 OV4689（1/3 英寸 CMOS），共用一根 USB 线。
- Windows 相机设备中可见内置 HP 摄像头和一项外接 USB Camera。
- 实际可用编号为 1，编号仍需在换接口、重连或换电脑后复核。
- 已验证使用 DirectShow 请求 MJPEG、3840×1080 后读到 (1080, 3840, 3)。
- 左右遮挡实验确认：画面左半幅对应物理左镜头，右半幅对应物理右镜头。
- 单目画面尺寸均为 1920×1080；分割后的像素坐标分别从各自画面的左上角计数。

厂商规格：[4M2142HD-2 V22](https://www.hbvcamera.com/4-mega-pixel-usb-cameras/dual-lens-camera-module.html)。厂商描述为双目同步模块，但本项目尚未测量曝光同步精度，也没有实际帧率测量报告。

## 最小实时预览

在 stereo-vision 环境中运行下列代码。它只预览，不保存图像。

~~~python
import cv2 as cv

cap = cv.VideoCapture(1, cv.CAP_DSHOW)
try:
    if not cap.isOpened():
        raise RuntimeError("无法打开相机")

    cap.set(cv.CAP_PROP_FOURCC, cv.VideoWriter_fourcc(*"MJPG"))
    cap.set(cv.CAP_PROP_FRAME_WIDTH, 3840)
    cap.set(cv.CAP_PROP_FRAME_HEIGHT, 1080)
    cap.set(cv.CAP_PROP_FPS, 30)

    cv.namedWindow("Stereo", cv.WINDOW_NORMAL)
    cv.resizeWindow("Stereo", 1280, 360)
    printed = False

    while True:
        ret, frame = cap.read()
        if not ret:
            raise RuntimeError("读取图像失败")
        if frame.shape[:2] != (1080, 3840):
            raise RuntimeError(f"实际尺寸不符合预期：{frame.shape}")

        left = frame[:, :1920]
        right = frame[:, 1920:]
        if not printed:
            print("完整帧：", frame.shape)
            print("左图：", left.shape, "右图：", right.shape)
            printed = True

        cv.imshow("Stereo", frame)
        if cv.waitKey(1) & 0xFF == ord("q"):
            break
finally:
    cap.release()
    cv.destroyAllWindows()
~~~

cap.set 是请求，实际 frame.shape 才是读到的结果。CAP_PROP_FPS=30 也只是请求。采集程序应验证真实尺寸并在不匹配时停止，不能将任意宽度的图像一律切半并假定正确。

## 对标定的影响

只打开一个 VideoCapture，每一帧产生一对左右原始图像。左右内参分别针对 1920×1080 像素坐标，立体校正也使用这个单目尺寸。

不要将整幅 3840×1080 图作为一台相机的图；它包含两个不同投影中心。不要把同一个编号重复打开后作为左右设备。

同一帧打包比两次独立 read() 更容易维持正确配对；但“打包在同一帧”本身不是曝光同时性的定量证明。需要严格运动测量时，应另外验证厂商同步机制和误差。

当前 calib.py 尚未实现这些采集变更，见 SINGLE_USB_HANDOFF.md。

