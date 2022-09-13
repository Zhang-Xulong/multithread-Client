import numpy as np
import time
import datetime
import paho.mqtt.client as mqtt
import threading
import os
import matplotlib.pyplot as plt
import struct
from scipy.io.wavfile import write

service_id = 'supervisor'
topic = '/Service'
IP = '124.223.71.233'
path_root = os.getcwd()

class stm32_data:
    data_mode = 0x01  # 0x01透传模式，0x10算法模式*
    data_type = 0x01  # 0x01声音数据，0x10加速度数据
    data_sta = 0xff  # 0xff透传模式下弃用，0x01为好数据，0x10为坏数据
    data_num = 0x1111  # 两个字节表示包的个数
    data_len = 0x01  # 每一包数据的字节数量
    data_recv_num = 0  # 已经接收包的数量
    data_recv_sta = 0  # 数据接收的状态，0表示等待接收握手，1表示握手成功接收数据

    def reset_all(self):
        self.data_mode = 0x01
        self.data_type = 0x01
        self.data_sta = 0xff
        self.data_num = 0x1111
        self.data_len = 0x01
        self.data_recv_num = 0
        self.data_recv_sta = 0


class IOT_data:
    data_info = ""
    data_str = []
    data_storage = [b'', "", data_str]

    sound_trans_data = "Sound data"
    acc_trans_data = "Acc data"

    sound_algorithm_data_good = "Sound Pro data good"
    sound_algorithm_data_bad = "Sound Pro data bad"
    acc_algorithm_data_good = "Acc Pro data good"
    acc_algorithm_data_bad = "Acc Pro data bad"

    data_info_index = [sound_trans_data, acc_trans_data,
                       sound_algorithm_data_good, sound_algorithm_data_bad,
                       acc_algorithm_data_good, acc_algorithm_data_bad]
    # 一个数据类型的信息，包含有开头的info字符串，代表这是哪一段信息，后面的包长度，以及最后的数据存储（bytes，字符串，浮点数据）
    Package0 = [data_info, 0, data_storage]
    Package1 = [data_info, 0, data_storage]
    Package2 = [data_info, 0, data_storage]
    Package3 = [data_info, 0, data_storage]
    Package4 = [data_info, 0, data_storage]
    Package5 = [data_info, 0, data_storage]
    # 声音透传，加速度透传，声音算法，加速度算法  一共四种数据类型
    General_Storage = [Package0, Package1, Package2, Package3, Package4, Package5]

    @classmethod
    def package_reset(cls):
        cls.data_str = []
        cls.data_storage = [b'', "", cls.data_str]

    def reset_all(self):
        null_data_str = []
        null_data_storage = [b'', "", null_data_str]
        self.package_reset()
        for i in range(0, 6):
            self.General_Storage[i][0] = self.data_info_index[i]
            self.General_Storage[i][1] = 0
            self.General_Storage[i][2] = null_data_storage


def Bytes2Float32String(feature, d_len):
    x = ""
    while len(feature) % 4 != 0:
        feature = feature + b'0'
    for i in range(d_len):
        data = feature[i * 4: (i * 4) + 4]
        # try:
        #     a = struct.unpack('<f', data)
        #     x += str(round(float(a[0]), 7))
        #     if i < d_len - 1:
        #         x += ',\r\n'
        # except Exception as e:
        #     print(e)
        a = struct.unpack('<f', data)
        x += str(round(float(a[0]), 7))
        if i < d_len - 1:
            x += ',\r\n'
    return x


def Bytes2Float32Slice(feature, d_len):
    x = []
    while len(feature) % 4 != 0:
        feature = feature + b'0'
    for i in range(d_len):
        data = feature[i * 4: (i * 4) + 4]
        # try:
        #     a = struct.unpack('<f', data)
        #     x.append(round(float(a[0]), 7))
        # except Exception as e:
        #     print(e)
        a = struct.unpack('<f', data)
        x.append(round(float(a[0]), 7))
    return x


def Bytes2Int8String(feature, len):
    x = ""
    for i in range(len):
        data = feature[i]
        if data > 128:
            a = data - 256
        else:
            a = data
        x += str(a)
        if i < len - 1:
            x += ',\r\n'
    return x


def Bytes2Int8Slice(feature, len):
    x = []
    for i in range(len):
        data = feature[i]
        if data > 128:
            a = data - 256
        else:
            a = data
        x.append(a)
    return x


def process_init():
    # 当前文件夹
    path = os.getcwd()
    # 创建所需的图片以及数据文件夹
    path_ak = path + "\\acc\\keep\\DATA"
    path_sk = path + "\\sound\\keep\\DATA"
    if os.path.exists(path_ak) == 0:
        os.makedirs(path_ak)
    if os.path.exists(path_sk) == 0:
        os.makedirs(path_sk)

    path_sk1 = path + "\\sound\\keep\\Audio"
    if os.path.exists(path_sk1) == 0:
        os.makedirs(path_sk1)

    path_at_ng = path + "\\acc\\ng\\time\\DATA"
    path_af_ng = path + "\\acc\\ng\\frequency\\DATA"
    if os.path.exists(path_at_ng) == 0:
        os.makedirs(path_at_ng)
    if os.path.exists(path_af_ng) == 0:
        os.makedirs(path_af_ng)
    path_at_ok = path + "\\acc\\ok\\time\\DATA"
    path_af_ok = path + "\\acc\\ok/frequency\\DATA"
    if os.path.exists(path_at_ok) == 0:
        os.makedirs(path_at_ok)
    if os.path.exists(path_af_ok) == 0:
        os.makedirs(path_af_ok)

    path_st_ng_d = path + "\\sound\\ng\\time\\DATA"
    path_st_ng_a = path + "\\sound\\ng\\time\\Audio"
    path_sf_ng = path + "\\sound\\ng\\frequency\\DATA"
    if os.path.exists(path_st_ng_d) == 0:
        os.makedirs(path_st_ng_d)
    if os.path.exists(path_st_ng_a) == 0:
        os.makedirs(path_st_ng_a)
    if os.path.exists(path_sf_ng) == 0:
        os.makedirs(path_sf_ng)

    path_st_ok_d = path + "\\sound\\ok\\time\\DATA"
    path_st_ok_a = path + "\\sound\\ok\\time\\Audio"
    path_sf_ok = path + "\\sound\\ok\\frequency\\DATA"
    if os.path.exists(path_st_ok_d) == 0:
        os.makedirs(path_st_ok_d)
    if os.path.exists(path_st_ok_a) == 0:
        os.makedirs(path_st_ok_a)
    if os.path.exists(path_sf_ok) == 0:
        os.makedirs(path_sf_ok)


def judge(data):
    judge_flag = 0
    judge_cnt1 = 0
    judge_cnt2 = 0
    judge_fft = np.fft.fft(data)
    judge_fft_20 = 20 * np.log(np.abs(judge_fft))
    for i in range(25, 76):
        if judge_fft_20[i] > 75:
            judge_cnt1 = judge_cnt1 + 1
    for i in range(650, 951):
        if judge_fft_20[i] > 65:
            judge_cnt2 = judge_cnt2 + 1
    if judge_cnt1 >= 4 and judge_cnt2 >= 20:
        judge_flag = 1
    return judge_flag


class MQTT_Receive:
    msg_count = 0
    Str_Flag = 0

    def __init__(self, STM32Data, BC25_Data):
        self.STM32Data = STM32Data
        self.BC25_Data = BC25_Data

    def reset(self):
        self.msg_count = 0
        self.Str_Flag = 0

    # @staticmethod
    def get_header(self, Message):
        STM32Data = self.STM32Data
        if len(Message) != 11:
            print("Cant get Header")
            return -1
        else:
            if Message[0] == 0xaa and Message[1] == 0xbb and Message[9] == 0xcc and Message[10] == 0xdd:
                STM32Data.data_mode = Message[2]  # 透传or算法
                STM32Data.data_type = Message[3]  # 声音or加速度
                STM32Data.data_sta = Message[4]  # 数据好还是坏还是无所谓
                STM32Data.data_num = Message[5] * 256 + Message[6]  # 数据包数量
                STM32Data.data_len = Message[7] * 256 + Message[8]
                self.STM32Data = STM32Data
                print("OK")
                return 1
            else:
                return -1
        pass

    def receive_all(self, IOT_MSG):
        # global STM32Data
        # global BC25_Data
        STM32Data = self.STM32Data
        BC25_Data = self.BC25_Data
        if len(IOT_MSG) == 5:
            if IOT_MSG[0] == 0xAF and IOT_MSG[1] == 0xBE and IOT_MSG[2] == 0xCD and IOT_MSG[3] == 0xAA and IOT_MSG[4] == 0xFF:
                print("BC25 Reboot")
                BC25_Data.reset_all()
                self.reset()
        else:
            # 准备接收包头
            if self.Str_Flag == 0:
                if self.get_header(IOT_MSG) == 1:
                    print("Successfully get header!")
                    self.Str_Flag = 1  # 跳转到下一步
                else:
                    self.Str_Flag = 0  # 从头开始
            # 准备接收数据
            elif self.Str_Flag == 1:
                self.msg_count = self.msg_count + 1
                # print("Receiving No.{} package".format(self.msg_count))
                # 打印接收进度
                # print("\r数据接收中{0}%".format(self.msg_count * 100 / STM32Data.data_num), end="", flush=True)
                BC25_Data.data_storage[0] = BC25_Data.data_storage[0] + IOT_MSG  # binascii.b2a_hex(IOT_MSG)
                if self.msg_count == STM32Data.data_num:
                    self.Str_Flag = 0  # 跳转回头，重新接收下一包
                    return "Receive OK"

                elif MQTT_Receive.msg_count > STM32Data.data_num:
                    print("Receive Error! PKG oversize!")
                    self.reset()
                    MQTT_Receive.Str_Flag = 0  # 跳转回头开始接收
        self.STM32Data = STM32Data
        self.BC25_Data = BC25_Data


class Subscriber:
    def __init__(self, client_id, receive_topic, qos, device_id):
        super(Subscriber, self).__init__()
        self.client = mqtt.Client(client_id, clean_session=True, userdata=None, transport="tcp")
        self.client.on_connect = self.on_connect
        self.client.on_message = self.on_message
        self.Receive_topic = receive_topic
        self.qos = qos
        self.device_id = device_id
        self.STM32Data = stm32_data()
        self.STM32Data.reset_all()
        self.BC25_Data = IOT_data()
        self.BC25_Data.reset_all()
        self.MQTT_Data = MQTT_Receive(self.STM32Data, self.BC25_Data)
        self.MQTT_Data.reset()
        self.draw_pic_flag = 0

    def connect(self, host: str, port: int, keepalive: int):
        self.client.connect(host, port, keepalive)

    def disconnect(self):
        self.client.disconnect()

    def subscribe(self, topic):
        self.client.subscribe(topic, self.qos)

    def loop_forever(self):
        self.client.loop_forever()

    # 连接成功回调
    def on_connect(self, client, userdata, flags, rc):
        print(str(self.device_id) +': Connected with result code ' + str(rc))
        self.client.subscribe(self.Receive_topic, self.qos)

    # 消息接收回调
    def on_message(self, client, userdata, msg):
        pass
        # #print(msg.payload)
        # if self.MQTT_Data.receive_all(msg.payload) == "Receive OK":
        #    return self.data_handler_callback()

    def Listen_CB(self, client, userdata, msg):
        # print(str(self.device_id),':')
        # print(msg.payload)
        if self.MQTT_Data.receive_all(msg.payload) == "Receive OK":
            return self.data_handler_callback()

    # 接收成功回调函数
    # @staticmethod
    def data_handler_callback(self):
        MQTT_Data = self.MQTT_Data
        STM32Data = self.MQTT_Data.STM32Data
        BC25_Data = self.MQTT_Data.BC25_Data

        __index = 0
        mode = ""
        receive_finished_flag = 0
        print("\rReceived all PKGs!")
        MQTT_Data.reset()
        # 判断数据包类型
        if STM32Data.data_mode == 0x01:
            if STM32Data.data_sta == 0xFF:
                mode = "keep_storage"
            elif STM32Data.data_sta == 0xEE:
                mode = "stop_storage"
            if STM32Data.data_type == 0x01:
                __index = 0
            elif STM32Data.data_type == 0x10:
                __index = 1
        elif STM32Data.data_mode == 0x10:
            mode = "storage_once"
            if STM32Data.data_type == 0x01:
                if STM32Data.data_sta == 0x01:
                    __index = 2
                elif STM32Data.data_sta == 0x10:
                    __index = 3
            elif STM32Data.data_type == 0x10:
                if STM32Data.data_sta == 0x01:
                    __index = 4
                elif STM32Data.data_sta == 0x10:
                    __index = 5
        print("mode is " + mode, "index is " + str(__index))

        if mode == "keep_storage":
            # 继续缓存
            # 如果是加速度类的数据
            if __index == 1 or __index == 4 or __index == 5:
                print("Acc data mode")
                data_len = int((STM32Data.data_num * STM32Data.data_len))
                BC25_Data.General_Storage[__index][1] += data_len
                BC25_Data.data_storage[1] = Bytes2Int8String(BC25_Data.data_storage[0], data_len)
                BC25_Data.data_storage[2] = Bytes2Int8Slice(BC25_Data.data_storage[0], data_len)

            else:
                data_len = int((STM32Data.data_num * STM32Data.data_len) / 4)
                BC25_Data.General_Storage[__index][1] += data_len
                BC25_Data.data_storage[1] = Bytes2Float32String(BC25_Data.data_storage[0], data_len)
                BC25_Data.data_storage[2] = Bytes2Float32Slice(BC25_Data.data_storage[0], data_len)

            for loop in range(0, 3):
                BC25_Data.General_Storage[__index][2][loop] += BC25_Data.data_storage[loop]

        elif mode == "stop_storage":
            # 先是继续缓存，直到存储完成后，清空缓存
            # 如果是加速度类的数据
            if __index == 1 or __index == 4 or __index == 5:
                print("Acc data mode")
                data_len = int((STM32Data.data_num * STM32Data.data_len))
                BC25_Data.General_Storage[__index][1] += data_len
                BC25_Data.data_storage[1] = Bytes2Int8String(BC25_Data.data_storage[0], data_len)
                BC25_Data.data_storage[2] = Bytes2Int8Slice(BC25_Data.data_storage[0], data_len)
            else:
                data_len = int((STM32Data.data_num * STM32Data.data_len) / 4)
                BC25_Data.General_Storage[__index][1] += data_len
                BC25_Data.data_storage[1] = Bytes2Float32String(BC25_Data.data_storage[0], data_len)
                BC25_Data.data_storage[2] = Bytes2Float32Slice(BC25_Data.data_storage[0], data_len)
            # 存储数据
            for loop in range(0, 3):
                BC25_Data.General_Storage[__index][2][loop] += BC25_Data.data_storage[loop]
            print("Transparent mode finished !")
            receive_finished_flag = 1

        elif mode == "storage_once":
            # 如果是加速度类的数据
            if __index == 1 or __index == 4 or __index == 5:
                print("Acc data mode")
                data_len = int((STM32Data.data_num * STM32Data.data_len))
                BC25_Data.General_Storage[__index][1] += data_len
                BC25_Data.data_storage[1] = Bytes2Int8String(BC25_Data.data_storage[0], data_len)
                BC25_Data.data_storage[2] = Bytes2Int8Slice(BC25_Data.data_storage[0], data_len)
            # 是声音类的数据
            else:
                data_len = int((STM32Data.data_num * STM32Data.data_len) / 4)
                BC25_Data.General_Storage[__index][1] = data_len
                BC25_Data.data_storage[1] = Bytes2Float32String(BC25_Data.data_storage[0], data_len)
                BC25_Data.data_storage[2] = Bytes2Float32Slice(BC25_Data.data_storage[0], data_len)
            # 存储数据
            BC25_Data.General_Storage[__index][2] = BC25_Data.data_storage
            print("Algorithm mode finished !")
            receive_finished_flag = 1

        BC25_Data.package_reset()

        print("========PKG_INFO========")
        print("This data is " + BC25_Data.General_Storage[__index][0])
        print("Data len is {}".format(BC25_Data.General_Storage[__index][1]))
        print("Package num  is " + str(STM32Data.data_num))
        print("One PKG size is " + str(STM32Data.data_len))
        print("========INFO_END========")
        # 如果接受完毕一组数据
        process_init()
        if receive_finished_flag == 1:
            # 保存在对应的txt
            # if BC25_Data.General_Storage[__index][1] == 4096 and (__index == 2 or
            # __index == 3 or __index == 4 or __index == 5):
            if BC25_Data.General_Storage[__index][1] == 4096:
                path = os.getcwd()
                time_run_now = datetime.datetime.now().strftime('%H-%M-%S (%Y-%m-%d)')
                judge_flag = 1
                if __index == 2:
                    os.chdir(".\\sound\\ok\\time\\DATA")
                elif __index == 3:
                    os.chdir(".\\sound\\ng\\time\\DATA")
                elif __index == 4:
                    os.chdir(".\\acc\\ok\\time\\DATA")
                elif __index == 0:
                    judge_flag = judge(BC25_Data.General_Storage[__index][2][2])
                    if judge_flag == 1:
                        os.chdir(".\\sound\\ng\\time\\DATA")
                    else:
                        os.chdir(".\\sound\\ok\\time\\DATA")
                elif __index == 1:
                    if judge_flag == 1:
                        os.chdir(".\\acc\\ng\\time\\DATA")
                    else:
                        os.chdir(".\\acc\\ok\\time\\DATA")
                else:
                    os.chdir(".\\acc\\ng\\time\\DATA")
                with open('./{} {}.txt'.format(BC25_Data.General_Storage[__index][0], time_run_now), 'w') as f:
                    f.write(BC25_Data.General_Storage[__index][2][1])

                x_axis_data = []
                for i in range(0, BC25_Data.General_Storage[__index][1]):
                    x_axis_data.append(i / 4096)
                y_axis_data = BC25_Data.General_Storage[__index][2][2]

                if __index == 0 or __index == 2 or __index == 3:
                    sounddata = BC25_Data.General_Storage[__index][2][2]
                    sound_data = np.asarray(sounddata, dtype=np.float32)
                    samplerate = 4096
                    write('../Audio/{} {}.wav'.format(BC25_Data.General_Storage[__index][0], time_run_now), samplerate,
                          sound_data)

                # 指定图像上文本的位置
                xt = 0.9
                yt = 1.3
                # 指定图像的大小
                plt.figure(figsize=(16, 16))
                plt.rcParams['font.sans-serif'] = ['SimHei']
                plt.rcParams['axes.unicode_minus'] = False
                # plot中参数的含义分别是横轴值，纵轴值，线的形状，颜色，透明度,线的宽度和标签
                plt.plot(x_axis_data, y_axis_data, color='#4169E1', alpha=0.8, linewidth=1, label='WaveForm')
                # 显示标签，如果不加这句，即使在plot中加了label='一些数字'的参数，最终还是不会显示标签
                plt.xlabel('t')
                plt.ylabel('{}Value'.format(BC25_Data.General_Storage[__index][0]))
                plt.xlim([0, 1])
                plt.grid()
                if __index == 2:
                    # plt.ylim([-1.5, 1.5])
                    plt.text(xt, yt, "正常", fontsize=20, color="green")
                elif __index == 3 or __index == 0 or __index == 1:
                    # plt.ylim([-1.5, 1.5])
                    plt.text(xt, yt, "异常", fontsize=20, color="red")
                plt.savefig('../{} {} {}.jpeg'.format(BC25_Data.General_Storage[__index][0], '_time_', time_run_now))
                plt.clf()
                # plt.close()
                os.chdir(path)

                if __index == 2:
                    os.chdir(".\\sound\\ok\\frequency\\DATA")
                elif __index == 3:
                    os.chdir(".\\sound\\ng\\frequency\\DATA")
                elif __index == 4:
                    os.chdir(".\\acc\\ok\\frequency\\DATA")
                elif __index == 0:
                    if judge_flag == 1:
                        os.chdir(".\\sound\\ng\\frequency\\DATA")
                    else:
                        os.chdir(".\\sound\\ok\\frequency\\DATA")
                elif __index == 1:
                    if judge_flag == 1:
                        os.chdir(".\\acc\\ng\\frequency\\DATA")
                    else:
                        os.chdir(".\\acc\\ok\\frequency\\DATA")
                else:
                    os.chdir(".\\acc\\ng\\frequency\\DATA")
                x_axis_data_f = []
                for i in range(0, BC25_Data.General_Storage[__index][1]):
                    x_axis_data_f.append(i)
                y_axis_data_f0 = np.fft.fft(y_axis_data)
                y_axis_data_f = 20 * np.log(np.abs(y_axis_data_f0))

                xf = 0.45 * 4096
                yf = 180
                # 指定图像的大小
                plt.figure(figsize=(16, 16))
                plt.rcParams['axes.unicode_minus'] = False
                plt.rcParams['font.sans-serif'] = ['SimHei']
                # plot中参数的含义分别是横轴值，纵轴值，线的形状，颜色，透明度,线的宽度和标签
                plt.plot(x_axis_data_f, y_axis_data_f, color='#4169E1', alpha=0.8, linewidth=1, label='WaveForm')
                # 显示标签，如果不加这句，即使在plot中加了label='一些数字'的参数，最终还是不会显示标签
                plt.xlabel('frequceny/Hz')
                plt.ylabel('{}FFT_Value'.format(BC25_Data.General_Storage[__index][0]))
                plt.xlim([0, 2048])
                plt.grid()
                if __index == 2:
                    # plt.ylim([-100, 200])
                    plt.text(xf, yf, "正常", fontsize=20, color="green")
                elif __index == 3:
                    # plt.ylim([-100, 200])
                    plt.text(xf, yf, "异常", fontsize=20, color="red")
                plt.savefig(
                    '../{} {} {}.jpeg'.format(BC25_Data.General_Storage[__index][0], '_frequency_', time_run_now))
                plt.clf()
                # plt.close()
                os.chdir(path)

            else:
                path = os.getcwd()
                time_run_now = datetime.datetime.now().strftime('%H-%M-%S (%Y-%m-%d)')
                if __index == 0:
                    os.chdir(".\\sound\\keep\\DATA")
                else:
                    os.chdir(".\\acc\\keep\\DATA")
                with open('./{} {}.txt'.format(BC25_Data.General_Storage[__index][0], time_run_now), 'w') as f:
                    f.write(BC25_Data.General_Storage[__index][2][1])
                x_axis_data = []
                for i in range(0, BC25_Data.General_Storage[__index][1]):
                    x_axis_data.append(i)
                y_axis_data = BC25_Data.General_Storage[__index][2][2]

                if __index == 0:
                    sounddata = BC25_Data.General_Storage[__index][2][2]
                    sound_data = np.asarray(sounddata, dtype=np.float32)
                    samplerate = 4096
                    write('../Audio/{} {}.wav'.format(BC25_Data.General_Storage[__index][0], time_run_now), samplerate,
                          sound_data)

                plt.rcParams['axes.unicode_minus'] = False  # 正常显示负号
                plt.rcParams['font.sans-serif'] = ['SimHei']
                plt.plot(x_axis_data, y_axis_data, color='#4169E1', alpha=0.8, linewidth=1, label='WaveForm')
                # 显示标签，如果不加这句，即使在plot中加了label='一些数字'的参数，最终还是不会显示标签
                plt.xlabel('t')
                plt.grid()
                plt.ylabel('{}Value'.format(BC25_Data.General_Storage[__index][0]))
                plt.savefig('../{} {}.jpeg'.format(BC25_Data.General_Storage[__index][0], time_run_now))
                plt.clf()
                # plt.close()
                os.chdir(path)

            self.draw_pic_flag = 0
            BC25_Data.reset_all()
            # 通知画图
            self.draw_pic_flag = 1 + __index
            receive_finished_flag = 0

        self.MQTT_Data.BC25_Data = BC25_Data
        self.MQTT_Data.STM32Data = STM32Data
        self.MQTT_Data = MQTT_Data

class Service:
    device_ID_pool_lens = 20  # 最坏情况的设备列表长度，限定为最多50台设备同时运行20秒
    device_ID_pool_len = 5
    device_ID_pools = [None for i in range(device_ID_pool_lens)]

    def __init__(self, service_id, receive_topic, qos):
        self.client = mqtt.Client(service_id, clean_session=True, userdata=None, transport="tcp")
        self.client.on_connect = self.Service_on_connect
        self.client.on_message = self.Service_on_message
        self.Receive_topic = receive_topic
        self.qos = qos
        self.Subscriber_Pool = {}
        self.device_ID_pool = [None for i1 in range(Service.device_ID_pool_len)]
        self.Client_td_Pool = {}
        # self.device_ID_offpool_save = []
        self.SuperviserThread()
        # self.device_ID_offpool = []

    def connect(self, host: str, port: int, keepalive: int):
        self.client.connect(host, port, keepalive)

    def disconnect(self):
        self.client.disconnect()

    def subscribe(self, topic):
        self.client.subscribe(topic, self.qos)

    def loop_forever(self):
        self.client.loop_forever()

    # 连接成功回调
    def Service_on_connect(self, client, userdata, flags, rc):
        print('Service: Connected with result code ' + str(rc))
        self.client.subscribe(self.Receive_topic, self.qos)
    
    # @staticmethod
    def SuperviserThread(self):
        supervisior_thread = threading.Thread(target=self.Supervise)
        supervisior_thread.setDaemon(True)
        supervisior_thread.start()

    def Supervise(self):
        device_ID_pool_pass = self.device_ID_pool
        while True:
            for idon in self.device_ID_pool:
                if idon not in device_ID_pool_pass and idon:
                    print(str(idon) + ": Client start!")
                    self.client_start(idon)
                    # print(str(idon)+": Client start!")
            for idoff in device_ID_pool_pass:
                if idoff not in self.device_ID_pool and idoff:
                    print(str(idoff) + ": Client stop!")
                    self.client_stop(self.Client_td_Pool[idoff], idoff)
                    # print(str(idoff)+": Client stop after!")
                    # Service.device_ID_offpool.append(id)
            # Self.device_ID_offpool_save = Service.device_ID_offpool
            device_ID_pool_pass = self.device_ID_pool
            time.sleep(0.5)
            # Service.device_ID_offpool.clear()
    
    # 创建客户端线程
    def client_start(self, device_id):
        if device_id:
            client_thread = threading.Thread(target=self.ClientThread(device_id), name=str(device_id))
            self.Client_td_Pool[str(device_id)] = client_thread
            client_thread.setDaemon(True)
            client_thread.start()
    
    # 根据需求下线并关闭客户端线程
    def client_stop(self, Client_thread: threading.Thread, device_id):
        if device_id:
            self.Subscriber_Pool[str(device_id)].client.disconnect()
            self.Subscriber_Pool[str(device_id)].client.loop_stop()
            Client_thread.join(0.5)
          

    #创建客户端
    def ClientThread(self, device_id):
        global IP
        global path_root
        topic = "/Sensors/{}".format(device_id)
        Client_savepath = '{}{}{}'.format(path_root, '\\', device_id)
        if(os.path.exists(Client_savepath) == 0):
            os.makedirs(Client_savepath)
        os.chdir(Client_savepath)
        process_init()

        Sub = Subscriber('Client'+str(device_id), topic, self.qos, device_id)
        # Sub.client.message_callback_add("/Sensors/{}".format(device_id), Sub.Listen_CB)
        self.Subscriber_Pool[device_id] = Sub
        Sub.client.connect(IP, 1883, 60)
        Sub.client.message_callback_add("/Sensors/{}".format(device_id), Sub.Listen_CB)
        Sub.client.loop_start()
        # Sub.client.loop_forever()

    def Service_on_message(self, client, userdata, msg):
        # global flag
        tmp = msg.payload
        device_id = tmp.decode()
        # flag = 0
        # if device_id not in self.device_ID_pool:
        #    flag = 1
        for cont in range(Service.device_ID_pool_lens - 1):
            Service.device_ID_pools[cont] = Service.device_ID_pools[cont + 1]
        Service.device_ID_pools[Service.device_ID_pool_lens - 1] = device_id
        self.device_ID_pool = list(set(Service.device_ID_pools))
        # print(Service.device_ID_pools)
        # print(self.device_ID_pool)
        # print(self.device_ID_offpool_save)


S = Service(service_id, topic, qos=0)
S.client.connect(IP, 1883, 60)
S.loop_forever()