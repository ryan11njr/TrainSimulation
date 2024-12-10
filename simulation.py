# simulation.py
import numpy as np
from scipy.interpolate import interp1d
import pandas as pd
import logging
from datetime import datetime
import os
import csv
from network_client import SimulationDataSender

logger = logging.getLogger(__name__)

class TrainSimulation:
    def __init__(self):
        self.train_length = 23.4
        self.train_mass = 194.295e3
        self.train_formation = "6编组4动2拖"
        self.max_speed = 120.0
        self.max_acc = 1.1
        self.max_dec = -1.1
        
        self.actual_time = []  # 用于记录达到指定距离时的时间
        self.number_1 = []     # 用于记录距离检测的次序
        self.actual_position = []  # 用于记录速度为 0 时的距离
        self.number_2 = []         # 用于记录速度检测的次序
        self.speed_zero_counter = 0  # 记录速度为 0 的次数
        self.position_counter = 0    # 记录距离检测的次数
        
        # 添加数据发送器
        self.data_sender = SimulationDataSender()

        self.reset()
        self.load_data()
        self.init_log_file()

        # 启动数据发送器
        self.data_sender.start()
        
        logger.info("列车仿真系统初始化完成")

    def reset(self):
        self.time = 0.0
        self.position = 21604.2803
        self.speed = 0.0
        self.acceleration = 0.0
        self.traction_acc = 0.0
        self.brake_acc = 0.0
        self.resistance_acc = 0.0
        self.status = "正常运行：惰行"
        self.emergency_brake_start = 0.0
        self.stop_start = 0.0
        logger.info("仿真状态已重置")

    def load_data(self):
        try:
            target_data = pd.read_excel('列车目标速度曲线.xlsx')
            self.target_speed_interp = interp1d(
                target_data['列车位置'],
                target_data['列车速度（km/h）'],
                bounds_error=False,
                fill_value=(target_data['列车速度（km/h）'].iloc[0], 
                           target_data['列车速度（km/h）'].iloc[-1])
            )
            
            ceiling_data = pd.read_excel('ATP顶棚速度数据.xls')
            x_points = []
            y_points = []
            for _, row in ceiling_data.iterrows():
                x_points.extend([row['信号里程起点'], row['信号里程终点']])
                y_points.extend([row['土建限速（ATP顶篷速度）']] * 2)
            self.ceiling_speed_interp = interp1d(
                x_points, y_points,
                bounds_error=False,
                fill_value=(y_points[0], y_points[-1])
            )
            
            brake_data = pd.read_excel('制动特性曲线.xls')
            self.brake_acc_interp = interp1d(
                brake_data['速度（km/h）'],
                brake_data['加速度（m/s2）'],
                bounds_error=False,
                fill_value=(brake_data['加速度（m/s2）'].iloc[0], 
                           brake_data['加速度（m/s2）'].iloc[-1])
            )
            
            traction_data = pd.read_excel('牵引特性曲线.xls')
            self.traction_acc_interp = interp1d(
                traction_data['速度（km/h）'],
                traction_data['加速度_AW0（m/s2）'],
                bounds_error=False,
                fill_value=(traction_data['加速度_AW0（m/s2）'].iloc[0], 
                           traction_data['加速度_AW0（m/s2）'].iloc[-1])
            )
            
            logger.info("数据文件加载完成")
            
        except Exception as e:
            logger.error(f"数据加载错误: {str(e)}")
            raise

    def init_log_file(self):
        try:
            if not os.path.exists('logs'):
                os.makedirs('logs')
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            self.log_filename = f'logs/train_simulation_{timestamp}.csv'
            
            with open(self.log_filename, 'w', newline='', encoding='utf-8') as f:
                writer = csv.writer(f)
                writer.writerow([
                    'Simulation Time (s)', 'Position (m)', 'Speed (km/h)', 
                    'Total Acceleration (m/s^2)', 'Traction Acceleration (m/s^2)',
                    'Braking Acceleration (m/s^2))', 'Resistance Acceleration (m/s^2))', 
                    'Operating Condition', 'Target Speed (km/h)', 'Ceiling Speed (km/h)'
                ])

            logger.info(f"日志文件已创建: {self.log_filename}")
            
        except Exception as e:
            logger.error(f"初始化日志文件失败: {str(e)}")
            raise

    def get_resistance(self, speed_kmh):
        A, B, C = 2.03, 0.062, 0.0018
        resistance = (A + B * speed_kmh + C * speed_kmh ** 2) * 9.81 / 1000
        return -resistance

    def update(self, dt, control_acc=None):
        try:
            self.time += dt

            # 检查是否超过顶棚速度并触发ATP紧急制动
            result_message = None
            if self.speed * 3.6 >= self.get_ceiling_speed() and self.status != "ATP紧急制动" and self.status != "紧急制动罚时":
                self.status = "ATP紧急制动"
                result_message = "触发ATP紧急制动"

            # 根据不同状态更新列车运行状态
            if self.status == "ATP紧急制动":
                if self.speed > 0:
                    speed_kmh = self.speed * 3.6
                    self.resistance_acc = self.get_resistance(speed_kmh)
                    self.traction_acc = 0
                    #self.brake_acc = float(self.brake_acc_interp(speed_kmh))
                    self.acceleration = -1.1
                    self.shanhou(dt)
                    status = self.get_status()
                    self.data_sender.send_data(status)
                    if result_message:
                        status["message"] = result_message
                    return status
                else:
                    self.status = "紧急制动罚时"
                    self.speed = 0
                    self.acceleration = 0
                    self.brake_acc = 0
                    self.traction_acc = 0
                    self.emergency_brake_start = self.time
                    self.shanhou(dt)
                    status = self.get_status()
                    self.data_sender.send_data(status)
                    status["message"] ="紧急制动罚时开始"
                    return status

            elif self.status == "紧急制动罚时":
                delta_t = self.time - self.emergency_brake_start
                if delta_t >= 5:
                    self.status = "正常运行：惰行"
                    self.shanhou(dt)
                    status = self.get_status()
                    self.data_sender.send_data(status)
                    status["message"] ="紧急制动罚时结束,进入惰行工况,按Q键进入牵引状态,列车可以再次启动"
                    return status
                else:
                    remaining_time = 5 - delta_t
                    self.shanhou(dt)
                    status = self.get_status()
                    status["message"] = f"紧急制动罚时仍在进行中，剩余时间：{remaining_time:.1f}秒"
                    self.data_sender.send_data(status)
                    return status

            elif self.status == "停站":
                if self.time - self.stop_start >= 23.5:
                    self.position = 22883.33
                    self.status = "正常运行：惰行"
                    self.shanhou(dt)
                    status = self.get_status()
                    self.data_sender.send_data(status)
                    status["message"] = f"列车停站结束，进入惰行状态"
                    return status
                else:
                    remaining_time = 23.5 - (self.time - self.stop_start)
                    self.shanhou(dt)
                    status = self.get_status()
                    self.data_sender.send_data(status)
                    status["message"] = f"列车停站，剩余时间：{remaining_time:.1f}秒"
                    return status

            else:
                # 检查站点停靠
                if self.check_station_stop():
                    if 24270.31 <= self.position <= 24280.31:
                        self.status = "停站"
                        self.speed = 0
                        self.acceleration = 0
                        self.brake_acc = 0
                        self.traction_acc = 0
                        self.shanhou(dt)
                        status = self.get_status()
                        self.data_sender.send_data(status)
                        status["message"] = "仿真结束，列车到终点站，驾驶任务完成"
                        return status
                    
                    else:
                        if self.speed* 3.6 <= 3.6: #这样一次dt更新就能变成0（这个数有点大可能违反jerk限制，不过无所谓了。。）
                            self.status = "停站" #可以在加一个flag_stopped来判断是否停过站了，因为我们中间只停这一次所以可以这么来,或者直接把位置挪到22883.33，防止多次停站
                            self.speed = 0
                            self.acceleration = 0
                            self.brake_acc = 0
                            self.traction_acc = 0
                            self.stop_start = self.time
                            self.shanhou(dt)
                            status = self.get_status()
                            self.data_sender.send_data(status)
                            status["message"] = "列车经停"
                            return status
                        else:
                            pass # 列车速度高于0.75km/h，不进行停靠

                # 正常运行更新
                speed_kmh = self.speed * 3.6
                self.resistance_acc = self.get_resistance(speed_kmh)

                if control_acc is not None:
                    self.acceleration = control_acc
                else:
                    if self.status == "正常运行：牵引":
                        self.acceleration = self.traction_acc + self.resistance_acc
                    elif self.status == "正常运行：制动":
                        if self.speed == 0:
                            self.acceleration = 0
                        else:
                            self.acceleration = -self.brake_acc + self.resistance_acc
                    else:  # 惰行状态
                        if self.speed == 0:
                            self.acceleration = 0
                        else:
                            self.acceleration = self.resistance_acc

                self.shanhou(dt)
                if result_message:
                    status = self.get_status()
                    self.data_sender.send_data(status)
                    status["message"] = result_message
                    return status
                status = self.get_status()
                self.data_sender.send_data(status)
                return self.get_status()

        except Exception as e:
            logger.error(f"仿真更新失败: {str(e)}")
            return {"error": str(e)}

    def shanhou(self, dt):
        old_speed = self.speed
        self.speed = max(0, old_speed + self.acceleration * dt)
        self.position += (old_speed + self.speed) * dt / 2
        
        # 检查指定位置
        specific_positions = [22878.32, 24275.31]
        for i, pos in enumerate(specific_positions):
            if self.position_counter <= i and self.position >= pos:
                self.position_counter += 1
                self.actual_time.append(self.time)  # 记录时间
                self.number_1.append(self.position_counter)  # 记录检测次序
        
        # 检查速度为 0
        if old_speed > 0 and self.speed == 0 and self.speed_zero_counter < 2:
            self.speed_zero_counter += 1
            self.actual_position.append(self.position)  # 记录距离
            self.number_2.append(self.speed_zero_counter)  # 记录检测次序
        
        # 发送实时数据
        data = {
            "actual_time": self.actual_time,
            "number_1": self.number_1,
            "actual_position": self.actual_position,
            "number_2": self.number_2,
            }
        self.data_sender.send_data(data)
            
        self.log_state()



    def check_station_stop(self):
        return (22873.32 <= self.position <= 22883.32 or  
                24270.31 <= self.position <= 24280.31)

    def get_status(self):
        return {
            "time": self.time,
            "position": self.position,
            "speed": self.speed * 3.6,
            "acceleration": self.acceleration,
            "status": self.status,
            "target_speed": self.get_target_speed(),
            'ceiling_speed': self.get_ceiling_speed()
        }

    def log_state(self):
        with open(self.log_filename, 'a', newline='', encoding='gbk') as f:
            writer = csv.writer(f)
            writer.writerow([
                f"{self.time:.1f}",
                f"{self.position:.4f}",
                f"{self.speed * 3.6:.2f}",
                f"{self.acceleration:.4f}",
                f"{self.traction_acc:.4f}",
                f"{self.brake_acc:.4f}",
                f"{self.resistance_acc:.4f}",
                self.status,
                f"{self.get_target_speed():.2f}",
                f"{self.get_ceiling_speed():.2f}"
            ])

    def get_target_speed(self, position=None):
        if position is None:
            position = self.position
        return float(self.target_speed_interp(position))

    def get_ceiling_speed(self, position=None):
        if position is None:
            position = self.position
        return float(self.ceiling_speed_interp(position))

    def set_traction_acc(self, value):
        if self.status != "正常运行：牵引":
            return
        speed_kmh = self.speed * 3.6
        max_traction = float(self.traction_acc_interp(speed_kmh))
        self.traction_acc = max(0, min(value, max_traction))

    def set_brake_acc(self, value):
        if self.status != "正常运行：制动":
            return
        speed_kmh = self.speed * 3.6
        max_brake = float(self.brake_acc_interp(speed_kmh))
        self.brake_acc = max(0, min(value, -max_brake))

