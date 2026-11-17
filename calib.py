"""
calib.py —— 双目相机标定
预期成果：标定参数（内参 K、畸变系数、外参 R/T）

流程：
    步骤1  单目采集标定图像                        -> frames/
    步骤2  单目标定，求内参 K 与畸变系数            -> camera_parameters/camera*_intrinsics.dat
    步骤3  双目同步采集标定图像                    -> frames_pair/
    步骤4  双目标定，求 R、T（camera0 -> camera1）
    步骤5  以 camera0 为世界原点保存外参            -> camera_parameters/camera*_rot_trans.dat
    步骤6  立体校正

运行：
    python calib.py calibration_settings.yaml
"""

import cv2 as cv
import glob
import numpy as np
import sys
import yaml
import os


# 保存从 calibration_settings.yaml 文件中读取的标定设置
calibration_settings = {}


# 打开并加载 calibration_settings.yaml 文件
def parse_calibration_settings_file(filename):

    global calibration_settings

    if not os.path.exists(filename):
        print('File does not exist:', filename)
        quit()

    print('Using for calibration settings: ', filename)

    with open(filename, encoding="utf-8-sig") as f:
        calibration_settings = yaml.safe_load(f)

    # 进行基本检查，确保加载了正确的文件
    if 'camera0' not in calibration_settings.keys():
        print('camera0 key was not found in the settings file. Check if correct calibration_settings.yaml file was passed')
        quit()


# 步骤1：打开相机视频流并保存图像帧
def save_frames_single_camera(camera_name):

    # 创建图像帧保存目录
    if not os.path.exists('frames'):
        os.mkdir('frames')

    # 获取设置
    camera_device_id = calibration_settings[camera_name]
    width = calibration_settings['frame_width']
    height = calibration_settings['frame_height']
    number_to_save = calibration_settings['mono_calibration_frames']
    view_resize = calibration_settings['view_resize']
    cooldown_time = calibration_settings['cooldown']

    # 打开视频流并设置分辨率。
    # 注意：即使设置了不受支持的分辨率，也不会报错。
    cap = cv.VideoCapture(camera_device_id)
    cap.set(3, width)
    cap.set(4, height)

    cooldown = cooldown_time
    start = False
    saved_count = 0

    while True:

        ret, frame = cap.read()
        if ret == False:
            # 如果未接收到视频数据，则无法标定相机，因此退出程序。
            print("No video data received from camera. Exiting...")
            quit()

        frame_small = cv.resize(frame, None, fx=1/view_resize, fy=1/view_resize)

        if not start:
            cv.putText(frame_small, "Press SPACEBAR to start collection frames", (50,50), cv.FONT_HERSHEY_COMPLEX, 1, (0,0,255), 1)

        if start:
            cooldown -= 1
            cv.putText(frame_small, "Cooldown: " + str(cooldown), (50,50), cv.FONT_HERSHEY_COMPLEX, 1, (0,255,0), 1)
            cv.putText(frame_small, "Num frames: " + str(saved_count), (50,100), cv.FONT_HERSHEY_COMPLEX, 1, (0,255,0), 1)

            # 当采集间隔倒计数减至 0 时保存图像帧。
            if cooldown <= 0:
                savename = os.path.join('frames', camera_name + '_' + str(saved_count) + '.png')
                cv.imwrite(savename, frame)
                saved_count += 1
                cooldown = cooldown_time

        cv.imshow('frame_small', frame_small)
        k = cv.waitKey(1)

        if k == 27:
            # 任何时候按下 ESC，程序都会退出。
            quit()

        if k == 32:
            # 按下空格键开始采集数据
            start = True

        # 保存的图像帧数量达到要求后退出循环
        if saved_count == number_to_save: break

    cv.destroyAllWindows()


# 步骤2：利用保存的图像帧进行单目标定，获取相机内参。
def calibrate_camera_for_intrinsic_parameters(images_prefix):

    # 注意：images_prefix 包含相机名称，例如 "frames/camera0*"。
    images_names = glob.glob(images_prefix)

    # 读取所有图像帧
    images = [cv.imread(imname, 1) for imname in images_names]

    # 棋盘格角点检测所用的终止条件。
    # 如果代码无法找到棋盘格，可调整此设置。
    criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 100, 0.001)

    rows = calibration_settings['checkerboard_rows']
    columns = calibration_settings['checkerboard_columns']
    world_scaling = calibration_settings['checkerboard_box_size_scale'] #将坐标转换为用户指定的长度尺度

    # 棋盘格角点在棋盘格世界坐标系中的坐标
    objp = np.zeros((rows*columns,3), np.float32)
    objp[:,:2] = np.mgrid[0:rows,0:columns].T.reshape(-1,2)
    objp = world_scaling* objp

    # 图像帧尺寸，所有图像帧应具有相同尺寸。
    width = images[0].shape[1]
    height = images[0].shape[0]

    # 棋盘格角点的像素坐标
    imgpoints = [] # 图像平面上的二维点。

    # 棋盘格角点在棋盘格世界坐标系中的坐标。
    objpoints = [] # 真实世界坐标系中的三维点


    for i, frame in enumerate(images):
        gray = cv.cvtColor(frame, cv.COLOR_BGR2GRAY)

        # 检测棋盘格角点
        ret, corners = cv.findChessboardCorners(gray, (rows, columns), None)

        if ret == True:

            # 用于细化角点定位的窗口尺寸，不宜设置过大。
            conv_size = (11, 11)

            # 使用 OpenCV 尝试细化棋盘格角点坐标
            corners = cv.cornerSubPix(gray, corners, conv_size, (-1, -1), criteria)
            cv.drawChessboardCorners(frame, (rows,columns), corners, ret)
            cv.putText(frame, 'If detected points are poor, press "s" to skip this sample', (25, 25), cv.FONT_HERSHEY_COMPLEX, 1, (0,0,255), 1)

            cv.imshow('img', frame)
            k = cv.waitKey(0)

            if k & 0xFF == ord('s'):
                print('skipping')
                continue

            objpoints.append(objp)
            imgpoints.append(corners)


    cv.destroyAllWindows()
    ret, cmtx, dist, rvecs, tvecs = cv.calibrateCamera(objpoints, imgpoints, (width, height), None, None)
    print('rmse:', ret)
    print('camera matrix:\n', cmtx)
    print('distortion coeffs:', dist)

    return cmtx, dist


# 步骤2：将相机内参保存到文件
def save_camera_intrinsics(camera_matrix, distortion_coefs, camera_name):

    # 如果文件夹不存在，则创建文件夹
    if not os.path.exists('camera_parameters'):
        os.mkdir('camera_parameters')

    out_filename = os.path.join('camera_parameters', camera_name + '_intrinsics.dat')
    outf = open(out_filename, 'w')

    outf.write('intrinsic:\n')
    for l in camera_matrix:
        for en in l:
            outf.write(str(en) + ' ')
        outf.write('\n')

    outf.write('distortion:\n')
    for en in distortion_coefs[0]:
        outf.write(str(en) + ' ')
    outf.write('\n')


# 步骤3：打开两台相机并采集标定图像帧
def save_frames_two_cams(camera0_name, camera1_name):

    # 创建图像帧保存目录
    if not os.path.exists('frames_pair'):
        os.mkdir('frames_pair')

    # 数据采集设置
    view_resize = calibration_settings['view_resize']
    cooldown_time = calibration_settings['cooldown']
    number_to_save = calibration_settings['stereo_calibration_frames']

    # 打开视频流
    cap0 = cv.VideoCapture(calibration_settings[camera0_name])
    cap1 = cv.VideoCapture(calibration_settings[camera1_name])

    # 设置相机分辨率
    width = calibration_settings['frame_width']
    height = calibration_settings['frame_height']
    cap0.set(3, width)
    cap0.set(4, height)
    cap1.set(3, width)
    cap1.set(4, height)

    cooldown = cooldown_time
    start = False
    saved_count = 0
    while True:

        ret0, frame0 = cap0.read()
        ret1, frame1 = cap1.read()

        if not ret0 or not ret1:
            print('Cameras not returning video data. Exiting...')
            quit()

        frame0_small = cv.resize(frame0, None, fx=1./view_resize, fy=1./view_resize)
        frame1_small = cv.resize(frame1, None, fx=1./view_resize, fy=1./view_resize)

        if not start:
            cv.putText(frame0_small, "Make sure both cameras can see the calibration pattern well", (50,50), cv.FONT_HERSHEY_COMPLEX, 1, (0,0,255), 1)
            cv.putText(frame0_small, "Press SPACEBAR to start collection frames", (50,100), cv.FONT_HERSHEY_COMPLEX, 1, (0,0,255), 1)

        if start:
            cooldown -= 1
            cv.putText(frame0_small, "Cooldown: " + str(cooldown), (50,50), cv.FONT_HERSHEY_COMPLEX, 1, (0,255,0), 1)
            cv.putText(frame0_small, "Num frames: " + str(saved_count), (50,100), cv.FONT_HERSHEY_COMPLEX, 1, (0,255,0), 1)

            cv.putText(frame1_small, "Cooldown: " + str(cooldown), (50,50), cv.FONT_HERSHEY_COMPLEX, 1, (0,255,0), 1)
            cv.putText(frame1_small, "Num frames: " + str(saved_count), (50,100), cv.FONT_HERSHEY_COMPLEX, 1, (0,255,0), 1)

            # 当采集间隔倒计数减至 0 时保存图像帧。
            if cooldown <= 0:
                savename = os.path.join('frames_pair', camera0_name + '_' + str(saved_count) + '.png')
                cv.imwrite(savename, frame0)

                savename = os.path.join('frames_pair', camera1_name + '_' + str(saved_count) + '.png')
                cv.imwrite(savename, frame1)

                saved_count += 1
                cooldown = cooldown_time

        cv.imshow('frame0_small', frame0_small)
        cv.imshow('frame1_small', frame1_small)
        k = cv.waitKey(1)

        if k == 27:
            # 任何时候按下 ESC，程序都会退出。
            quit()

        if k == 32:
            # 按下空格键开始采集数据
            start = True

        # 保存的图像帧数量达到要求后退出循环
        if saved_count == number_to_save: break

    cv.destroyAllWindows()


# 步骤4：读取成对标定图像并进行双目标定，求取 camera0 到 camera1 的坐标变换
def stereo_calibrate(mtx0, dist0, mtx1, dist1, frames_prefix_c0, frames_prefix_c1):
    # 读取同步采集的图像帧
    c0_images_names = sorted(glob.glob(frames_prefix_c0))
    c1_images_names = sorted(glob.glob(frames_prefix_c1))

    # 读取图像
    c0_images = [cv.imread(imname, 1) for imname in c0_images_names]
    c1_images = [cv.imread(imname, 1) for imname in c1_images_names]

    # 如果双目标定效果不佳，可调整此设置。
    criteria = (cv.TERM_CRITERIA_EPS + cv.TERM_CRITERIA_MAX_ITER, 100, 0.001)

    # 标定板设置
    rows = calibration_settings['checkerboard_rows']
    columns = calibration_settings['checkerboard_columns']
    world_scaling = calibration_settings['checkerboard_box_size_scale']

    # 棋盘格角点在棋盘格世界坐标系中的坐标
    objp = np.zeros((rows*columns,3), np.float32)
    objp[:,:2] = np.mgrid[0:rows,0:columns].T.reshape(-1,2)
    objp = world_scaling* objp

    # 图像帧尺寸，所有图像帧应具有相同尺寸。
    width = c0_images[0].shape[1]
    height = c0_images[0].shape[0]

    # 棋盘格角点的像素坐标
    imgpoints_left = [] # 图像平面上的二维点。
    imgpoints_right = []

    # 棋盘格角点在棋盘格世界坐标系中的坐标。
    objpoints = [] # 真实世界坐标系中的三维点

    for frame0, frame1 in zip(c0_images, c1_images):
        gray1 = cv.cvtColor(frame0, cv.COLOR_BGR2GRAY)
        gray2 = cv.cvtColor(frame1, cv.COLOR_BGR2GRAY)
        c_ret1, corners1 = cv.findChessboardCorners(gray1, (rows, columns), None)
        c_ret2, corners2 = cv.findChessboardCorners(gray2, (rows, columns), None)

        if c_ret1 == True and c_ret2 == True:

            corners1 = cv.cornerSubPix(gray1, corners1, (11, 11), (-1, -1), criteria)
            corners2 = cv.cornerSubPix(gray2, corners2, (11, 11), (-1, -1), criteria)

            p0_c1 = corners1[0,0].astype(np.int32)
            p0_c2 = corners2[0,0].astype(np.int32)

            cv.putText(frame0, 'O', (p0_c1[0], p0_c1[1]), cv.FONT_HERSHEY_COMPLEX, 1, (0,0,255), 1)
            cv.drawChessboardCorners(frame0, (rows,columns), corners1, c_ret1)
            cv.imshow('img', frame0)

            cv.putText(frame1, 'O', (p0_c2[0], p0_c2[1]), cv.FONT_HERSHEY_COMPLEX, 1, (0,0,255), 1)
            cv.drawChessboardCorners(frame1, (rows,columns), corners2, c_ret2)
            cv.imshow('img2', frame1)
            k = cv.waitKey(0)

            if k & 0xFF == ord('s'):
                print('skipping')
                continue

            objpoints.append(objp)
            imgpoints_left.append(corners1)
            imgpoints_right.append(corners2)

    stereocalibration_flags = cv.CALIB_FIX_INTRINSIC
    ret, CM1, dist0, CM2, dist1, R, T, E, F = cv.stereoCalibrate(objpoints, imgpoints_left, imgpoints_right, mtx0, dist0,
                                                                 mtx1, dist1, (width, height), criteria = criteria, flags = stereocalibration_flags)

    print('rmse: ', ret)
    cv.destroyAllWindows()
    return R, T


# 将旋转矩阵 R 和平移向量 T 转换为齐次变换矩阵
def _make_homogeneous_rep_matrix(R, t):
    P = np.zeros((4,4))
    P[:3,:3] = R
    P[:3, 3] = t.reshape(3)
    P[3,3] = 1

    return P

# 根据相机标定数据构建投影矩阵
def get_projection_matrix(cmtx, R, T):
    P = cmtx @ _make_homogeneous_rep_matrix(R, T)[:3,:]
    return P

# 步骤5：将外参标定结果保存到文件
def save_extrinsic_calibration_parameters(R0, T0, R1, T1, prefix = ''):

    # 如果文件夹不存在，则创建文件夹
    if not os.path.exists('camera_parameters'):
        os.mkdir('camera_parameters')

    camera0_rot_trans_filename = os.path.join('camera_parameters', prefix + 'camera0_rot_trans.dat')
    outf = open(camera0_rot_trans_filename, 'w')

    outf.write('R:\n')
    for l in R0:
        for en in l:
            outf.write(str(en) + ' ')
        outf.write('\n')

    outf.write('T:\n')
    for l in T0:
        for en in l:
            outf.write(str(en) + ' ')
        outf.write('\n')
    outf.close()

    # R1 和 T1 即双目标定返回的旋转矩阵和平移向量
    camera1_rot_trans_filename = os.path.join('camera_parameters', prefix + 'camera1_rot_trans.dat')
    outf = open(camera1_rot_trans_filename, 'w')

    outf.write('R:\n')
    for l in R1:
        for en in l:
            outf.write(str(en) + ' ')
        outf.write('\n')

    outf.write('T:\n')
    for l in T1:
        for en in l:
            outf.write(str(en) + ' ')
        outf.write('\n')
    outf.close()

    return R0, T0, R1, T1


# 步骤6：根据双目标定结果计算立体校正参数
def stereo_rectify(cmtx0, dist0, cmtx1, dist1, R, T, image_size, alpha = 1.):

    # R、T 是 camera0 到 camera1 的外参；image_size 为标定图像的实际宽、高。
    # rect_R0、rect_R1 是校正旋转矩阵，避免与已有相机外参 R0、R1 混淆。
    # alpha=1 保留原始图像视野，但边缘可能存在黑色无效区域；alpha=0 会裁减视野以去除黑边。
    rect_R0, rect_R1, P0, P1, Q, roi0, roi1 = cv.stereoRectify(cmtx0, dist0, cmtx1, dist1,
                                                            image_size, R, T, flags = cv.CALIB_ZERO_DISPARITY,
                                                            alpha = alpha, newImageSize = image_size)

    # P0、P1 用于校正后的三角测量；Q 用于将视差转换为三维坐标。
    # roi0、roi1 分别表示左右校正图像中的有效像素矩形区域。
    return rect_R0, rect_R1, P0, P1, Q, roi0, roi1


# 步骤6：将立体校正参数保存到文件
def save_stereo_rectification_parameters(rect_R0, rect_R1, P0, P1, Q, roi0, roi1, image_size, prefix = ''):

    # 沿用已有标定参数的保存目录和文本格式。
    if not os.path.exists('camera_parameters'):
        os.mkdir('camera_parameters')

    out_filename = os.path.join('camera_parameters', prefix + 'stereo_rectification.dat')
    outf = open(out_filename, 'w')

    # 依次保存两个 3×3 校正旋转矩阵、两个 3×4 投影矩阵和一个 4×4 视差映射矩阵。
    for name, matrix in [('rect_R0', rect_R0), ('rect_R1', rect_R1), ('P0', P0), ('P1', P1), ('Q', Q)]:
        outf.write(name + ':\n')
        for l in matrix:
            for en in l:
                outf.write(str(en) + ' ')
            outf.write('\n')

    # 图像尺寸按 width、height 保存；有效区域按 x、y、width、height 保存。
    # 后续使用这些参数时，应保持相同的图像尺寸和左右相机顺序。
    for name, values in [('image_size', image_size), ('roi0', roi0), ('roi1', roi1)]:
        outf.write(name + ':\n')
        for en in values:
            outf.write(str(en) + ' ')
        outf.write('\n')
    outf.close()

    print('Stereo rectification parameters saved to:', out_filename)


def main():

    if len(sys.argv) != 2:
        print('Call with settings filename: "python calib.py calibration_settings.yaml"')
        return

    # 打开并解析设置文件
    parse_calibration_settings_file(sys.argv[1])


    """步骤1：保存各单目相机的标定图像帧"""
    save_frames_single_camera('camera0') #保存 camera0 的图像帧
    save_frames_single_camera('camera1') #保存 camera1 的图像帧


    """步骤2：获取并保存相机内参矩阵"""
    #camera0 的内参
    images_prefix = os.path.join('frames', 'camera0*')
    cmtx0, dist0 = calibrate_camera_for_intrinsic_parameters(images_prefix)
    save_camera_intrinsics(cmtx0, dist0, 'camera0') #将 cmtx 和 dist 写入磁盘
    #camera1 的内参
    images_prefix = os.path.join('frames', 'camera1*')
    cmtx1, dist1 = calibrate_camera_for_intrinsic_parameters(images_prefix)
    save_camera_intrinsics(cmtx1, dist1, 'camera1') #将 cmtx 和 dist 写入磁盘


    """步骤3：保存两台相机同时采集的标定图像帧"""
    save_frames_two_cams('camera0', 'camera1') #保存同时采集的图像帧


    """步骤4：利用成对标定板图像求取 camera0 到 camera1 的旋转和平移"""
    frames_prefix_c0 = os.path.join('frames_pair', 'camera0*')
    frames_prefix_c1 = os.path.join('frames_pair', 'camera1*')
    R, T = stereo_calibrate(cmtx0, dist0, cmtx1, dist1, frames_prefix_c0, frames_prefix_c1)


    """步骤5：以 camera0 为世界坐标系原点保存标定数据。"""
    #camera0 的旋转矩阵和平移向量分别为单位矩阵和零向量
    R0 = np.eye(3, dtype=np.float32)
    T0 = np.array([0., 0., 0.]).reshape((3, 1))

    save_extrinsic_calibration_parameters(R0, T0, R, T) #将 R 和 T 写入磁盘
    R1 = R; T1 = T #为避免混淆，将 camera1 的 R 和 T 分别记为 R1 和 T1



    """步骤6：计算并保存立体校正参数"""
    # 使用实际标定图像的尺寸，避免相机未采用设置文件中指定的分辨率。
    calibration_frame = cv.imread(sorted(glob.glob(frames_prefix_c0))[0], 1)
    image_size = (calibration_frame.shape[1], calibration_frame.shape[0])

    rect_R0, rect_R1, P0, P1, Q, roi0, roi1 = stereo_rectify(cmtx0, dist0, cmtx1, dist1, R, T, image_size)
    save_stereo_rectification_parameters(rect_R0, rect_R1, P0, P1, Q, roi0, roi1, image_size)


if __name__ == '__main__':
    main()
