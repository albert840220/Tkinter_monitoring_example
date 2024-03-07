import requests
import matplotlib.pyplot as plt
import matplotlib.animation as animation
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib import style
import tkinter as tk
import tkinter.ttk as ttk
from tkinter import messagebox
import time
import threading
import serial
import struct
import datetime
import csv

BAUD_RATES = 19200
COMPORT_LIST = ["60666", "60667", "60668", "60669"]

# threading多線程
class MyThread(threading.Thread):
    def __init__(self, func, *args):
        super().__init__()
        self.func = func
        self.args = args
        #self.setDaemon(True) #主線程結束後，其它子線程跟著結束。
        self.start()  # 在这里开始

    def run(self):
        self.func(*self.args)

# 判定modbus的讀法
def bowo(modbus, bo = 'l', wo = 4):
    if bo == 'l' and wo == 4  :#int情況解碼
        modbus = modbus[2:4] + modbus[0:2]
        return modbus
    if bo == 'b' and wo == 'l':
        if len(modbus) == 8:
            modbus = modbus[4:8] + modbus[0:4]
        else:
            modbus = modbus
        return modbus
    if bo == 'l' and wo == 'l':
        modbus = modbus[6:8] + modbus[4:6] + modbus[2:4] + modbus[0:2]
        return modbus
    if bo == 'l' and wo == 'b':
        modbus = modbus[2:4] + modbus[0:2] + modbus[6:8] + modbus[4:6]
        return modbus
    if bo == 'h' and wo == 'h':  #拿掉HEX的0x and 'b' ,'l'
        if len(modbus) == 10:
            modbus = modbus[6:10] + modbus[2:6]
            return modbus
        else : return  modbus[2:6]

#計算CRC
def calc_crc(string):
    data = bytes.fromhex(string)  #hex轉bytearray陣列,值其實不變
    crc = 0xFFFF
    for pos in data:
        crc ^= pos #crc
        for i in range(8):
            if crc & 1:
                crc >>= 1
                crc ^= 0xA001
            else:
                crc >>= 1
    return hex(((crc & 0xff) << 8) + (crc >> 8))  #做word little調換

# 不同資料型態的解碼
slope_1 = 0
offset_1 = 0

def addr_type_tex(raw, ad0, ad1, typ, strr=0, lab=0):
    global add,temp_mv_convert_ph,slope,offset,total_list
    addr = raw[ad0:ad1]#取要抓取的地址，是歷史資料不是int，就l,l。
    if strr == 0 and typ != 'int':
        data = bowo(addr, 'l', 'l')
    elif typ == 'int' :
        if strr == 'methed':
            data = bowo(addr)
        else : data = addr
        if len(bytes.fromhex(data)) == 2:#資料像int一樣2bytes在計算
            tag = int(data,16)
            # if lab == value_SensorDays:
            #     lab.set(f'{tag} Day')
            # if lab == value_SensorHealth:
            #     lab.set(f'{tag} %')
            if lab == 0 and strr == 'methed':
                return tag
                lab.set(tag)
    else:    
        data = bowo(addr, 'b', 'l') #即時資料是b,l.

    if len(bytes.fromhex(data)) == 4:
        if typ == 'time':
            tag = int(data,16)
            tag = datetime.datetime.fromtimestamp(tag+946656000)
            if strr == 0:
                return tag
                lab.set(tag)
            else:
                t = str(tag)
                tag = t[0:10]#即時連線只顯示日期
                lab.set(tag)
        elif typ == 'float':
            tag = struct.unpack('!f', bytes.fromhex(data))[0]
            tag = round(tag, 2)
            # if lab == value_ph:
            #     if 0 < tag and tag < 14 and tag != 0:
            #         former_ph = tag
            #         lab.set(tag)
            #     else:
            #         lab.set(former_ph)
            # if lab == value_temp:
            #     if 0 < tag and tag<100 and tag != 0:
            #         former_temp = tag
            #         lab.set(tag)
            #     else:
            #         lab.set(former_temp)
            #取slope和offset的值
            # if lab == value_Slope_mV_pH:
            #     slope = tag
            #     lab.set(f'{tag} mV/pH')
            # if lab == value_Offset_mV:
            #     offset = tag
            #     lab.set(f'{tag} mV')
            # #即時圖表的Spec判定
            # if lab == value_mV:
            #     if -414.14 < tag and tag < 414.14 and tag != 0 :
            #         temp_mv_convert_ph = round(7+(tag-offset)/(slope),2)
            #         former_mV = tag 
            #         lab.set(tag)
            #     else:
            #         lab.set(former_mV)
            # if lab == value_Act_mv:
            #     if tag != 0:
            #         former_Act_mv = tag
            #         lab.set(f'{tag} mV')
            #     else:
            #         lab.set(f'{former_Act_mv} mV')
            # if lab == value_Ref_mv:
            #     if tag != 0:
            #         former_Ref_mv = tag
            #         lab.set(f'{tag} mV')
            #     else:
            #         lab.set(f'{former_Ref_mv} mV')
            # if lab == value_Temperature_Ohms:
            #     if tag != 0:
            #         former_Temperature_Ohms = tag
            #         lab.set(f'{tag} Ω')
            #     else:
            #         lab.set(f'{former_Temperature_Ohms} Ω')
            if lab == 0 and strr == 0:
                return tag
                lab.set(tag)        
    elif typ == 'ascii':
        try:
            tag = bytes.fromhex(data)
            tag = tag.decode()
            if lab == 0 and strr == 0:
                return tag
        except:
            pass
        lab.set(tag)
def addr_type_tex_1(raw, ad0, ad1, typ, strr=0, lab=0):
    global add,temp_mv_convert_ph_1,slope_1,offset_1
    global former_ph_1,former_mV_1,former_temp_1,former_Act_mv_1,former_Ref_mv_1,former_Temperature_Ohms_1
    addr = raw[ad0:ad1]#取要抓取的地址，是歷史資料不是int，就l,l。
    if strr == 0 and typ != 'int':
        data = bowo(addr, 'l', 'l')
    elif typ == 'int' :
        if strr == 'methed':
            data = bowo(addr)
        else : data = addr
        if len(bytes.fromhex(data)) == 2:#資料像int一樣2bytes在計算
            tag = int(data,16)
            if lab == value_SensorDays_1:
                lab.set(f'{tag} Day')
            if lab == value_SensorHealth_1:
                lab.set(f'{tag} %')
            if lab == 0 and strr == 'methed':
                return tag
                lab.set(tag)
    else:    
        data = bowo(addr, 'b', 'l') #即時資料是b,l.

    if len(bytes.fromhex(data)) == 4:
        if typ == 'time':
            tag = int(data,16)
            tag = datetime.datetime.fromtimestamp(tag+946656000)
            if strr == 0:
                return tag
                lab.set(tag)
            else:
                t = str(tag)
                tag = t[0:10]#即時連線只顯示日期
                lab.set(tag)
        elif typ == 'float':
            tag = struct.unpack('!f', bytes.fromhex(data))[0]
            if lab ==value_ph_1:
                tag = '%.2f'% tag
            if lab ==value_temp_1:
                tag = '%.1f'% tag
            if lab == value_mV_1:
                tag = '%.3f'% tag
                temp_mv_convert_ph_1 = '%.2f'% (7+(float(tag)-float(offset_1))/float(slope_1))
            
            if lab == 0 and strr == 0:
                return tag
                lab.set(tag)      
            lab.set(tag)
            #取slope和offset的值
            if lab == value_Slope_mV_pH_1:
                tag = '%.2f'% tag
                slope_1 = tag
                lab.set(f'{tag} mV/pH')
            if lab == value_Offset_mV_1:
                tag = '%.2f'% tag
                offset_1 = tag
                lab.set(f'{tag} mV')
            #即時圖表的Spec判定
            if lab == value_Act_mv_1:
                tag = '%.3f'% tag
                lab.set(f'{tag} mV')
            if lab == value_Ref_mv_1:
                tag = '%.3f'% tag
                lab.set(f'{tag} mV')
            if lab == value_Temperature_Ohms_1:
                tag = '%.1f'% tag
                lab.set(f'{tag} Ω')
    elif typ == 'ascii':
        try:
            tag = bytes.fromhex(data)
            tag = tag.decode()
            if lab == 0 and strr == 0:
                return tag
        except:
            pass
        lab.set(tag)
# 不同資料型態的解碼
slope_2 = 0
offset_2 = 0
former_ph_2 = 0
former_mV_2 = 0
former_temp_2 = 0
former_Act_mv_2 = 0
former_Ref_mv_2 = 0
former_Temperature_Ohms_2 = 0
def addr_type_tex_2(raw, ad0, ad1, typ, strr=0, lab=0):
    global add,temp_mv_convert_ph_2,slope_2,offset_2
    global former_ph_2,former_mV_2,former_temp_2,former_Act_mv_2,former_Ref_mv_2,former_Temperature_Ohms_2
    addr = raw[ad0:ad1]#取要抓取的地址，是歷史資料不是int，就l,l。
    if strr == 0 and typ != 'int':
        data = bowo(addr, 'l', 'l')
    elif typ == 'int' :
        if strr == 'methed':
            data = bowo(addr)
        else : data = addr
        if len(bytes.fromhex(data)) == 2:#資料像int一樣2bytes在計算
            tag = int(data,16)
            if lab == value_SensorDays_2:
                lab.set(f'{tag} Day')
            if lab == value_SensorHealth_2:
                lab.set(f'{tag} %')
            if lab == 0 and strr == 'methed':
                return tag
                lab.set(tag)
    else:    
        data = bowo(addr, 'b', 'l') #即時資料是b,l.

    if len(bytes.fromhex(data)) == 4:
        if typ == 'time':
            tag = int(data,16)
            tag = datetime.datetime.fromtimestamp(tag+946656000)
            if strr == 0:
                return tag
                lab.set(tag)
            else:
                t = str(tag)
                tag = t[0:10]#即時連線只顯示日期
                lab.set(tag)
        elif typ == 'float':
            tag = struct.unpack('!f', bytes.fromhex(data))[0]
            if lab ==value_ph_2:
                tag = '%.2f'% tag
            if lab ==value_temp_2:
                tag = '%.1f'% tag
            if lab == value_mV_2:
                tag = '%.3f'% tag
                temp_mv_convert_ph_2 = '%.2f'% (7+(float(tag)-float(offset_2))/float(slope_2))
            lab.set(tag)
            #取slope和offset的值
            if lab == value_Slope_mV_pH_2:
                tag = '%.2f'% tag
                slope_2 = tag
                lab.set(f'{tag} mV/pH')
            if lab == value_Offset_mV_2:
                tag = '%.2f'% tag
                offset_2 = tag
                lab.set(f'{tag} mV')
            if lab == 0 and strr == 0:
                return tag
                lab.set(tag)      
            #即時圖表的Spec判定
            if lab == value_Act_mv_2:
                tag = '%.3f'% tag
                lab.set(f'{tag} mV')
            if lab == value_Ref_mv_2:
                tag = '%.3f'% tag
                lab.set(f'{tag} mV')
            if lab == value_Temperature_Ohms_2:
                tag = '%.1f'% tag
                lab.set(f'{tag} Ω') 
    elif typ == 'ascii':
        try:
            tag = bytes.fromhex(data)
            tag = tag.decode()
            if lab == 0 and strr == 0:
                return tag
        except:
            pass
        lab.set(tag)

#即時顯示

#即時顯示讀值
def serial_try_1():
    # COM_PORT_1 = var_1.get()
    global BAUD_RATES,temp_mv_convert_ph_1,switch_function_1,ser_1
    # ser_1 = serial.Serial(COMPORT_LIST[1], BAUD_RATES, timeout=0.5)
    ser_1 = serial.serial_for_url('loop://', timeout=1)
    global text
    # r1_code = bytes.fromhex('F7 03 00 00 00 37 10 8A')
    # ser_1.write(r1_code)
    ser_1.write(b"is connect")
    data_raw = ser_1.readline()  # 讀取一行
    print(data_raw)
    # raw_ = data_raw.hex()
    # if len(raw_) != 230:
    #                 while True:        
    #                     msg = ser_1.readline()
    #                     raw_ = f'{raw_}{msg.hex()}'
    #                     if len(raw_) == 230:
    #                         # print(raw_)
    #                         break
    # #time.sleep(0.5)
    # addr_type_tex_1(raw_, 130, 162, 'ascii', 'Device_model_name', value_Device_model_name_1)
    # addr_type_tex_1(raw_, 162, 186, 'ascii', 'DeviceName', value_DeviceName_1)
    # addr_type_tex_1(raw_, 186, 210, 'ascii', 'SerialNumberString', value_SerialNumberString_1)

    # r2_code = bytes.fromhex('F7 03 00 37 00 36 60 84')
    # ser_1.write(r2_code)
    # data_raw = ser_1.readline()  # 讀取一行
    # raw_hex = data_raw.hex()
    # if len(raw_hex) != 226:
    #                 while True:        
    #                     msg = ser_1.readline()
    #                     raw_hex = f'{raw_hex}{msg.hex()}'
    #                     if len(raw_hex) == 226 :
    #                         # print(raw_hex)
    #                         break
    # #time.sleep(0.5)
    # addr_type_tex_1(raw_hex, 10, 42, 'ascii', 'SensorModel', value_SensorModel_1)
    # addr_type_tex_1(raw_hex, 42, 66, 'ascii', 'SensorSNString', value_SensorSNString_1)
    # addr_type_tex_1(raw_hex, 66, 74, 'time', 'FactoryCalDate', value_FactoryCalDate_1)
    # addr_type_tex_1(raw_hex, 74, 82, 'time', 'FirstCalDate', value_FirstCalDate_1)
    # addr_type_tex_1(raw_hex, 82, 90, 'time', 'LastCalDate', value_LastCalDate_1)
    # addr_type_tex_1(raw_hex, 98, 102, 'int', 'SensorDays', value_SensorDays_1)#校正完後使用天數
    # addr_type_tex_1(raw_hex, 102, 110, 'float', 'Slope_mV_pH', value_Slope_mV_pH_1)
    # addr_type_tex_1(raw_hex, 110, 118, 'float', 'Offset_mV', value_Offset_mV_1)
    # addr_type_tex_1(raw_hex, 118, 122, 'int', 'SensorHealth', value_SensorHealth_1)
    # time.sleep(2)
    # instant_display_1()

def serial_try_2():
    COM_PORT_2 = var_2.get()
    global BAUD_RATES,temp_mv_convert_ph_2,switch_function_2,ser_2
    ser_2 = serial.Serial(COM_PORT_2, BAUD_RATES, timeout=0.5)
    global text
    r1_code = bytes.fromhex('F7 03 00 00 00 37 10 8A')
    ser_2.write(r1_code)
    data_raw = ser_2.readline()  # 讀取一行
    raw_ = data_raw.hex()
    if len(raw_) != 230:
                    while True:        
                        msg = ser_2.readline()
                        raw_ = f'{raw_}{msg.hex()}'
                        if len(raw_) == 230:
                            # print(raw_)
                            break
    #time.sleep(0.5)
    addr_type_tex_2(raw_, 130, 162, 'ascii', 'Device_model_name', value_Device_model_name_2)
    addr_type_tex_2(raw_, 162, 186, 'ascii', 'DeviceName', value_DeviceName_2)
    addr_type_tex_2(raw_, 186, 210, 'ascii', 'SerialNumberString', value_SerialNumberString_2)

    r2_code = bytes.fromhex('F7 03 00 37 00 36 60 84')
    ser_2.write(r2_code)
    data_raw = ser_2.readline()  # 讀取一行
    raw_hex = data_raw.hex()
    if len(raw_hex) != 226:
                    while True:        
                        msg = ser_2.readline()
                        raw_hex = f'{raw_hex}{msg.hex()}'
                        if len(raw_hex) == 226 :
                            # print(raw_hex)
                            break
    #time.sleep(0.5)
    addr_type_tex_2(raw_hex, 10, 42, 'ascii', 'SensorModel', value_SensorModel_2)
    addr_type_tex_2(raw_hex, 42, 66, 'ascii', 'SensorSNString', value_SensorSNString_2)
    addr_type_tex_2(raw_hex, 66, 74, 'time', 'FactoryCalDate', value_FactoryCalDate_2)
    addr_type_tex_2(raw_hex, 74, 82, 'time', 'FirstCalDate', value_FirstCalDate_2)
    addr_type_tex_2(raw_hex, 82, 90, 'time', 'LastCalDate', value_LastCalDate_2)
    addr_type_tex_2(raw_hex, 98, 102, 'int', 'SensorDays', value_SensorDays_2)#校正完後使用天數
    addr_type_tex_2(raw_hex, 102, 110, 'float', 'Slope_mV_pH', value_Slope_mV_pH_2)
    addr_type_tex_2(raw_hex, 110, 118, 'float', 'Offset_mV', value_Offset_mV_2)
    addr_type_tex_2(raw_hex, 118, 122, 'int', 'SensorHealth', value_SensorHealth_2)
    time.sleep(2)
    instant_display_2()
def close():
    global ser, temp_mv_convert_ph
    temp_mv_convert_ph = 0
    ser.close()
def close_1():
    global ser_1, temp_mv_convert_ph_1
    btn_ok_1['state'] = tk.DISABLED
    temp_mv_convert_ph_1 = 0
    ser_1.close()
    remind_content_1.set('')

def close_2():
    global ser_2, temp_mv_convert_ph_2
    btn_ok_2['state'] = tk.DISABLED
    temp_mv_convert_ph_2 = 0
    ser_2.close()
    remind_content_2.set('')

# 顯示可用的COM Port
def serial_ports():
    ports = ['COM%s' % (i + 1) for i in range(256)]#列出所有1-256 COM ports
    result = []
    for port in ports:
        try:
            s = serial.Serial(port)
            s.close()
            result.append(port)
        except (OSError, serial.SerialException):
            pass
    return result
#寫現在時間的程式碼
stamp = int(time.time()-946656000)
stamp_hex = hex(stamp)#轉成HEX
stamp_mod = bowo(stamp_hex, 'h', 'h')
now_mod = 'f71026fc000204'+str(stamp_mod)
now_crc = calc_crc(now_mod)
now = now_mod + bowo(now_crc, 'h', 'h')

code_list = [
    {'request': 'F7 08 00 00 55 55 0B F2',
      'response':'F7 08 00 00 55 55 0B F2'},
    {'request': 'F7 03 27 08 00 05 1A 29',
      'response':'F7 03 0A'},  
#轉接頭號碼 No.1#'F7 03 0A A1 00 19 06 00 25 00 28 00 00 50 6F'  
                #
                #'F7 03 0A 00 00 70 4F 00 01 00 28 00 00 69 A9'
                #'F7 03 0A A1 00 19 06 00 24 00 28 00 00 6d af'
    {'request': 'F7 06 26 E7 00 00 26 23',
      'response':'F7 06 26 E7 00 00 26 23'},
    {'request': 'F7 06 26 E3 00 0A E7 E5',
      'response':'F7 06 26 E3 00 0A E7 E5'},
    {'request': now,#現在時間
      'response':'F7 10 26 FC 00 02 9E 26'},
    {'request': 'F7 11 87 8C',
      'response':'F7 11 0C D5 FF 01 00 00 28'}, ##
    {'request': 'F7 06 26 E4 00 00 D6 23',
      'response':'F7 06 26 E4 00 00 D6 23'},
    {'request': 'F7 06 26 E6 00 01 B6 23',
      'response':'F7 06 26 E6 00 01 B6 23'},
    {'request': 'F7 06 26 E4 00 01 17 E3',
      'response':'F7 06 26 E4 00 01 17 E3'},
    {'request': 'F7 03 26 E4 00 01 DB E3',
      'response':'F7 03 02 00 03 30 50'},
    {'request': 'F7 03 26 E5 00 01 8A 23',
      'response':'F7 03 02'},#'F7 03 02 18 DA FB CA'},
    {'request': 'F7 14 07 06 00 01 00 00 00 05 E1 3B',
      'response':'F7 14 0C 0B 06'},
  # 轉接頭號碼   #'F7 14 0C 0B 06 06 00 B6 0F 01 00 00 00 28 00 82 E2'
                #'f7140c0b067f9fb60f010000002800bd10'
                #'f7 14 0c 0b 06 7f bf b6 0f 01 00 00 00 28 00 24 d1'
    { 'request': 'F7 06 26 E4 00 00 D6 23' ,
      'response':'F7 06 26 E4 00 00 D6 23' },
    {'request': 'F7 06 00 92 00 0A BC B6',
      'response':'F7 06 00 92 00 0A BC B6' },
    { 'request': 'F7 06 00 92 00 1D FC B8',
      'response':'F7 06 00 92 00 1D FC B8'}]

command_list = [
    {'request': 'F7 06 00 92 00 10 3D 7D',
      'response':'F7 06 00 92 00 10 3D 7D',
      'addr':'001d0017',
      'action': 'put point 1'},
    { 'request': 'F7 06 00 92 00 14 3C BE',
      'response':'F7 06 00 92 00 14 3C BE',
      'addr':'00100018',
      'action': ''},
    {'request': 'F7 06 00 92 00 14 3C BE',
      'response':'F7 06 00 92 00 14 3C BE',
      'addr':'0014001a',
      'action': '' },
    {'request': 'F7 06 00 92 00 16 BD 7F',
      'response':'F7 06 00 92 00 16 BD 7F',
      'addr':'0014001a',
      'action': 'wait1' },
    {'request': 'F7 06 00 92 00 11 FC BD',
      'response':'F7 06 00 92 00 11 FC BD',
      'addr':'0016001b',
      'action': '' },
    {'request': 'F7 06 00 92 00 11 FC BD',
      'response':'F7 06 00 92 00 11 FC BD',
      'addr':'0011001b',
      'action': '' },
    {'request': 'F7 06 00 92 00 11 FC BD',
      'response':'F7 06 00 92 00 11 FC BD',
      'addr':'00110018',
      'action': '' },
    {'request': 'F7 06 00 92 00 15 FD 7E',
      'response':'F7 06 00 92 00 15 FD 7E',
      'addr':'00110018',
      'action': 'complete 1' },
    {'request': 'F7 10 00 8E 00 01 02 00 01 56 DA',
      'response':'F7 10 00 8E 00 01 75 74',
      'addr':'0015001d',
      'action': '' },
    {'request': 'F7 06 00 92 00 19 FD 7B',
      'response':'F7 06 00 92 00 19 FD 7B',
      'addr':'0015001d',
      'action': ''},
    {'request': 'F7 06 00 92 00 14 3C BE',
      'response':'F7 06 00 92 00 14 3C BE',
      'addr':'00190018',
      'action':'put point 2'},
    {'request': 'F7 06 00 92 00 16 BD 7F',
      'response':'F7 06 00 92 00 16 BD 7F',
      'addr':'0014001a',
      'action': 'wait2' },
    {'request': 'F7 06 00 92 00 12 BC BC',
      'response':'F7 06 00 92 00 12 BC BC',
      'addr':'0016001e',
      'action': 'complete 2'}]

history_list = [{'request': 'F7 06 26 E4 00 00 D6 23' ,
                'response':'F7 06 26 E4 00 00 D6 23 '},
                {'request':'F7 06 26 E6 00 1A F6 28 ',
                'response':'F7 06 26 E6 00 1A F6 28 '},
                {'request':'F7 06 26 E4 00 01 17 E3 ',
                'response':'F7 06 26 E4 00 01 17 E3 '},
                {'request':'F7 03 26 E4 00 01 DB E3 ',
                'response':'F7 03 02 00 03 30 50 '},
                {'request':'F7 03 26 E5 00 01 8A 23' ,
                'response':'F7 03 02 08 00 77 91 '}]

read_history = ['F7 14 07 06 00 1A 00 00 00 34 44 ED' , 
                'F7 14 07 06 00 1A 00 34 00 34 05 23' , 
                'F7 14 07 06 00 1A 00 68 00 34 C5 31' ,
                'F7 14 07 06 00 1A 00 9C 00 34 84 C3' ,
                'F7 14 07 06 00 1A 00 D0 00 34 45 14' ,
                'F7 14 07 06 00 1A 01 04 00 34 04 D0' ,
                'F7 14 07 06 00 1A 01 38 00 34 C4 DC' ,
                'F7 14 07 06 00 1A 01 6C 00 34 85 0C' ,
                'F7 14 07 06 00 1A 01 A0 00 34 45 33' ,
                'F7 14 07 06 00 1A 01 D4 00 34 05 29' ,
                'F7 14 07 06 00 1A 02 08 00 34 C4 97' ,
                'F7 14 07 06 00 1A 02 3C 00 34 85 59' ,
                'F7 14 07 06 00 1A 02 70 00 34 44 8E' ,
                'F7 14 07 06 00 1A 02 A4 00 34 04 B6' ,
                'F7 14 07 06 00 1A 02 D8 00 34 C5 6E' ,
                'F7 14 07 06 00 1A 03 0C 00 34 84 AA' ,
                'F7 14 07 06 00 1A 03 40 00 34 45 7D' ,
                'F7 14 07 06 00 1A 03 74 00 34 04 B3' ,
                'F7 14 07 06 00 1A 03 A8 00 34 C5 49' ,
                'F7 14 07 06 00 1A 03 DC 00 34 85 53' ,
                'F7 14 07 06 00 1A 04 10 00 34 44 18' ,
                'F7 14 07 06 00 1A 04 44 00 34 05 C8' ,
                'F7 14 07 06 00 1A 04 78 00 34 C5 C4' ,
                'F7 14 07 06 00 1A 04 AC 00 34 85 FC' ,
                'F7 14 07 06 00 1A 04 E0 00 34 44 2B' ,
                'F7 14 07 06 00 1A 05 14 00 34 04 25' ,
                'F7 14 07 06 00 1A 05 48 00 34 C4 37' ,
                'F7 14 07 06 00 1A 05 7C 00 34 85 F9' ,
                'F7 14 07 06 00 1A 05 B0 00 34 45 C6' ,
                'F7 14 07 06 00 1A 05 E4 00 34 04 16' ,
                'F7 14 07 06 00 1A 06 18 00 34 C4 62' ,
                'F7 14 07 06 00 1A 06 4C 00 34 85 B2' ,
                'F7 14 07 06 00 1A 06 80 00 34 45 8D' ,
                'F7 14 07 06 00 1A 06 B4 00 34 04 43' ,
                'F7 14 07 06 00 1A 06 E8 00 34 C4 51' ,
                'F7 14 07 06 00 1A 07 1C 00 34 84 5F' ,
                'F7 14 07 06 00 1A 07 50 00 34 45 88' ,
                'F7 14 07 06 00 1A 07 84 00 34 05 B0' ,
                'F7 14 07 06 00 1A 07 B8 00 34 C5 BC' ,
                'F7 14 07 06 00 1A 07 EC 00 14 85 B4' ]
batch_list = []
total_list = []
def history_decode(s):
    global batch_list 
    his_list = []
    if 'ffffffffffffffff' in s:
        return his_list
    timeArray = addr_type_tex(s, 0, 8, 'time')
    t = str(timeArray)
    method = addr_type_tex(s, 8, 12, 'int','methed')
    slope = addr_type_tex(s, 12, 20, 'float')
    Offset = addr_type_tex(s,20, 28, 'float')
    Temp  = addr_type_tex(s, 28, 36, 'float')
    Act_Z = addr_type_tex(s, 36, 44, 'float')
    Ref_Z = addr_type_tex(s, 44, 52, 'float')
    Res_time=addr_type_tex(s,52, 60, 'float')
    Buf_A = addr_type_tex(s, 60, 68, 'float')
    Buf_B = addr_type_tex(s, 68, 76, 'float')
    Dev_A = addr_type_tex(s, 76, 84, 'float')
    Dev_B = addr_type_tex(s, 84, 92, 'float')
    Pot_A = addr_type_tex(s, 92,100, 'float')
    Pot_B = addr_type_tex(s,100,108, 'float')
    Temp_A= addr_type_tex(s,108,116, 'float')
    Temp_B= addr_type_tex(s,116,124, 'float')
    Res1_A= addr_type_tex(s,124,132, 'float')
    Res1_B= addr_type_tex(s,132,140, 'float')
    Res2_A= addr_type_tex(s,140,148, 'float')
    Res2_B= addr_type_tex(s,148,156, 'float')
    item_list = [slope, Offset, Temp, Act_Z, Ref_Z,
                 Res_time, Buf_A ,Buf_B,Dev_A,Dev_B,Pot_A,Pot_B,Temp_A,Temp_B,
                 Res1_A, Res1_B, Res2_A, Res2_B]#個數值存成陣列
    his_list.append(t[0:10])
    his_list.append(t[11:19])
    his_list.append(method)
    batch_list.append(timeArray)
    if method == 0:
        batch_list.append('Auto 1 Point')
    elif method == 1:
        batch_list.append('Auto 2 Points')
    elif method == 2:
        batch_list.append('Manual 1 Point')
    elif method == 5:
        batch_list.append('External 2 Points')
    for item in item_list:
        his_list.append(item)
        batch_list.append(item)
    return his_list
#歷史紀錄時間產生變數，給下面函式檔名用。
now_time = datetime.datetime.now()
time_name = now_time.strftime('%Y%m%d%H%M')

def history():
    time.sleep(2)
    COM_PORT = var_log.get()
    global BAUD_RATES,ser,cache_result,batch_list,sortedList
    cache_result = '0'
    ser = serial.Serial(COM_PORT, BAUD_RATES, timeout=0.2)

    for history_code in history_list:
        write_code = bytes.fromhex(history_code['request'])
        check_code = history_code['response'].replace(' ', '').lower()#空格去除
        ser.write(write_code)
        msg_cache = ''#抓取的資料
        while True:
            if ser.in_waiting:
                msg = ser.readline()#讀取資料

                if msg_cache == '':
                    decode_msg = msg.hex()
                else:
                    decode_msg = f'{msg_cache}{msg.hex()}'

                print(f'check_code: {check_code}\ndecode_msg: {decode_msg}')
                if decode_msg == check_code:
                    msg_cache = ''
                    break
                else:
                    msg_cache = decode_msg                
        print('one history_code request done.')
        print('-' * 100)
    print('loop request done.')
    print('-' * 100) 

    with open(f'History_{time_name}.csv', 'w', newline='') as csvfile:

            writer = csv.writer(csvfile)
            csv_list = []
            total_list = []
            global sub_list
            i = 0; save = 76; data = ''
            writer.writerow(['Date' ,'Time' ,'Method' ,'Slope' ,'Offset',	
                             'Temp' ,'Act_Z','Ref_Z','Res_time','Buf_A' ,
                             'Buf_B','Dev_A','Dev_B','Pot_A','Pot_B',
                    'Temp_A','Temp_B','Res1_A','Res1_B','Res2_A','Res2_B'])
            num = 0
            for readhis_code in read_history:
                i = i + 1
                if i == 40 : break
                write_code = bytes.fromhex(readhis_code)
                ser.write(write_code)
                msg = ser.readline()
                raw_hex = msg.hex()
                if 'f'*182 in raw_hex:break
                if len(raw_hex) != 222:
                    while True:        
                        msg = ser.readline()
                        raw_hex = f'{raw_hex}{msg.hex()}'
                        if len(raw_hex) == 222:
                            break

                print(f'The {i}th raw: \n{raw_hex}')
                if readhis_code == 'F7 14 07 06 00 1A 00 00 00 34 44 ED':
                    continue
                elif readhis_code == 'F7 14 07 06 00 1A 00 34 00 34 05 23':
                    data = raw_hex[142:218]
                else :
                    left = 156 - save
                    data  = data + raw_hex[10:10+left]
                    history_csv = history_decode(data)
                    csv_list.append(history_csv)
                    total_list.append(batch_list)
                    num += 1
                    pb1['value'] = num
                    batch_list = []
                    save = 208 - left # 剩下資料長度 總長222 前10H、後4H、data等於208
                    if save >= 156 :
                        data = raw_hex[10+left:left+166]
                        if 'f'*120 in data:break
                        history_csv = history_decode(data)
                        csv_list.append(history_csv)
                        total_list.append(batch_list)
                        num += 1
                        pb1['value'] = num
                        batch_list = []
                        left = left + 156
                    data = raw_hex[10+left:218]    
                    save = 208 - left
            if lb.size() != 0:
                while lb.size():
                    lb.delete(0)
                    
            sortedList = sorted(total_list,reverse= False)#執行排序
            #total_list = []
            i = 0
            for item in sortedList:#將排序結果插入
                if i <10:
                    string = str('%3d'%(i))+' : '+str(item[0])
                else :
                    string = str(i)+' : '+str(item[0])
                lb.insert(tk.END,string)
                i += 1
            sortedcsv = sorted(csv_list,reverse= False)    
            for item in sortedcsv:
                writer.writerow(item)
            pb1['value'] = 40
            
    print('log history finished download.')
    print('-' * 100)
    download_complete()
    ser.close()

#檢查ok_1開關的值  
def ok_function_1(prompt):
    global switch_okbtn_1,ser_1,temp_mv_convert_ph_1,switch_function_1
    btn_ok_1['state'] = tk.NORMAL
    remind_content_1.set(prompt)
    while True:
        if switch_okbtn_1 == '0':
            r1_code = bytes.fromhex('F7 03 00 00 00 37 10 8A')
            ser_1.write(r1_code)
            data_ra = ser_1.readline()  # 讀取一行
            raw = data_ra.hex()
            if len(raw) != 230:
                    while True:        
                        msg = ser_1.readline()
                        raw = f'{raw}{msg.hex()}'
                        if len(raw) == 230:
                            # print(raw)
                            break
            # value_day.set(time.ctime())
            value_ph_1.set(temp_mv_convert_ph_1)
            # addr_type_tex(raw, 6, 14, 'float', 'ph', value_ph)
            addr_type_tex_1(raw, 14, 22, 'float', 'temperature', value_temp_1)
            addr_type_tex_1(raw, 46, 54, 'float', 'measure_mv', value_mV_1)
            addr_type_tex_1(raw, 54, 62, 'float', 'Act_mv', value_Act_mv_1)
            addr_type_tex_1(raw, 62, 70, 'float', 'Ref_mv', value_Ref_mv_1)
            addr_type_tex_1(raw, 70, 78, 'float', 'Temperature_Ohms', value_Temperature_Ohms_1)
            time.sleep(1)
        else:
            switch_okbtn_1 = '0' #復歸按鈕
            switch_function_1 = '0'
            btn_ok_1['state'] = tk.DISABLED 
            remind_content_1.set('')
            return  #跳出迴圈
#檢查ok_2開關的值
def ok_function_2(prompt):
    global switch_okbtn_2,ser_2,temp_mv_convert_ph_2,switch_function_2
    btn_ok_2['state'] = tk.NORMAL
    remind_content_2.set(prompt)
    while True:
        if switch_okbtn_2 == '0':
            r1_code = bytes.fromhex('F7 03 00 00 00 37 10 8A')
            ser_2.write(r1_code)
            data_ra = ser_2.readline()  # 讀取一行
            raw = data_ra.hex()
            if len(raw) != 230:
                    while True:        
                        msg = ser_2.readline()
                        raw = f'{raw}{msg.hex()}'
                        if len(raw) == 230:
                            # print(raw)
                            break
            value_ph_2.set(temp_mv_convert_ph_2)
            addr_type_tex_2(raw, 14, 22, 'float', 'temperature', value_temp_2)
            addr_type_tex_2(raw, 46, 54, 'float', 'measure_mv', value_mV_2)
            addr_type_tex_2(raw, 54, 62, 'float', 'Act_mv', value_Act_mv_2)
            addr_type_tex_2(raw, 62, 70, 'float', 'Ref_mv', value_Ref_mv_2)
            addr_type_tex_2(raw, 70, 78, 'float', 'Temperature_Ohms', value_Temperature_Ohms_2)
            time.sleep(1)
        else:
            switch_okbtn_2 = '0' #復歸按鈕
            switch_function_2 = '0'
            btn_ok_2['state'] = tk.DISABLED 
            remind_content_2.set('')
            return  #跳出迴圈
#切換功能_1
switch_function_1 = '0' 
switch_okbtn_1 = '0' 
def ok_btn_1():
    global switch_okbtn_1
    switch_okbtn_1 = '1'
def go_disconnect_1() :
    global switch_function_1
    switch_function_1 = 'disconnect'
def go_connect_1():
    global switch_function_1
    switch_function_1 = 'go connect'
def go_calibration_1() :
    global switch_function_1
    switch_function_1 = 'go calibration'
def go_log_1() :
    global switch_function_1
    switch_function_1 = 'go datalog'

#切換功能_2
switch_function_2 = '0' 
switch_okbtn_2 = '0' 
def ok_btn_2():
    global switch_okbtn_2
    switch_okbtn_2 = '1'
def go_disconnect_2() :
    global switch_function_2
    switch_function_2 = 'disconnect'
def go_connect_2():
    global switch_function_2
    switch_function_2 = 'go connect'
def go_calibration_2() :
    global switch_function_2
    switch_function_2 = 'go calibration'
def go_log_2() :
    global switch_function_2
    switch_function_2 = 'go datalog'

#按鈕睡覺功能_1
def btn_sleep_1(btn,data):
    global temp_mv_convert_ph_1,yar_1
    btn['state'] = tk.DISABLED
    remind_content_1.set('Please wait...')
    while True:
        r1_code = bytes.fromhex('F7 03 00 00 00 37 10 8A')
        ser_1.write(r1_code)
        data_ra = ser_1.readline()  # 讀取一行
        raw = data_ra.hex()
        if len(raw) != 230:
                    while True:        
                        msg = ser_1.readline()
                        raw = f'{raw}{msg.hex()}'
                        if len(raw) == 230:
                            # print(raw)
                            break
        # value_day.set(time.ctime())
        value_ph_1.set(temp_mv_convert_ph_1)
        addr_type_tex_1(raw, 14, 22, 'float', 'temperature', value_temp_1)
        addr_type_tex_1(raw, 46, 54, 'float', 'measure_mv', value_mV_1)
        addr_type_tex_1(raw, 54, 62, 'float', 'Act_mv', value_Act_mv_1)
        addr_type_tex_1(raw, 62, 70, 'float', 'Ref_mv', value_Ref_mv_1)
        addr_type_tex_1(raw, 70, 78, 'float', 'Temperature_Ohms', value_Temperature_Ohms_1)
        print(round(abs(float(temp_mv_convert_ph_1)-(sum(yar_1[-data:]) / data)),2)) #abs絕對值
        if abs(float(temp_mv_convert_ph_1)-(sum(yar_1[-data:]) / data)) <0.1:
            break
    remind_content_1.set('Please wait...')
#按鈕睡覺功能_2

def animate(i):
    global yar_1,xar_1,temp_mv_convert_ph_1,j,ylim_value_1
    yar_1.append(float(temp_mv_convert_ph_1))
    xar_1.append(i)
    line1.set_data(xar_1, yar_1)
    if i<50:
        ax1.set_xlim(0,i+1)
    else:
        ax1.set_xlim(i-50,i)
    ax1.set_ylim(round(ylim_value_1, 1) - 0.2, round(ylim_value_1, 1) + 0.2)
    if len(yar_1) <= 10:
        ylim_value_1 = temp_mv_convert_ph_1
    else:
        ylim_value_1 = sum(yar_1[-5:]) / 5
#畫圖_2，更新data
temp_mv_convert_ph_2 = 0
ylim_value_2 = 0

#校正功能_1
temp_action_1 = []
alert_message_1 = ''
def command():
    time.sleep(2)
    COM_PORT = var_1.get()
    global BAUD_RATES,ser_1,temp_action_1,alert_message_1
    ser_1 = serial.Serial(COM_PORT, BAUD_RATES, timeout=1)

    r2_code = bytes.fromhex('F7 03 00 37 00 36 60 84')
    ser_1.write(r2_code)
    data_raw = ser_1.readline()  # 讀取一行
    raw_hex = data_raw.hex()
    if len(raw_hex) != 226:
                    while True:        
                        msg = ser_1.readline()
                        raw_hex = f'{raw_hex}{msg.hex()}'
                        if len(raw_hex) == 226 :
                            # print(raw_hex)
                            break
    addr_type_tex_1(raw_hex, 102, 110, 'float', 'Slope_mV_pH', value_Slope_mV_pH_1)
    addr_type_tex_1(raw_hex, 110, 118, 'float', 'Offset_mV', value_Offset_mV_1)
    time.sleep(2)#有時slope.offset會沒讀到
    remind_content_1.set('Please wait...')

    for code_dict in code_list:
        print('###COM09###')
        write_code = bytes.fromhex(code_dict['request'])
        check_code = code_dict['response'].replace(' ', '').lower()#空格去除
        ser_1.write(write_code)

        msg_cache = ''#抓取的資料
        while True:
            if ser_1.in_waiting:
                msg = ser_1.readline()#讀取資料

                if msg_cache == '':
                    decode_msg = msg.hex()
                else:
                    decode_msg = f'{msg_cache}{msg.hex()}'

                print(f'check_code: {check_code}\ndecode_msg: {decode_msg}')
                if check_code in decode_msg:
                    msg_cache = ''
                    break
                else:
                    msg_cache = decode_msg

        print('one request done.')
        print('-' * 100)

    #判斷address位置
    for code_item in command_list:
        print('###COM09###')
        r3_code = bytes.fromhex('F7 03 00 6D 00 37 81 57')
        check_code0 = code_item['addr']
        ser_1.write(r3_code)
        while True:
            if ser_1.in_waiting:
                msg = ser_1.readline()#讀取資料

                if msg_cache == '':
                    decode_msg = msg.hex()
                else:
                    decode_msg = f'{msg_cache}{msg.hex()}'


                if check_code0 in decode_msg :
                    print(f'check_code: {check_code0}\ndecode_msg: {decode_msg}')
                    msg_cache = ''
                    break
                else:
                    msg_cache = decode_msg
                    print(msg_cache)
                    if '00160021' in decode_msg:
                        alert_message_1 = 'Calibration Warning\nSlope low'
                        temp_action_1 = code_item['action']
                        code_item['action'] = 'error'
                        break
                    if '00160020' in decode_msg:
                        alert_message_1 = 'Calibration Error\nCALS TOO CLOSE'
                        temp_action_1 = code_item['action']
                        code_item['action'] = 'error'
                        break
                    if '0016001a' in decode_msg:
                        alert_message_1 = 'Calibration Error\nNot Stable'#插兩支有問題
                        temp_action_1 = code_item['action']
                        code_item['action'] = 'error'
                        break

        action = code_item['action']
        print(f'action is {action}')
        if action =='wait1':
            remind_content_1.set('Please wait...')
            btn_sleep_1(btn_ok_1,100)

        if action =='wait2':
            remind_content_1.set('Please wait...')
            btn_sleep_1(btn_ok_1,150)

        if action =='put point 1':
            ok_function_1('Point 1 put into buffer\nBuffer List: JIS:2,4,7,9,10')

        if action =='complete 1':
            ok_function_1('First Point Complete')

        if action =='put point 2':
            ok_function_1('Point 2 put into buffer\nBuffer List: JIS:2,4,7,9,10')

        if action =='complete 2':
            r2_code = bytes.fromhex('F7 03 00 37 00 36 60 84')
            ser_1.write(r2_code)
            data_raw = ser_1.readline()  # 讀取一行
            raw_hex = data_raw.hex()
            if len(raw_hex) != 226:
                    while True:        
                        msg = ser_1.readline()
                        raw_hex = f'{raw_hex}{msg.hex()}'
                        if len(raw_hex) == 226 :
                            # print(raw_hex)
                            break
            addr_type_tex_1(raw_hex, 102, 110, 'float', 'Slope_mV_pH', value_Slope_mV_pH_1)
            addr_type_tex_1(raw_hex, 110, 118, 'float', 'Offset_mV', value_Offset_mV_1)
            ok_function_1(f'Result : Slope {slope_1} mV/ph\n         Offset {offset_1} mV')

        if action =='error':
            print(temp_action_1)
            code_item['action'] = temp_action_1
            quit_code = bytes.fromhex('F7 06 00 92 00 0A BC B6')
            ser_1.write(quit_code)
            data_raw = ser_1.readline()  # 讀取一行
            raw_hex = data_raw.hex()
            print(raw_hex)
            ok_function_1(alert_message_1)
            alert_message_1 = ''
            
            break #會直接跳到ser_1.close
        write_code = bytes.fromhex(code_item['request'])
        check_code = code_item['response'].replace(' ', '').lower()
        ser_1.write(write_code)

        msg_cache = ''
        checkcode_time = 0
        while True:
                if ser_1.in_waiting:
                    msg = ser_1.readline()#讀取資料

                    if msg_cache == '':
                        decode_msg = msg.hex()
                    else:
                        decode_msg = f'{msg_cache}{msg.hex()}'

                    print(f'check_code: {check_code}\ndecode_msg: {decode_msg}')
                    if check_code in decode_msg :
                        msg_cache = ''
                        break
                    else:
                        msg_cache = decode_msg
                        checkcode_time+=1
                        print(checkcode_time)
                        if checkcode_time == 3:
                            quit_code = bytes.fromhex('F7 06 00 92 00 0A BC B6')#0A BC B6#12 BC BC
                            ser_1.write(quit_code)
                            data_raw = ser_1.readline()  # 讀取一行
                            raw_hex = data_raw.hex()
                            ok_function_1('Calibration fail')
        print('one command done.')
        print('-' * 100)

#校正功能_2
temp_action_2 = []
alert_message_2 = ''

def callback(event):

    obj = event.widget
    indexs = obj.curselection()
    indexs = indexs[0]
    var = [ his_date ,his_method ,his_slope ,his_temp ,his_Act_Z ,his_ref_Z,
            his_respond_time, his_respond_char,Buf_A ,Buf_B	,Dev_A	, Dev_B,
            Pot_A, Pot_B, Temp_A, Temp_B, Res1_A, Res1_B, Res2_A, Res2_B] #, his_health

    sublist = sortedList[indexs]

    for i in range(len(var)):
        var[i].set(sublist[i])
    if   sublist[2] < -57.55: his_health.set(100)
    elif sublist[2] < -57.00: his_health.set(80)
    elif sublist[2] < -53.41: his_health.set(70)
    elif sublist[2] < -52.54: his_health.set(60)
    else : his_health.set(50)

def download_complete():
    messagebox.showinfo("Info","Downloads completed")


# =============================================================================
# GUI
# =============================================================================
root = tk.Tk()
root.geometry('800x770+500+0')
notebook = ttk.Notebook(root)
frame1 = ttk.Frame()
# frame2 = ttk.Frame()
# frame3 = ttk.Frame()
# frame4 = ttk.Frame()
frame5 = ttk.Frame()

notebook.add(frame1, text="Measure")
# notebook.add(frame2, text="Probe info 1")
# notebook.add(frame3, text="Signals")
# notebook.add(frame4, text="Probe info 2")
notebook.add(frame5, text="History log")
notebook.pack(padx=10, pady=10)  # ,fill=BOTH,expand=TRUE

# =============================================================================
# 頁次1
# =============================================================================
#command
# 顯示預設值
#value_day_1 = tk.StringVar()
# =============================================================================
# 1.CALMEMO
pw = tk.PanedWindow(frame1)
class Section:

    def __init__(self, num, pw):
        self.pw = pw
        self.num = num
        if num == 1: 
            self.order = [1,1]
        elif num == 2:
            self.order = [2,1]
        elif num == 3:
            self.order = [1,2]
        elif num == 4:
            self.order = [2,2]
        self.calmemo_labelframe = tk.LabelFrame(self.pw, text = str(self.num)+'.CALMEMO')
        self.pw.add(self.calmemo_labelframe)
        self.calibration_labelframe = tk.LabelFrame(self.calmemo_labelframe)
        self.signal_labelframe =  tk.LabelFrame(self.calmemo_labelframe,bd = 0)
        self.ph_label = {}
        self.ph_label['item_ph'] = tk.Label(self.calmemo_labelframe, width=20, text='pH', anchor ='e', font=('Arial', 14))
        self.ph_label['value'] = tk.StringVar()
        self.ph_label['value_ph'] = tk.Label(self.calmemo_labelframe , width=10, relief="raised", textvariable=self.ph_label['value'], font=("Times", 20))
        self.c_label = {}
        self.c_label['item_c'] = tk.Label(self.calmemo_labelframe, width=20, text='°C', anchor ='e', font=('Arial', 14))
        self.c_label['value'] = tk.StringVar()
        self.c_label['value_c'] = tk.Label(self.calmemo_labelframe , width=10, relief="raised", textvariable=self.c_label['value'], font=("Times", 20))
        self.mv_label = {}
        self.mv_label['item_mv'] = tk.Label(self.calmemo_labelframe, width=20, text='mV', anchor ='e', font=('Arial', 14))
        self.mv_label['value'] = tk.StringVar()
        self.mv_label['value_mv'] = tk.Label(self.calmemo_labelframe , width=10, relief="raised", textvariable=self.mv_label['value'], font=("Times", 20))
        self.calibration_btn = tk.Button(self.calibration_labelframe, width=10,text='Calibration')
        self.ok_btn = tk.Button(self.calibration_labelframe, width=10,text="OK")
        self.abort_btn = tk.Button(self.calibration_labelframe,width=10, text="Abort")
        self.glassmv_label = {}
        self.glassmv_label['item_glassmv'] = tk.Label(self.signal_labelframe,width=10, text='Glass mV:', font=('Arial', 12),anchor ='e')
        self.glassmv_label['value'] = tk.StringVar()
        self.glassmv_label['value_glassmv'] = tk.Label(self.signal_labelframe, width=15, textvariable=self.glassmv_label['value'], font=("Times", 12),anchor ='w')
        self.refmv_label = {}
        self.refmv_label['item_refmv'] = tk.Label(self.signal_labelframe,width=10, text='Ref mV:', font=('Arial', 12),anchor ='e')
        self.refmv_label['value'] = tk.StringVar()
        self.refmv_label['value_refmv'] =tk.Label(self.signal_labelframe, width=15, textvariable=self.refmv_label['value'], font=("Times", 12),anchor ='w') 
        self.rtdohm_label = {}
        self.rtdohm_label['item_rtdohm'] = tk.Label(self.signal_labelframe,width=10, text='RTD Ohm:', font=('Arial', 12),anchor ='e')
        self.rtdohm_label['value'] = tk.StringVar()
        self.rtdohm_label['value_rtdohm'] = tk.Label(self.signal_labelframe, width=15, textvariable=self.rtdohm_label['value'], font=("Times", 12),anchor ='w')
        self.probe_btn = tk.Button(self.calmemo_labelframe,width=10, text='Probe', command=self.probe_info)
        self.connect_btn = tk.Button(self.calmemo_labelframe,width=10, text="Connect", command=lambda: [MyThread(serial_try_1),MyThread(go_connect_1)])
        self.disconnect_btn = tk.Button(self.calmemo_labelframe,width=10, text='Disconnect', command=lambda: [MyThread(go_disconnect_1)])
        
        self.remind_label = {}
        self.remind_label['value'] = tk.StringVar()
        self.remind_label = tk.Label(self.calmemo_labelframe,width=25,height=2,textvariable = self.remind_label['value'], font=('Arial',12),fg='blue')
        
        self.comport_combobox = {}
        self.comport_combobox['value'] = tk.StringVar()
        self.comport_combobox['item_comport'] = ttk.Combobox(self.calmemo_labelframe,width=8, textvariable=self.comport_combobox['value'])
        self.comport_combobox['item_comport']["value"] = '0'
        # self.comport_combobox['item_comport']["value"] = serial_ports()
        self.comport_combobox['item_comport'].current(0) #設定預設選項為0項
# =============================================================================
#         probe
# =============================================================================
        #item1
        self.deviceModelName_label = {}
        self.deviceModelName_label['value'] = tk.StringVar()
        self.deviceModelName_label['value_deviceModelName'] = tk.Label(frame1, width=15, textvariable=self.deviceModelName_label['value'], font=("Times", 16),anchor ='w')
        #item2
        self.deviceName_label = {}
        self.deviceName_label['value'] = tk.StringVar()
        self.deviceName_label['value_deviceName'] = tk.Label(frame1, width=15,textvariable=self.deviceName_label['value'], font=("Times", 16),anchor ='w')
        #item3
        self.serialNumberString_label = {}
        self.serialNumberString_label['value'] = tk.StringVar()
        self.serialNumberString_label['value_serialNumberString'] = tk.Label(frame1, width=15,textvariable=self.serialNumberString_label['value'], font=("Times", 16),anchor ='w')
        #item 4
        self.sensorModel_label = {}
        self.sensorModel_label['value'] = tk.StringVar()
        self.sensorModel_label['value_sensorModel'] = tk.Label(frame1, width=15 , textvariable=self.sensorModel_label['value'], font=("Times", 16),anchor ='w')
        #item 5
        self.sensorSNString_label = {}
        self.sensorSNString_label['value'] = tk.StringVar()
        self.sensorSNString_label['value_sensorSNString'] = tk.Label(frame1, width=15,textvariable=self.sensorSNString_label['value'], font=("Times", 16),anchor ='w')
        #item 6
        self.factoryCalDate_label = {}
        self.factoryCalDate_label['value'] = tk.StringVar()
        self.factoryCalDate_label['value_factoryCalDate'] = tk.Label(frame1, width=15,textvariable=self.factoryCalDate_label['value'], font=("Times", 16),anchor ='w')
        #item 7
        self.firstCalDate_label = {}
        self.firstCalDate_label['value'] = tk.StringVar()
        self.firstCalDate_label['value_firstCalDate'] = tk.Label(frame1, width=15,textvariable=self.firstCalDate_label['value'], font=("Times", 16),anchor ='w')
        #item 8
        self.lastCalDate_label = {}
        self.lastCalDate_label['value'] = tk.StringVar()
        self.lastCalDate_label['value_lastCalDate'] = tk.Label(frame1, width=15, textvariable=self.lastCalDate_label['value'],font=("Times", 16),anchor ='w')
        #item 9
        # text_NextState = tk.Label(frame1,width=20, text='NextState:', font=('Arial', 14))
        # text_NextState.grid(padx=5, pady=10, row=9, column=1)
        # NextState = tk.Label(frame1, width=20, font=("Times", 20),anchor ='w')
        # NextState.grid(padx=5, pady=10, row=9, column=2)
        #item 10
        self.sensorDays_label = {}
        self.sensorDays_label['value'] = tk.StringVar()
        self.sensorDays_label['value_sensorDays'] = tk.Label(frame1, width=15,textvariable=self.sensorDays_label['value'], font=("Times", 16),anchor ='w')
        #item 11
        self.offsetMv_label = {}
        self.offsetMv_label['value'] = tk.StringVar()
        self.offsetMv_label['value_offsetMv'] = tk.Label(frame1, width=15,textvariable=self.offsetMv_label['value'], font=("Times", 16),anchor ='w')
        #item 12
        self.slopeMv_label = {}
        self.slopeMv_label['value'] = tk.StringVar()
        self.slopeMv_label['value_slopeMv'] =  tk.Label(frame1, width=15,textvariable=self.slopeMv_label['value'], font=("Times", 16),anchor ='w') 
        #item 13
        self.sensorHealth_label = {}
        self.sensorHealth_label['value'] = tk.StringVar()
        self.sensorHealth_label['value_sensorHealth'] = tk.Label(frame1, width=15,textvariable=self.sensorHealth_label['value'], font=("Times", 16),anchor ='w')
        

        
        self.grid_component()
        
    def probe_info(self):
        top = tk.Toplevel()
        top.title('Probe information '+str(self.num))
        #item 1
        text_Device_model_name = tk.Label(top,width=20, text='Device model name:', font=('Arial', 14),anchor ='e')
        text_Device_model_name.grid(padx=5, pady=5, row=1, column=1)
        Device_model_name1 = tk.Label(top, width=15, textvariable=self.deviceModelName_label['value'], font=("Times", 16),anchor ='w')
        Device_model_name1.grid(padx=5, pady=5, row=1, column=2)
        #item2
        text_DeviceName = tk.Label(top,width=20,text='Probe name:', font=('Arial', 14),anchor ='e')
        text_DeviceName.grid(padx=5, pady=5, row=2, column=1)
        DeviceName = tk.Label(top, width=15,textvariable=self.deviceName_label['value'], font=("Times", 16),anchor ='w')
        DeviceName.grid(padx=5, pady=5, row=2, column=2 )
        #item3
        text_SerialNumberString = tk.Label(top,width=20, text='Serial number:', font=('Arial', 14),anchor ='e')
        text_SerialNumberString.grid(padx=5, pady=5, row=3, column=1)
        SerialNumberString = tk.Label(top, width=15,textvariable=self.serialNumberString_label['value'], font=("Times", 16),anchor ='w')
        SerialNumberString.grid(padx=5, pady=5, row=3, column=2)
        #item 4
        text_SensorModel = tk.Label(top,width=20, text='Sensor model name:', font=('Arial', 14),anchor ='e')
        text_SensorModel.grid(padx=5, pady=5, row=4, column=1)
        SensorModel = tk.Label(top, width=15 , textvariable=self.sensorModel_label['value'], font=("Times", 16),anchor ='w')
        SensorModel.grid(padx=5, pady=5, row=4, column=2 )
        #item 5
        text_SensorSNString = tk.Label(top,width=20, text='Sensor serial number:', font=('Arial', 14),anchor ='e')
        text_SensorSNString.grid(padx=5, pady=5, row=5, column=1)
        SensorSNString = tk.Label(top, width=15,textvariable=self.sensorSNString_label['value'], font=("Times", 16),anchor ='w')
        SensorSNString.grid(padx=5, pady=5, row=5, column=2)
        #item 6
        text_FactoryCalDate = tk.Label(top,width=20, text='FactoryCalDate:', font=('Arial', 14),anchor ='e')
        text_FactoryCalDate.grid(padx=5, pady=5, row=6, column=1)
        FactoryCalDate = tk.Label(top, width=15,textvariable=self.factoryCalDate_label['value'], font=("Times", 16),anchor ='w')
        FactoryCalDate.grid(padx=5, pady=5, row=6, column=2)
        #item 7
        text_FirstCalDate = tk.Label(top,width=20, text='FirstCalDate:', font=('Arial', 14),anchor ='e')
        text_FirstCalDate.grid(padx=5, pady=5, row=7, column=1)
        FirstCalDate = tk.Label(top, width=15,textvariable=self.firstCalDate_label['value'], font=("Times", 16),anchor ='w')  # ,textvariable=mV
        FirstCalDate.grid(padx=5, pady=5, row=7, column=2)
        #item 8
        text_LastCalDate = tk.Label(top,width=20, text='LastCalDate:', font=('Arial', 14),anchor ='e')
        text_LastCalDate.grid(padx=5, pady=5, row=8, column=1)
        LastCalDate = tk.Label(top, width=15, textvariable=self.lastCalDate_label['value'],font=("Times", 16),anchor ='w')  # ,textvariable=mV
        LastCalDate.grid(padx=5, pady=5, row=8, column=2)
        #item 9
        # text_NextState = tk.Label(top,width=20, text='NextState:', font=('Arial', 14))
        # text_NextState.grid(padx=5, pady=10, row=9, column=1)
        # NextState = tk.Label(top, width=20, font=("Times", 20),anchor ='w')
        # NextState.grid(padx=5, pady=10, row=9, column=2)
        #item 10
        text_SensorDays = tk.Label(top,width=20, text='Sensor days:', font=('Arial', 14),anchor ='e')
        text_SensorDays.grid(padx=5, pady=5, row=10, column=1)
        SensorDays = tk.Label(top, width=15,textvariable=self.sensorDays_label['value'], font=("Times", 16),anchor ='w')  # ,textvariable=mV
        SensorDays.grid(padx=5, pady=5, row=10, column=2)
        #item 11
        text_Offset_mV = tk.Label(top,width=20, text='Offset mV:', font=('Arial', 14),anchor ='e')
        text_Offset_mV.grid(padx=5, pady=5, row=11, column=1)
        Offset_mV = tk.Label(top, width=15,textvariable=self.offsetMv_label['value'], font=("Times", 16),anchor ='w')  # ,textvariable=mV
        Offset_mV.grid(padx=5, pady=5, row=11, column=2)
        #item 12
        text_Slope_mV_pH = tk.Label(top,width=20, text='Slope mV/pH:', font=('Arial', 14),anchor ='e')
        text_Slope_mV_pH.grid(padx=5, pady=5, row=12, column=1)
        Slope_mV_pH = tk.Label(top, width=15,textvariable=self.slopeMv_label['value'], font=("Times", 16),anchor ='w')  # ,textvariable=mV
        Slope_mV_pH.grid(padx=5, pady=5, row=12, column=2)
        #item 13
        text_SensorHealth = tk.Label(top,width=20, text='Health:', font=('Arial', 14),anchor ='e')
        text_SensorHealth.grid(padx=5, pady=5, row=13, column=1)
        SensorHealth = tk.Label(top, width=15,textvariable=self.sensorHealth_label['value'], font=("Times", 16),anchor ='w')  # ,textvariable=mV
        SensorHealth.grid(padx=5, pady=5, row=13, column=2)    
        
    def grid_component(self):
        self.calmemo_labelframe.grid(padx=10, pady=10, row = self.order[0],column=self.order[1])
        self.ph_label['item_ph'].grid(padx=1, pady=10, row=1, column=1,sticky = 'n')
        self.ph_label['value_ph'].grid(padx=1, pady=10, row=1, column=1,sticky = 'n')
        self.c_label['item_c'].grid(padx=1, pady=10, row=1, column=1)
        self.c_label['value_c'].grid(padx=1, pady=10, row=1, column=1)
        self.mv_label['item_mv'].grid(padx=1, pady=10, row=1, column=1,sticky = 's')
        self.mv_label['value_mv'].grid(padx=1, pady=10, row=1, column=1,sticky = 's')
        
        self.calibration_labelframe.grid(padx=5, pady=10, row=1, column=2)
        self.calibration_btn.grid(padx=5, pady=10, row=1, column=1)
        self.ok_btn.grid(padx=5, pady=10, row=2, column=1)
        self.abort_btn.grid(padx=5, pady=10, row=3, column=1)
        
        self.signal_labelframe.grid(row=2,column=1)
        self.glassmv_label['item_glassmv'].grid(pady=2, row=1, column=1)
        self.glassmv_label['value_glassmv'].grid(row=1, column=2)
        self.refmv_label['item_refmv'].grid(pady=2,row=2, column=1)
        self.refmv_label['value_refmv'].grid(row=2, column=2)
        self.rtdohm_label['item_rtdohm'].grid(pady=2,row=3, column=1)
        self.rtdohm_label['value_rtdohm'].grid(row=3, column=2)
        
        self.probe_btn.grid(row=2, column=2,sticky = 'n')
        self.connect_btn.grid(row=2,column=2)
        self.disconnect_btn.grid(row=2, column=2,sticky = 's')
        self.comport_combobox['item_comport'].grid(pady=3,row=3,column=2,sticky='n')
        
    
    def serial_ports(self):
        ports = ['COM%s' % (i + 1) for i in range(256)]#列出所有1-256 COM ports
        result = []
        for port in ports:
            try:
                s = serial.Serial(port)
                s.close()
                result.append(port)
            except (OSError, serial.SerialException):
                pass
        return result

S1 = Section(1, pw)
S2 = Section(2, pw)
S3 = Section(3, pw)
S4 = Section(4, pw)

# probe_info(S1)
# probe(S2)
# probe(S3)

# S1 = Section(1, pw)
# S1.calmemo_dict['ph_component']['value'].set('24')

pw.pack()
# a.probe_info()
# pw = tk.PanedWindow(frame1)


# =============================================================================
# 頁次3
# =============================================================================
his_date = tk.StringVar()
his_method = tk.StringVar()
his_slope = tk.StringVar()
his_temp = tk.StringVar()
his_Act_Z = tk.StringVar()
his_ref_Z = tk.StringVar()
his_respond_time = tk.StringVar()
his_respond_char = tk.StringVar()
his_health = tk.StringVar()
Buf_A = tk.StringVar()
Buf_B = tk.StringVar()
Dev_A = tk.StringVar()
Dev_B = tk.StringVar()
Pot_A = tk.StringVar()
Pot_B = tk.StringVar()	
Temp_A = tk.StringVar()	
Temp_B = tk.StringVar()	
Res1_A = tk.StringVar()	
Res1_B = tk.StringVar()	
Res2_A = tk.StringVar()	
Res2_B = tk.StringVar()

pw = tk.PanedWindow(frame5)
labframe1 = tk.LabelFrame(pw,text = 'Date',width=40,height = 40)
pw.add(labframe1)
labframe1.grid(row=1,column=1)
lb = tk.Listbox(labframe1,width=28,height = 30)
lb.bind("<<ListboxSelect>>",callback)
lb.grid(padx=8, pady=16, row=1, column=1)
labframe = tk.LabelFrame(pw,text = 'Record',width=40,height = 20)
labframe.grid(row=1,column=2)
labframe8 = tk.LabelFrame(labframe,text = 'main',width=40,height = 20)
labframe8.grid(row=1,column=1)
labframe0 = tk.LabelFrame(labframe,text = 'Buffer',width=40,height = 20)
labframe0.grid(row=10,column=1)
lab_date = tk.Label(labframe8, text='Date:', font=('Arial', 10))
lab_date.grid(padx=5, pady=2, row=1, column=1)
lab_date1 = tk.Label(labframe8, width=20, relief="raised", textvariable=his_date, font=("Times", 10))
lab_date1.grid(padx=5, pady=2, row=1, column=2)
#item 2
lab_method = tk.Label(labframe8, text='Method:', font=('Arial', 10))
lab_method.grid(padx=5, pady=2, row=2, column=1)
lab_method1 = tk.Label(labframe8, width=20, relief="raised",textvariable=his_method, font=("Times", 10))
lab_method1.grid(padx=5, pady=2, row=2, column=2)
#item 3
lab_slope = tk.Label(labframe8, text='Slope:', font=('Arial', 10))
lab_slope.grid(padx=5, pady=2, row=3, column=1)
lab_slope1 = tk.Label(labframe8, width=20, relief="raised",textvariable=his_slope, font=("Times", 10))
lab_slope1.grid(padx=5, pady=2, row=3, column=2)
#item 4
lab_temp = tk.Label(labframe8, text='Temperature:', font=('Arial', 10))
lab_temp.grid(padx=5, pady=2, row=4, column=1)
lab_temp1 = tk.Label(labframe8, width=20, relief="raised",textvariable=his_temp, font=("Times", 10))  # ,textvariable=mV
lab_temp1.grid(padx=5, pady=2, row=4, column=2)
#item 5
lab_Act_Z = tk.Label(labframe8, text='Act_Z:', font=('Arial', 10))
lab_Act_Z.grid(padx=5, pady=2, row=5, column=1)
lab_Act_Z1 = tk.Label(labframe8, width=20, relief="raised", textvariable=his_Act_Z,font=("Times", 10))  # ,textvariable=mV
lab_Act_Z1.grid(padx=5, pady=2, row=5, column=2)
#item 6
lab_ref_Z = tk.Label(labframe8, text='Ref_Z:', font=('Arial', 10))
lab_ref_Z.grid(padx=5, pady=2, row=6, column=1)
lab_ref_Z1 = tk.Label(labframe8, width=20, relief="raised",textvariable=his_ref_Z, font=("Times", 10))  # ,textvariable=mV
lab_ref_Z1.grid(padx=5, pady=2, row=6, column=2)
#item 7
lab_respond_time = tk.Label(labframe8, text='Respond_Time:', font=('Arial', 10))
lab_respond_time.grid(padx=5, pady=2, row=7, column=1)
lab_respond_time1 = tk.Label(labframe8, width=20, relief="raised",textvariable=his_respond_time, font=("Times", 10))  # ,textvariable=mV
lab_respond_time1.grid(padx=5, pady=2, row=7, column=2)
#item 8
lab_respond_char = tk.Label(labframe8, text='Respond_Char:', font=('Arial', 10))
lab_respond_char.grid(padx=5, pady=2, row=8, column=1)
lab_respond_char1 = tk.Label(labframe8, width=20, relief="raised",textvariable=his_respond_char, font=("Times", 10))  # ,textvariable=mV
lab_respond_char1.grid(padx=5, pady=2, row=8, column=2)
#item 9
lab_SensorHealth = tk.Label(labframe8, text='SensorHealth:', font=('Arial', 10))
lab_SensorHealth.grid(padx=5, pady=2, row=9, column=1)
lab_SensorHealth1 = tk.Label(labframe8, width=20, relief="raised",textvariable=his_health, font=("Times", 10))  # ,textvariable=mV
lab_SensorHealth1.grid(padx=5, pady=2, row=9, column=2)


lab_Buf_A = tk.Label(labframe0, text='Buf_A:', font=('Arial', 10))
lab_Buf_A.grid(padx=5, pady=2, row=1, column=1)
lab_Buf_A1 = tk.Label(labframe0, width=20, relief="raised", textvariable=Buf_A, font=("Times", 10))
lab_Buf_A1.grid(padx=5, pady=2, row=1, column=2)
#item 2
lab_Buf_B = tk.Label(labframe0, text='Buf_B:', font=('Arial', 10))
lab_Buf_B.grid(padx=5, pady=2, row=1, column=3)
lab_Buf_B1 = tk.Label(labframe0, width=20, relief="raised",textvariable=Buf_B, font=("Times", 10))
lab_Buf_B1.grid(padx=5, pady=2, row=1, column=4)
#item 3
lab_Dev_A = tk.Label(labframe0, text='Dev_A:', font=('Arial', 10))
lab_Dev_A.grid(padx=5, pady=2, row=2, column=1)
lab_Dev_A1 = tk.Label(labframe0, width=20, relief="raised",textvariable=Dev_A, font=("Times", 10))
lab_Dev_A1.grid(padx=5, pady=2, row=2, column=2)
#item 4
lab_Dev_B = tk.Label(labframe0, text='Dev_B:', font=('Arial', 10))
lab_Dev_B.grid(padx=5, pady=2, row=2, column=3)
lab_Dev_B1 = tk.Label(labframe0, width=20, relief="raised",textvariable=Dev_B, font=("Times", 10))  # ,textvariable=mV
lab_Dev_B1.grid(padx=5, pady=2, row=2, column=4)
#item 5
lab_Pot_A = tk.Label(labframe0, text='Pot_A:', font=('Arial', 10))
lab_Pot_A.grid(padx=5, pady=2, row=3, column=1)
lab_Pot_A1 = tk.Label(labframe0, width=20, relief="raised", textvariable=Pot_A,font=("Times", 10))  # ,textvariable=mV
lab_Pot_A1.grid(padx=5, pady=2, row=3, column=2)
#item 6
lab_Pot_B = tk.Label(labframe0, text='Pot_B:', font=('Arial', 10))
lab_Pot_B.grid(padx=5, pady=2, row=3, column=3)
lab_Pot_B1 = tk.Label(labframe0, width=20, relief="raised",textvariable=Pot_B, font=("Times", 10))  # ,textvariable=mV
lab_Pot_B1.grid(padx=5, pady=2, row=3, column=4)
#item 7
lab_Temp_A = tk.Label(labframe0, text='Temp_A:', font=('Arial', 10))
lab_Temp_A.grid(padx=5, pady=2, row=4, column=1)
lab_Temp_A1 = tk.Label(labframe0, width=20, relief="raised",textvariable=Temp_A, font=("Times", 10))  # ,textvariable=mV
lab_Temp_A1.grid(padx=5, pady=2, row=4, column=2)
#item 8
lab_Temp_B = tk.Label(labframe0, text='Temp_B:', font=('Arial', 10))
lab_Temp_B.grid(padx=5, pady=2, row=4, column=3)
lab_Temp_B1 = tk.Label(labframe0, width=20, relief="raised",textvariable=Temp_B, font=("Times", 10))  # ,textvariable=mV
lab_Temp_B1.grid(padx=5, pady=2, row=4, column=4)
#item 9
lab_Res1_A = tk.Label(labframe0, text='Res1_A:', font=('Arial', 10))
lab_Res1_A.grid(padx=5, pady=2, row=5, column=1)
lab_Res1_A1 = tk.Label(labframe0, width=20, relief="raised",textvariable=Res1_A, font=("Times", 10))  # ,textvariable=mV
lab_Res1_A1.grid(padx=5, pady=2, row=5, column=2)
# Res1_A	Res1_B	Res2_A	Res2_B
lab_Res1_B = tk.Label(labframe0, text='Res1_B:', font=('Arial', 10))
lab_Res1_B.grid(padx=5, pady=2, row=5, column=3)
lab_Res1_B1 = tk.Label(labframe0, width=20, relief="raised",textvariable=Res1_B, font=("Times", 10))  # ,textvariable=mV
lab_Res1_B1.grid(padx=5, pady=2, row=5, column=4)
#item 7
lab_Res2_A = tk.Label(labframe0, text='Res2_A:', font=('Arial', 10))
lab_Res2_A.grid(padx=5, pady=2, row=6, column=1)
lab_Res2_A1 = tk.Label(labframe0, width=20, relief="raised",textvariable=Res2_A, font=("Times", 10))  # ,textvariable=mV
lab_Res2_A1.grid(padx=5, pady=2, row=6, column=2)
#item 8
lab_Res2_B = tk.Label(labframe0, text='Res2_B:', font=('Arial', 10))
lab_Res2_B.grid(padx=5, pady=2, row=6, column=3)
lab_Res2_B1 = tk.Label(labframe0, width=20, relief="raised",textvariable=Res2_B, font=("Times", 10))  # ,textvariable=mV
lab_Res2_B1.grid(padx=5, pady=2, row=6, column=4)

history_btn = tk.Button(pw,width=14, text="log download", command=lambda: [MyThread(history)])
pw.add(history_btn)
history_btn.grid(padx=8, pady=4, row=2, column=1,sticky = 'e')
quitbtn1 = tk.Button(pw,width=10, text="Abort", command=lambda: MyThread(close))
quitbtn1.grid( padx=5,pady=5,row=2, column=2)

#COM PORT
# var_log= tk.StringVar()
# cb = ttk.Combobox(pw,width=8, textvariable=var_log)
# cb["value"] = serial_ports()
# cb.current(0) #設定預設選項為0項
# cb.grid(row=2,column=1,sticky = 'w')
pb1 = ttk.Progressbar(pw,length=200,mode = 'determinate')
pb1['maximum'] = 40
pb1.grid(row=3,column=1)
    
pw.pack(padx=10,pady=10)
# =============================================================================
root.mainloop()


