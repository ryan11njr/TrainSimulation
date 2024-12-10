import sys
import os
from datetime import datetime
from PyQt5.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                           QHBoxLayout, QLabel, QPushButton, QTextEdit, 
                           QFileDialog, QGroupBox, QMessageBox, QProgressBar)
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtNetwork import QTcpServer, QTcpSocket
import pandas as pd
import numpy as np
import json
import logging

class EvaluationMetrics:
    """评价指标计算类"""
    @staticmethod
    def calculate_overshoot(actual_speed, target_speed):
        """计算超调量"""
        if target_speed == 0:
            return 0
        overshoot = max(0, (actual_speed - target_speed) / target_speed * 100)
        return overshoot

    @staticmethod
    def calculate_comfort_level(acceleration):
        """计算舒适度"""
        abs_acc = abs(acceleration)
        if abs_acc <= 0.28:
            return 1, "极舒适"
        elif abs_acc <= 1.23:
            return 2, "舒适"
        elif abs_acc <= 2.12:
            return 3, "不舒适"
        else:
            return 4, "无法忍受"

    @staticmethod
    def calculate_punctuality(actual_time, number):
        """计算准点率"""
        if number == 1:
            if abs(actual_time-98.2) <= 5:
                in_time = 1
            else:
                in_time = 0
        else:
            if abs(actual_time-228.6) <= 5:
                in_time = 1
            else:
                in_time = 0
        return in_time

    @staticmethod
    def calculate_stopping_error(actual_position, number):
        """计算停车误差"""
        if number == 1:
            stopping_error = abs(actual_position-22878.32)
        else:
            stopping_error = abs(actual_position-24275.31)
        return stopping_error

class EvaluationSystem(QMainWindow):
    """评价系统主窗口"""
    def __init__(self):
        super().__init__()
        self.setWindowTitle('列车驾驶评价系统')
        self.setGeometry(100, 100, 800, 600)
        
        # 初始化状态变量
        self.tcp_server = None
        self.client_socket = None
        self.real_time_data = []
        
        # 初始化界面
        self.setup_ui()
        
        # 初始化TCP服务器
        self.setup_tcp_server()
        
        # 创建定时器用于实时评价更新
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self.update_realtime_evaluation)
        self.update_timer.start(1000)  # 每秒更新一次

    def setup_ui(self):
        """初始化用户界面"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        """ 用户界面上部，连接状态组 """
        # 创建连接状态组
        connection_group = QGroupBox("连接状态")
        connection_layout = QHBoxLayout()
        self.status_label = QLabel("等待连接...")
        connection_layout.addWidget(self.status_label)
        connection_group.setLayout(connection_layout)
        layout.addWidget(connection_group)
        
        """ 用户界面中上部，实时评价组 """
        # 创建实时评价组
        realtime_group = QGroupBox("实时评价")
        realtime_layout = QVBoxLayout()

        # 实时评价组标签显示
        self.overshoot_label = QLabel("超调量: 0%")
        self.comfort_label = QLabel("舒适度: 极舒适")
        self.speed_deviation_label = QLabel("与目标速度偏差: 0km/h")
        self.speed_deviation_label_percent = QLabel("与目标速度偏差百分比: 0%")
        
        # 将标签添加入实时评价组
        for label in [self.overshoot_label, self.comfort_label, self.speed_deviation_label, self.speed_deviation_label_percent]:
            realtime_layout.addWidget(label)
            
        realtime_group.setLayout(realtime_layout)
        layout.addWidget(realtime_group)

        """ 用户界面中下部，评价交流组 """
        # 创建交流组
        communication_group = QGroupBox("实时评价交流")
        communication_layout = QVBoxLayout()
        
        # 添加各项评价指标的显示
        self.ATP_TRIGGERED = QLabel("ATP触发情况: 暂无")
        self.encoragement_label = QLabel("就绪")

        # 将标签添加入交流组
        for label in [self.ATP_TRIGGERED, self.encoragement_label]:
            communication_layout.addWidget(label)
            
        communication_group.setLayout(communication_layout)
        layout.addWidget(communication_group)

        # 添加一个重置按钮
        self.reset_online_evaluation_button = QPushButton("重置实时评价界面")
        self.reset_online_evaluation_button.clicked.connect(self.reset_evaluation)
        layout.addWidget(self.reset_online_evaluation_button)
        
        """ 用户界面下部，离线评价组 """
        # 创建离线评价组
        offline_group = QGroupBox("离线评价")
        offline_layout = QVBoxLayout()
        
        # 添加评价结果显示区域
        self.result_text = QTextEdit()
        self.result_text.setReadOnly(True)
        offline_layout.addWidget(self.result_text)
        
        offline_group.setLayout(offline_layout)
        layout.addWidget(offline_group)
        
        # 添加文件选择按钮
        self.file_button = QPushButton("选择CSV文件")
        self.file_button.clicked.connect(self.select_file)
        offline_layout.addWidget(self.file_button)

        # 添加文件保存按钮
        self.save_button = QPushButton("保存离线评价结果")
        self.save_button.clicked.connect(self.save_result)
        offline_layout.addWidget(self.save_button)

        # 添加清空按钮
        self.clear_button = QPushButton("清空离线评价结果")
        self.clear_button.clicked.connect(self.clear_result)
        offline_layout.addWidget(self.clear_button)

        # 将以上三个按钮水平并排放置在离线评价组下方
        offline_hlayout = QHBoxLayout()
        offline_hlayout.addWidget(self.file_button)
        offline_hlayout.addWidget(self.save_button)
        offline_hlayout.addWidget(self.clear_button)
        offline_layout.addLayout(offline_hlayout)
        

    def setup_tcp_server(self):
        """初始化TCP服务器"""
        self.tcp_server = QTcpServer()
        if not self.tcp_server.listen(port=5000):
            QMessageBox.critical(self, "错误", "无法启动服务器")
            return
            
        self.tcp_server.newConnection.connect(self.handle_new_connection)
        self.status_label.setText("服务器已启动，等待连接...")

    def handle_new_connection(self):
        """处理新的客户端连接"""
        self.client_socket = self.tcp_server.nextPendingConnection()
        self.client_socket.readyRead.connect(self.handle_client_data)
        self.client_socket.disconnected.connect(self.handle_client_disconnect)
        self.status_label.setText("客户端已连接")

    def handle_client_data(self):
        """处理接收到的客户端数据"""
        try:
            data = self.client_socket.readAll().data().decode()
            sim_data = json.loads(data)
            
            # 更新评价数据
            self.actual_time = sim_data.get("actual_time", [])
            self.number_1 = sim_data.get("number_1", [])
            self.actual_position = sim_data.get("actual_position", [])
            self.number_2 = sim_data.get("number_2", [])
            
            self.real_time_data.append(sim_data)
            self.update_realtime_evaluation()
        except Exception as e:
            logging.error(f"数据处理错误: {str(e)}")

    def handle_client_disconnect(self):
        """处理客户端断开连接"""
        self.client_socket = None
        self.status_label.setText("客户端已断开")

    def update_realtime_evaluation(self):
        """更新实时评价显示"""
        # 在命名变量前检查有没有同名变量，如果没有则初始化
        if not hasattr(self, "actual_time"):
            self.actual_time = []
        if not hasattr(self, "number_1"):
            self.number_1 = []
        if not hasattr(self, "actual_position"):
            self.actual_position = []
        if not hasattr(self, "number_2"):
            self.number_2 = []
        
        if not self.real_time_data:
            return
            
        current_data = self.real_time_data[-1]
        
        # 计算超调量
        overshoot = EvaluationMetrics.calculate_overshoot(
            current_data['speed'],
            current_data['target_speed']
        )
        self.overshoot_label.setText(f"超调量: {overshoot:.2f}%")

        # 实际速度与目标速度偏差（大小）
        deviation = current_data['speed'] - current_data['target_speed']
        self.speed_deviation_label.setText(f"与目标速度偏差: {deviation:.2f}km/h")

        # 实际速度与目标速度偏差（百分比）
        deviation_percent = abs(deviation / current_data['target_speed'] * 100)
        self.speed_deviation_label_percent.setText(f"与目标速度偏差百分比: {deviation_percent:.2f}%")
        
        # 计算舒适度
        comfort_text = EvaluationMetrics.calculate_comfort_level(
            current_data['acceleration']
        )
        self.comfort_label.setText(f"舒适度: {comfort_text}")
        
        # 如果当前状态为紧急制动，则将ATP警告显示为“ATP警告: 警告”
        if current_data["status"]=="ATP紧急制动":
            self.ATP_TRIGGERED.setText("很遗憾，您触发了ATP紧急制动，请及时处理！")
        
        # 更新encoragement_label
        if current_data['status']=="ATP紧急制动":
            # 字号为20，颜色为红色
            self.encoragement_label.setStyleSheet("font-size:20px;color:red;")
            self.encoragement_label.setText("ATP紧急制动中")
        
        elif abs(deviation / current_data['target_speed'])>0.05:
            if current_data['speed']>current_data['target_speed']:
                 # 字号为20，颜色为红色
                self.encoragement_label.setStyleSheet("font-size:20px;color:red;")
                self.encoragement_label.setText("速度过快，请减速！")

            else:
                # 字号为20，颜色为蓝色
                self.encoragement_label.setStyleSheet("font-size:20px;color:blue;")
                self.encoragement_label.setText("速度过慢，请加速！")
                
        else:
            # 字号为20，颜色为绿色
            self.encoragement_label.setStyleSheet("font-size:20px;color:green;")
            self.encoragement_label.setText("速度恰好，请保持！")


    def reset_evaluation(self):
        """重置实时评价界面"""
        self.overshoot_label.setText("与目标速度平均相对偏差: 0%")
        self.comfort_label.setText("舒适度: 极舒适")
        self.speed_deviation_label.setText("与目标速度偏差: 0km/h")
        self.speed_deviation_label_percent.setText("与目标速度偏差百分比: 0%")
        self.ATP_TRIGGERED.setText("ATP触发情况: 暂无")
        # 字号为20，颜色为黑色
        self.encoragement_label.setStyleSheet("font-size:16px;color:black;text-align:center;")
        self.encoragement_label.setText("就绪")

        self.real_time_data = []

    def select_file(self):
        """选择CSV文件进行离线评价"""
        file_name, _ = QFileDialog.getOpenFileName(
            self,
            "选择CSV文件",
            "",
            "CSV Files (*.csv)"
        )
        
        if file_name:
            self.evaluate_offline_data(file_name)
    
    def save_result(self):
        """保存离线评价结果"""
        # 在按下“保存离线评价结果”按钮时，将评价结果显示区域中的内容保存为txt文件，并询问用户文件的保存路径。
        file_name, _ = QFileDialog.getSaveFileName(
            self,
            "保存评价结果",
            "",
            "Text Files (*.txt)"
        )
        
        if file_name:
            with open(file_name, "w", encoding="gb2312") as f:
                f.write(self.result_text.toPlainText())
        # 弹出提示框，提示保存成功
        QMessageBox.information(self, "提示", "离线评价结果保存成功")

    def clear_result(self):
        """清空离线评价结果"""
        self.result_text.clear()


    def evaluate_offline_data(self, file_path):
        """评价离线数据"""
        try:
            # 读取离线数据，读取第一行为标题行
            df = pd.read_csv(file_path, encoding='gb2312')
            # 读取时间表数据，相对路径为Simulation_V1.1\列车目标速度曲线.xlsx
            time_table=pd.read_excel(r'./列车目标速度曲线.xlsx')
            # 从df中筛选出Operating Condition不为停站的行，保存为df_on_rail
            df_on_rail = df[df["Operating Condition"]!="停站"]

            # 计算评价指标
            results = {
                # 列车运行平稳性指标
                "与目标速度平均相对偏差": 0, # 与目标速度平均相对偏差，实际运行速度与目标速度差的绝对值除以目标速度
                "极舒适时间占比": 0, # 舒适度为“极舒适”的总时间占比
                "舒适时间占比": 0, # 舒适度为”极舒适“与”舒适“的总时间占比
                "不舒适总时长": 0, # 舒适度为”不舒适“与”无法忍受“的总时间

                # 列车停站指标
                "实际到发时间列表": [],
                "目标到发时间列表": [],
                "准点率": 0, # 各站到站准点率与离站准点率
                "目标停车位置": [],
                "实际停车位置": [],
                "是否完成所有停站任务":[],
                "停车误差": [],
                "平均停车误差": 0, # 各站停车误差的平均值
            }
            

            # 计算各项指标
            """ 与目标速度平均相对偏差 """
            sum = 0
            # 计算和
            for i in range(0,len(df_on_rail)):
                sum += abs(df_on_rail.iloc[i]["Speed (km/h)"]-df_on_rail.iloc[i]["Target Speed (km/h)"])/df_on_rail.iloc[i]["Target Speed (km/h)"]
            
            #计算与目标速度平均相对偏差
            results["与目标速度平均相对偏差"] = sum/(len(df_on_rail))



            """ 舒适度统计 """
            # 统计舒适度为“极舒适”的总时间占比，注意，我们评价的是运行过程中的舒适度，故分母中的总时间不包括停车时间。
            comfort_time=0
            for i in range(0,len(df_on_rail)):
                if abs(df_on_rail.iloc[i]["Total Acceleration (m/s^2)"])<=0.28:
                    comfort_time+=1

            # 将极舒适时间占比写入results字典中
            results["极舒适时间占比"] = 100*comfort_time/(len(df_on_rail['Simulation Time (s)']))

            # 统计舒适度为“极舒适”或“舒适”的总时间占比，注意，我们评价的是运行过程中的舒适度，故分母中的总时间不包括停车时间。
            mid_comfort_time=0
            for i in range(0,len(df_on_rail)):
                if abs(df_on_rail.iloc[i]["Total Acceleration (m/s^2)"])<=1.23:
                    mid_comfort_time+=1

            # 将舒适时间占比写入results字典中
            results["舒适时间占比"] = 100*mid_comfort_time/(len(df_on_rail['Simulation Time (s)']))

            # 统计舒适度为”不舒适“或”无法忍受“的总时间
            un_comfort_time=0
            for i in range(0,len(df_on_rail)):
                if abs(df_on_rail.iloc[i]["Total Acceleration (m/s^2)"])>1.23:
                    un_comfort_time+=1

            # 将不舒适总时长写入results字典中
            results["不舒适总时长"] = un_comfort_time



            """ 准点率 """
            # 本次仿真只考虑中间站到站、中间站离站与终点站到站的时间。认为与时间表相比差距在60s以内的为准点。
            on_time_count = 0
            actual_stop_time = []
            for i in range(0,len(df)):
                # 遍历df中的各行，如果该行的Operating Condition为停站且与上一行或下一行不同，记录该行的Simulation Time (s)，并保存到数组actual_stop_time中
                if (i>0 and i<len(df)-1) and df.iloc[i]["Operating Condition"]=="停站":
                    if df.iloc[i]["Operating Condition"] != df.iloc[i-1]["Operating Condition"] or df.iloc[i]["Operating Condition"] != df.iloc[i+1]["Operating Condition"]:
                        actual_stop_time.append(df.iloc[i]["Simulation Time (s)"])
            # 将actual_stop_time数组中的所有元素写入results的“实际到发时间列表”数组中
            results["实际到发时间列表"] = actual_stop_time
            
            target_stop_time = []
            for i in range(0,len(time_table)):
                if(i>0 and i<len(time_table)-1) and (time_table.iloc[i]["列车速度（km/h）"]==0):
                    if (time_table.iloc[i]["列车速度（km/h）"]!=time_table.iloc[i-1]["列车速度（km/h）"] or time_table.iloc[i]["列车速度（km/h）"]!=time_table.iloc[i+1]["列车速度（km/h）"]):
                        target_stop_time.append(time_table.iloc[i]["仿真时间"])

            # 将target_stop_time数组中的所有元素写入results的“目标到发时间列表”数组中
            results["目标到发时间列表"] = target_stop_time
            
            # 计算准点率
            for i in range(len(actual_stop_time)):
                if abs(actual_stop_time[i]-target_stop_time[i])<=60:
                    on_time_count = on_time_count+1
            
            # 将准点率写入results字典中
            results["准点率"] = 100 * on_time_count/len(actual_stop_time)
            


            """ 停车误差与平均停车误差 """
            # 将目标停站位置写入数组target_stop_position中
            target_stop_position = []
            for i in range(len(time_table)):
                if time_table.iloc[i]["列车速度（km/h）"]==0:
                    # 对于已经记录的停站位置，不再重复记录
                    if (time_table.iloc[i]["列车位置"] not in target_stop_position) and time_table.iloc[i]["列车位置"]!=22880.2255:
                        target_stop_position.append(time_table.iloc[i]["列车位置"])
            
            # 将目标停车位置写入字典
            results["目标停车位置"] = target_stop_position

            # 将实际停站位置写入数组stop_position中
            stop_position = []
            for i in range(len(df)):
                if df.iloc[i]["Operating Condition"]=="停站":
                    # 对于已经记录的停站位置，不再重复记录
                    if df.iloc[i]["Position (m)"] not in stop_position:
                        stop_position.append(df.iloc[i]["Position (m)"])
            
            # 将实际停车位置写入字典
            results["实际停车位置"] = stop_position
            
            # 检查是否完成所有停站任务，若是，则继续计算平均停车误差
            if len(target_stop_position)!=len(stop_position):
                results["是否完成所有停站任务"]="未完成停站任务"
            else:
                results["是否完成所有停站任务"]="完成停站任务"
                # 将target_stop_position与stop_position数组对应元素相减并取绝对值，结果写入results的“停车误差”数组中
                results["停车误差"] = [abs(target_stop_position[i]-stop_position[i]) for i in range(len(target_stop_position))]
                # 对results的“停车误差”数组求平均值，并写入results的“平均停车误差”字段中
                results["平均停车误差"] = np.mean(results["停车误差"])
            
            
            """ 评价结果展示 """
            # 显示评价结果
            self.display_evaluation_results(results)
            
        except Exception as e:
            QMessageBox.critical(self, "错误", f"数据处理错误: {str(e)}")

    def display_evaluation_results(self, results):
        """显示评价结果"""
        report = "离线评价报告\n"
        report += "=" * 50 + "\n\n"

        # 小标题显示：列车运行平稳性指标
        report += "#列车运行平稳性指标\n"
        report += "=" * 50 + "\n\n"

        # 与目标速度平均相对偏差
        report += f"与目标速度平均相对偏差: {np.mean(results['与目标速度平均相对偏差']):.2f}%\n\n"
        
        # 极舒适时间占比
        report += f"极舒适时间占比: {results['极舒适时间占比']:.2f}%\n\n"

        # 舒适时间占比
        report += f"舒适时间占比: {results['舒适时间占比']:.2f}%\n\n"

        # 不舒适总时长
        report += f"不舒适总时长: {results['不舒适总时长']:.2f}s\n\n"

        # 小标题显示：列车停站指标
        report += "#列车停站指标\n"
        report += "=" * 50 + "\n"

        # 目标到发时间列表数组中的所有元素，并用空格分隔
        report+=f"\n目标到发时间列表: {results['目标到发时间列表']}\n"
        
        # 实际到发时间列表数组中的所有元素，并用空格分隔
        report+=f"\n实际到发时间列表: {results['实际到发时间列表']}\n"

        # 是否完成所有停站任务
        if results['是否完成所有停站任务']=="完成停站任务":
            # 准点率
            report += f"\n准点率: {results['准点率']:.2f}%\n"
        
            # 目标停车位置所有元素，并用空格分隔
            report += f"\n目标停车位置: {results['目标停车位置']}\n"

            # 实际停车位置所有元素，并用空格分隔
            report += f"\n实际停车位置: {results['实际停车位置']}\n"
        
            # 各站停车误差
            report += f"\n各站停车误差: {results['停车误差']}\n"

            # 平均停车误差
            report += f"\n平均停车误差: {results['平均停车误差']:.2f}m\n"
        else:
            report += f"\n{results['是否完成所有停站任务']}\n"
        
        self.result_text.setText(report)

def main():
    """主函数"""
    app = QApplication(sys.argv)
    window = EvaluationSystem()
    window.show()
    sys.exit(app.exec_())

if __name__ == "__main__":
    main()
