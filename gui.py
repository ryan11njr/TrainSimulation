# gui.py
from PyQt5.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
                           QGroupBox, QLabel, QPushButton, QComboBox, QTextEdit,
                           QMessageBox, QFrame, QGridLayout, QSpacerItem, QSizePolicy)
from PyQt5.QtCore import Qt, QTimer, QSize
from PyQt5.QtGui import QFont, QPalette, QColor, QIcon, QPainter, QLinearGradient
import logging
import numpy as np
import os
from datetime import datetime
import csv

from widgets import SpeedGaugeWidget, AccelerationGaugeWidget, MatplotlibWidget
from simulation import TrainSimulation
from pid import TrainSpeedController

logger = logging.getLogger(__name__)

class ModernGroupBox(QGroupBox):
    """现代风格的GroupBox"""
    def __init__(self, title, parent=None):
        super().__init__(title, parent)
        self.setStyleSheet("""
            QGroupBox {
                background-color: dark;
                border: 1px solid #e0e0e0;
                border-radius: 8px;
                margin-top: 1em;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px;
                color: #2563eb;
            }
        """)

class ModernButton(QPushButton):
    """现代风格的按钮"""
    def __init__(self, text="", parent=None):
        super().__init__(text, parent)
        self.setMinimumSize(QSize(40, 40))
        self.setCursor(Qt.PointingHandCursor)
        self.setStyleSheet("""
            QPushButton {
                background-color: #f3f4f6;
                border: none;
                border-radius: 20px;
                color: #4b5563;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #e5e7eb;
            }
            QPushButton:pressed {
                background-color: #d1d5db;
            }
            QPushButton:disabled {
                background-color: #f3f4f6;
                color: #9ca3af;
            }
        """)

class ModernComboBox(QComboBox):
    """现代风格的下拉框"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setStyleSheet("""
            QComboBox {
                border: 1px solid #e0e0e0;
                border-radius: 4px;
                padding: 5px;
                background-color: white;
            }
            QComboBox::drop-down {
                border: none;
            }
            QComboBox::down-arrow {
                image: url(down_arrow.png);
                width: 12px;
                height: 12px;
            }
        """)

class MainWindow(QMainWindow):
    """主窗口类"""
    def __init__(self):
        super().__init__()
        try:
            # 设置窗口基本属性
            self.setWindowTitle('列车驾驶仿真软件')
            self.setGeometry(100, 100, 1280, 800)
            self.setMinimumSize(1000, 600)
            
            # 设置应用样式
            self.setStyleSheet("""
                QMainWindow {
                    background-color: #f9fafb;
                }
                QLabel {
                    color: #374151;
                }
                QTextEdit {
                    border: 1px solid #e0e0e0;
                    border-radius: 4px;
                    background-color: white;
                    padding: 5px;
                }
            """)
            
            # 初始化状态变量
            self.is_running = False
            self.is_manual = True
            self.actual_positions = []
            self.actual_speeds = []
            self.simulation_speed = 1
            
            # 初始化界面
            self.setup_ui()
            
            # 初始化仿真系统
            self.setup_simulation()
            
            # 创建定时器
            self.sim_timer = QTimer()
            self.sim_timer.timeout.connect(self.update_simulation)
            self.base_interval = 100  # 100ms = 10Hz
            
            logger.info("主窗口初始化完成")
            
        except Exception as e:
            logger.error(f"主窗口初始化失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"初始化失败: {str(e)}")

    def create_info_section(self):
        """创建顶部信息区域"""
        info_layout = QHBoxLayout()
        
        # 基本信息组
        info_group = ModernGroupBox("列车基本信息")
        info_grid = QGridLayout()
        
        params = [
            ("车长:", "23.4m"),
            ("列车编组:", "6编组4动2拖"),
            ("列车质量:", "194.295×10³ kg")
        ]
        
        for i, (label_text, value_text) in enumerate(params):
            label = QLabel(label_text)
            value = QLabel(value_text)
            value.setStyleSheet("font-weight: bold; color: #2563eb;")
            info_grid.addWidget(label, i, 0)
            info_grid.addWidget(value, i, 1)
            
        info_group.setLayout(info_grid)
        info_layout.addWidget(info_group)
        
        # 实时状态组
        status_group = ModernGroupBox("实时状态")
        status_grid = QGridLayout()
        
        self.status_labels = {}
        status_items = {
            "工况": "正常运行：惰行",
            "驾驶模式": "人工驾驶",
            "速度": "0.0 km/h",
            "位置": "21604.2803 m",
            "时间": "0.0 s"
        }
        
        row = 0
        col = 0
        for key, value in status_items.items():
            container = QFrame()
            container.setStyleSheet("""
                QFrame {
                    background-color: #f3f4f6;
                    border-radius: 8px;
                    padding: 10px;
                }
            """)
            container_layout = QVBoxLayout(container)
            
            title = QLabel(key)
            title.setStyleSheet("color: #6b7280; font-size: 12px;")
            value_label = QLabel(value)
            value_label.setStyleSheet("color: #2563eb; font-weight: bold; font-size: 16px;")
            
            container_layout.addWidget(title)
            container_layout.addWidget(value_label)
            
            self.status_labels[key] = value_label
            status_grid.addWidget(container, row, col)
            
            col += 1
            if col > 1:
                col = 0
                row += 1
                
        status_group.setLayout(status_grid)
        info_layout.addWidget(status_group)
        
        return info_layout

    def create_control_section(self):
        """创建底部控制区域"""
        control_layout = QVBoxLayout()
        
        # 控制按钮组
        control_group = ModernGroupBox("仿真控制")
        button_layout = QHBoxLayout()
        
        # 创建控制按钮
        self.start_button = ModernButton("开始仿真")
        self.stop_button = ModernButton("结束仿真")
        self.reset_button = ModernButton("重置仿真")
        
         # 驾驶模式选择
        mode_label = QLabel("驾驶模式:")
        self.mode_combo = ModernComboBox()
        self.mode_combo.addItems(["人工驾驶", "自动驾驶"])
        self.mode_combo.currentTextChanged.connect(self.change_drive_mode)
        
        # 仿真速度选择
        speed_label = QLabel("仿真速度:")
        self.speed_combo = ModernComboBox()
        self.speed_combo.addItems(["1倍速", "2倍速", "5倍速", "10倍速"])
        
        for button in [self.start_button, self.stop_button, self.reset_button]:
            button_layout.addWidget(button)
    
        button_layout.addWidget(mode_label)
        button_layout.addWidget(self.mode_combo)
        button_layout.addWidget(speed_label)
        button_layout.addWidget(self.speed_combo)
        button_layout.addStretch()
        
        control_group.setLayout(button_layout)
        control_layout.addWidget(control_group)
        
        # 消息显示区域
        message_group = ModernGroupBox("运行信息")
        message_layout = QVBoxLayout()
        self.message_box = QTextEdit()
        self.message_box.setReadOnly(True)
        self.message_box.setMaximumHeight(100)
        self.message_box.setStyleSheet("""
            QTextEdit {
                background-color: #f9fafb;
                border: 1px solid #e5e7eb;
                border-radius: 8px;
                padding: 10px;
                color: #374151;
            }
        """)
        message_layout.addWidget(self.message_box)
        message_group.setLayout(message_layout)
        control_layout.addWidget(message_group)
        
        return control_layout

    def setup_ui(self):
        """初始化用户界面"""
        try:
            # 创建中心部件
            central_widget = QWidget()
            self.setCentralWidget(central_widget)
            main_layout = QVBoxLayout(central_widget)
            main_layout.setContentsMargins(20, 20, 20, 20)
            main_layout.setSpacing(20)
            
            # 创建顶部信息栏
            top_layout = self.create_info_section()
            main_layout.addLayout(top_layout)
            
            # 创建中部显示区域
            middle_layout = QHBoxLayout()
            
            # 速度-位置图表
            plot_group = ModernGroupBox("速度-位置曲线")
            plot_layout = QVBoxLayout()
            self.plot_widget = MatplotlibWidget()
            plot_layout.addWidget(self.plot_widget)
            plot_group.setLayout(plot_layout)
            middle_layout.addWidget(plot_group, stretch=2)
            
            # 仪表盘区域
            gauge_group = ModernGroupBox("列车状态仪表")
            gauge_layout = QVBoxLayout()
            
            self.speed_gauge = SpeedGaugeWidget()
            self.acc_gauge = AccelerationGaugeWidget()
            gauge_layout.addWidget(self.speed_gauge)
            gauge_layout.addWidget(self.acc_gauge)
            
            gauge_group.setLayout(gauge_layout)
            middle_layout.addWidget(gauge_group)
            
            main_layout.addLayout(middle_layout, stretch=1)
            
            # 创建底部控制栏
            bottom_layout = self.create_control_section()
            main_layout.addLayout(bottom_layout)
            
            # 连接信号
            self.start_button.clicked.connect(self.start_simulation)
            self.stop_button.clicked.connect(self.stop_simulation)
            self.reset_button.clicked.connect(self.reset_simulation)
            self.mode_combo.currentTextChanged.connect(self.change_drive_mode)
            self.speed_combo.currentTextChanged.connect(self.update_simulation_speed)
            
            logger.info("界面初始化完成")
            
        except Exception as e:
            logger.error(f"界面初始化失败: {str(e)}")
            raise

    def create_info_section(self):
        """创建顶部信息区域"""
        top_layout = QHBoxLayout()
        
        # 基本信息组
        info_group = QGroupBox("列车基本信息")
        info_layout = QVBoxLayout()
        
        params = [
            ("车长:", "23.4m"),
            ("列车编组:", "6编组4动2拖"),
            ("列车质量:", "194.295×10³ kg")
        ]
        
        for label_text, value_text in params:
            param_layout = QHBoxLayout()
            label = QLabel(label_text)
            value = QLabel(value_text)
            param_layout.addWidget(label)
            param_layout.addWidget(value)
            param_layout.addStretch()
            info_layout.addLayout(param_layout)
            
        info_group.setLayout(info_layout)
        top_layout.addWidget(info_group)
        
        # 实时状态组
        status_group = QGroupBox("实时状态")
        status_layout = QVBoxLayout()
        
        self.status_labels = {}
        status_items = {
            "工况": "当前工况: 正常运行：惰行",
            "驾驶模式": "当前驾驶模式: 人工驾驶",
            "速度": "当前速度: 0.0 km/h",
            "位置": "当前位置: 21604.2803 m",
            "时间": "仿真时间: 0.0 s"
        }
        
        for key, initial_text in status_items.items():
            label = QLabel(initial_text)
            self.status_labels[key] = label
            status_layout.addWidget(label)
            
        status_group.setLayout(status_layout)
        top_layout.addWidget(status_group)
        
        return top_layout

    def create_display_section(self):
        """创建中部显示区域"""
        middle_layout = QHBoxLayout()
        
        # 速度-位置图表
        plot_group = QGroupBox("速度-位置曲线")
        plot_layout = QVBoxLayout()
        self.plot_widget = MatplotlibWidget()
        plot_layout.addWidget(self.plot_widget)
        plot_group.setLayout(plot_layout)
        middle_layout.addWidget(plot_group, stretch=2)
        
        # 仪表盘区域
        gauge_group = QGroupBox("列车状态仪表")
        gauge_layout = QVBoxLayout()
        
        # 速度仪表盘
        speed_label = QLabel("速度仪表盘")
        self.speed_gauge = SpeedGaugeWidget()
        gauge_layout.addWidget(speed_label)
        gauge_layout.addWidget(self.speed_gauge)
        
        # 加速度仪表盘
        acc_label = QLabel("加速度仪表盘")
        self.acc_gauge = AccelerationGaugeWidget()
        gauge_layout.addWidget(acc_label)
        gauge_layout.addWidget(self.acc_gauge)
        
        gauge_group.setLayout(gauge_layout)
        middle_layout.addWidget(gauge_group)
        
        return middle_layout

    def create_control_section(self):
        """创建底部控制区域"""
        bottom_layout = QVBoxLayout()
        
        # 控制按钮区域
        control_group = QGroupBox("仿真控制")
        control_layout = QHBoxLayout()
        
        # 创建控制按钮
        self.start_button = QPushButton("开始仿真")
        self.stop_button = QPushButton("结束仿真")
        self.reset_button = QPushButton("重置仿真")
        
        # 驾驶模式选择
        self.mode_combo = QComboBox()
        self.mode_combo.addItems(["人工驾驶", "自动驾驶"])
        self.mode_combo.currentTextChanged.connect(self.change_drive_mode)
        
        # 仿真速度选择
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["1倍速", "2倍速", "5倍速", "10倍速"])
        
        # 连接信号
        self.start_button.clicked.connect(self.start_simulation)
        self.stop_button.clicked.connect(self.stop_simulation)
        self.reset_button.clicked.connect(self.reset_simulation)
        self.mode_combo.currentTextChanged.connect(self.change_drive_mode)
        self.speed_combo.currentTextChanged.connect(self.update_simulation_speed)
        
        # 添加到布局
        control_layout.addWidget(self.start_button)
        control_layout.addWidget(self.stop_button)
        control_layout.addWidget(self.reset_button)
        control_layout.addWidget(QLabel("驾驶模式:"))
        control_layout.addWidget(self.mode_combo)
        control_layout.addWidget(QLabel("仿真速度:"))
        control_layout.addWidget(self.speed_combo)
        control_layout.addStretch()
        
        control_group.setLayout(control_layout)
        bottom_layout.addWidget(control_group)
        
        # 消息显示区域
        message_group = QGroupBox("运行信息")
        message_layout = QVBoxLayout()
        self.message_box = QTextEdit()
        self.message_box.setReadOnly(True)
        self.message_box.setMaximumHeight(100)
        message_layout.addWidget(self.message_box)
        message_group.setLayout(message_layout)
        bottom_layout.addWidget(message_group)
        
        return bottom_layout

    def setup_simulation(self):
        """初始化仿真系统"""
        try:
            self.simulation = TrainSimulation()
            self.controller = TrainSpeedController()
            self.reset_data_records()
            self.update_displays()
            self.show_message("仿真系统初始化完成")
            
        except Exception as e:
            logger.error(f"仿真系统初始化失败: {str(e)}")
            QMessageBox.critical(self, "错误", f"仿真系统初始化失败: {str(e)}")

    def start_simulation(self):
        """开始仿真"""
        try:
            if not self.is_running:
                self.is_running = True
                interval = self.base_interval / self.simulation_speed
                self.sim_timer.setInterval(int(interval))
                self.sim_timer.start()
                
                self.update_control_state(True)
                self.show_message("仿真开始")
                
        except Exception as e:
            logger.error(f"启动仿真失败: {str(e)}")
            self.show_message(f"错误: 启动仿真失败 - {str(e)}")

    def stop_simulation(self):
        """停止仿真"""
        try:
            if self.is_running:
                self.is_running = False
                self.sim_timer.stop()
                
                self.update_control_state(False)
                self.show_message("仿真结束")
                self.save_simulation_data()
                
        except Exception as e:
            logger.error(f"停止仿真失败: {str(e)}")
            self.show_message(f"错误: 停止仿真失败 - {str(e)}")

    def reset_simulation(self):
        """重置仿真"""
        try:
            if self.is_running:
                self.stop_simulation()
                
            self.simulation.reset()
            self.controller.reset()
            self.reset_data_records()
            self.update_displays()
            self.show_message("仿真已重置")
            
        except Exception as e:
            logger.error(f"重置仿真失败: {str(e)}")
            self.show_message(f"错误: 重置仿真失败 - {str(e)}")

    def change_drive_mode(self, mode_text):
        """切换驾驶模式"""
        try:
            self.is_manual = (mode_text == "人工驾驶")
            self.status_labels["驾驶模式"].setText(f"当前驾驶模式: {mode_text}")
            self.show_message(f"切换到{mode_text}模式")
            
        except Exception as e:
            logger.error(f"切换驾驶模式失败: {str(e)}")
            self.show_message(f"错误: 切换驾驶模式失败 - {str(e)}")

    def update_simulation_speed(self):
        """更新仿真速度"""
        try:
            speed_text = self.speed_combo.currentText()
            self.simulation_speed = int(speed_text.replace('倍速', ''))
            
            if self.is_running:
                interval = self.base_interval / self.simulation_speed
                self.sim_timer.setInterval(int(interval))
                
        except Exception as e:
            logger.error(f"更新仿真速度失败: {str(e)}")

    def update_simulation(self):
        """更新仿真状态"""
        try:
            if not self.is_running:
                return
                
            dt = 0.1 * self.simulation_speed
            
            # 计算控制输出（自动驾驶模式）
            control_acc = None
            if not self.is_manual:
                target_speed = self.simulation.get_target_speed()
                current_speed = self.simulation.speed * 3.6
                control_acc = self.controller.compute_control(
                    target_speed,
                    current_speed,
                    dt
                )
            
            # 更新仿真状态
            result = self.simulation.update(dt, control_acc)
            
            if "error" in result:
                raise Exception(result["error"])
                
            # 更新数据记录和显示
            self.update_data_records(result)
            self.update_displays(result)
            
            if result.get("message"):
                self.show_message(result["message"])
                if result["message"].startswith("仿真结束"):
                    self.show_message("仿真结束")
                    self.stop_simulation()
                
        except Exception as e:
            logger.error(f"仿真更新失败: {str(e)}")
            self.show_message(f"错误: 仿真更新失败 - {str(e)}")
            self.stop_simulation()

    def update_data_records(self, result):
        """更新数据记录"""
        if result["speed"] > 0 or self.actual_positions:
            self.actual_positions.append(result["position"])
            self.actual_speeds.append(result["speed"])


    def update_displays(self, result=None):
        """更新显示信息"""
        try:
            if result is None:
                result = self.simulation.get_status()
                
            # 更新状态标签
            self.status_labels["工况"].setText(f"当前工况: {result['status']}")
            self.status_labels["速度"].setText(f"当前速度: {result['speed']:.1f} km/h")
            self.status_labels["位置"].setText(f"当前位置: {result['position']:.4f} m")
            self.status_labels["时间"].setText(f"仿真时间: {result['time']:.1f} s")
            
            # 更新仪表盘
            self.speed_gauge.setValue(result["speed"])
            self.acc_gauge.setValue(result["acceleration"])
            
            # 更新图表
            self.update_plot()
            
        except Exception as e:
            logger.error(f"更新显示失败: {str(e)}")

    def update_plot(self):
        """更新速度-位置图表"""
        try:
            # 生成目标速度和顶棚速度曲线数据
            x_range = np.linspace(21604.2803, 24275.30985, 1000)
            target_speeds = [self.simulation.get_target_speed(x) for x in x_range]
            ceiling_speeds = [self.simulation.get_ceiling_speed(x) for x in x_range]
            
            # 绘制图表
            self.plot_widget.plot_data(
                x_range, target_speeds,
                x_range, ceiling_speeds,
                self.actual_positions, self.actual_speeds
            )
        except Exception as e:
            logger.error(f"更新图表失败: {str(e)}")

    def reset_data_records(self):
        """重置数据记录"""
        try:
            self.actual_positions.clear()
            self.actual_speeds.clear()
            self.update_plot()
        except Exception as e:
            logger.error(f"重置数据记录失败: {str(e)}")

    def save_simulation_data(self):
        """保存仿真数据"""
        try:
            # 创建保存目录
            save_dir = "logs"
            if not os.path.exists(save_dir):
                os.makedirs(save_dir)
                
            # 生成文件名
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            base_filename = os.path.join(save_dir, f"simulation_{timestamp}")
            
            # 保存运行数据
            #self.export_data_to_csv(f"{base_filename}.csv")
            
            # 保存速度曲线图
            self.plot_widget.save_plot(f"{base_filename}.png")
            
            self.show_message(f"仿真数据以及仿真过程记录已保存至 {save_dir} 目录")
            logger.info(f"仿真数据已保存: {base_filename}")
            
        except Exception as e:
            logger.error(f"保存仿真数据失败: {str(e)}")
            self.show_message(f"错误: 保存数据失败 - {str(e)}")

    def export_data_to_csv(self, filename):
        """导出数据到CSV文件"""
        try:
            with open(filename, 'w', newline='', encoding='utf-8') as file:
                writer = csv.writer(file)
                # 写入表头
                writer.writerow([
                    'loc(m)',
                    'actual_speed(km/h)',
                    'target_speed(km/h)',
                    'ceiling_speed(km/h)'
                ])
                
                # 写入数据
                for i, pos in enumerate(self.actual_positions):
                    target_speed = self.simulation.get_target_speed(pos)
                    ceiling_speed = self.simulation.get_ceiling_speed(pos)
                    writer.writerow([
                        f"{pos:.4f}",
                        f"{self.actual_speeds[i]:.2f}",
                        f"{target_speed:.2f}",
                        f"{ceiling_speed:.2f}"
                    ])
                    
        except Exception as e:
            logger.error(f"导出CSV数据失败: {str(e)}")
            raise

    def update_control_state(self, is_running):
        """更新控制按钮状态"""
        try:
            self.start_button.setEnabled(not is_running)
            self.stop_button.setEnabled(is_running)
            self.reset_button.setEnabled(not is_running)
            self.speed_combo.setEnabled(not is_running)
            self.mode_combo.setEnabled(not is_running)
        except Exception as e:
            logger.error(f"更新控制状态失败: {str(e)}")

    def show_message(self, message):
        """显示消息"""
        try:
            timestamp = self.simulation.time if hasattr(self, 'simulation') else 0
            formatted_message = f"[{timestamp:.1f}s] {message}"
            self.message_box.append(formatted_message)
            
            # 自动滚动到底部
            scrollbar = self.message_box.verticalScrollBar()
            scrollbar.setValue(scrollbar.maximum())
            
        except Exception as e:
            logger.error(f"显示消息失败: {str(e)}")

    def keyPressEvent(self, event):
        """处理键盘事件"""
        if not self.is_running or not self.is_manual:
            return
            
        try:
            if event.key() == Qt.Key_Q:
                self.handle_traction_key()
            elif event.key() == Qt.Key_W:
                self.handle_coasting_key()
            elif event.key() == Qt.Key_E:
                self.handle_brake_key()
            elif event.key() == Qt.Key_O:
                self.handle_increase_key()
            elif event.key() == Qt.Key_P:
                self.handle_decrease_key()
                
        except Exception as e:
            logger.error(f"键盘事件处理失败: {str(e)}")
            self.show_message(f"错误: 键盘控制失败 - {str(e)}")

    def handle_traction_key(self):
        """处理牵引按键"""
        status = self.simulation.status
        
        if status == "正常运行：牵引":
            return
        elif status == "正常运行：制动":
            self.simulation.status = "正常运行：惰行"
            self.simulation.brake_acc = 0.0
            self.show_message("已断开制动，并清除制动力。现在处于惰行工况，请再按下Q来切换牵引")
        elif status == "正常运行：惰行":
            self.simulation.status = "正常运行：牵引"
            self.show_message("已切换至牵引工况")
        else:
            self.show_message("当前状态无法切换至牵引工况")

    def handle_coasting_key(self):
        """处理惰行按键"""
        if self.simulation.status.startswith("正常运行"):
            self.simulation.traction_acc = 0.0
            self.simulation.brake_acc = 0.0
            self.simulation.status = "正常运行：惰行"
            self.show_message("已切换至惰行工况,断开牵引和制动力")

    def handle_brake_key(self):
        """处理制动按键"""
        status = self.simulation.status
        
        if status == "正常运行：制动":
            self.show_message("列车已处于制动工况，无需再次切换")
            return
        elif status == "正常运行：牵引":
            self.simulation.status = "正常运行：惰行"
            self.simulation.traction_acc = 0.0
            self.show_message("已断开牵引，并清除牵引力。现在处于惰行工况，请再按E来切换至制动工况")
        elif status == "正常运行：惰行":
            self.simulation.status = "正常运行：制动"
            self.show_message("已切换至制动工况")
        else:
            self.show_message("当前状态无法切换至制动工况")

    def handle_increase_key(self):
        """处理增加按键"""
        try:
            if self.simulation.status == "正常运行：牵引":
                current_acc = self.simulation.traction_acc
                new_acc = current_acc + 0.1
                self.simulation.set_traction_acc(new_acc)
                self.show_message(f"增加牵引加速度至 {new_acc:.1f} m/s²")
            elif self.simulation.status == "正常运行：制动":
                current_acc = self.simulation.brake_acc
                new_acc = current_acc + 0.1
                self.simulation.set_brake_acc(new_acc)
                self.show_message(f"增加制动加速度至 {new_acc:.1f} m/s²")
            else:
                self.show_message("当前状态无法增加起牵引或制动加速度")
        except Exception as e:
            logger.error(f"增加按键处理失败: {str(e)}")

    def handle_decrease_key(self):
        """处理减小按键"""
        try:
            if self.simulation.status == "正常运行：牵引":
                current_acc = self.simulation.traction_acc
                new_acc = current_acc - 0.1
                if new_acc < 0:
                    new_acc = 0.0
                self.simulation.set_traction_acc(new_acc)
                self.show_message(f"减小牵引加速度至 {new_acc:.1f} m/s²")
            elif self.simulation.status == "正常运行：制动":
                current_acc = self.simulation.brake_acc
                new_acc = current_acc - 0.1
                if new_acc < 0:
                    new_acc = 0.0
                if self.simulation.speed <= 0:
                    self.show_message(f"列车已停止，制动加速度已无法再减小")
                else:
                    self.show_message(f"减小制动加速度至 {new_acc:.1f} m/s²")
                self.simulation.set_brake_acc(new_acc)
            else:
                self.show_message("当前状态无法减小起牵引或制动加速度")
        except Exception as e:
            logger.error(f"减小按键处理失败: {str(e)}")

    def closeEvent(self, event):
        """窗口关闭事件处理"""
        try:
            if self.is_running:
                self.stop_simulation()
            
            # 保存最终日志
            if hasattr(self, 'simulation'):
                self.simulation.log_state()
                
            event.accept()
            
        except Exception as e:
            logger.error(f"关闭窗口失败: {str(e)}")
            event.accept()
