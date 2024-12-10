# widgets.py
from PyQt5.QtWidgets import QWidget, QVBoxLayout
from PyQt5.QtCore import Qt, QPoint, QRectF
from PyQt5.QtGui import (QPainter, QPen, QColor, QPainterPath, QFont, 
                        QLinearGradient, QRadialGradient)
import matplotlib.pyplot as plt
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
import numpy as np

class SpeedGaugeWidget(QWidget):
    """现代风格速度仪表盘控件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0
        self.setMinimumSize(200, 200)
        # 定义角度范围
        self.start_angle = -210  # 起始角度（左侧）
        self.end_angle = 30      # 结束角度（右侧）
        self.range_angle = self.end_angle - self.start_angle  # 总范围240度
        
    def setValue(self, value):
        """设置速度值（km/h）"""
        self.value = max(0, min(value, 120))  # 限制在0-120范围内
        self.update()
        
    def paintEvent(self, event):
        """绘制仪表盘"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 计算绘制区域
        width = self.width()
        height = self.height()
        center_x = width // 2
        center_y = height // 2  # 居中放置
        radius = min(width, height) // 2 - 20
        
        # 绘制外圈
        painter.save()
        painter.translate(center_x, center_y)
        
        # 绘制背景弧
        pen = QPen(QColor("#e5e7eb"), 10)
        painter.setPen(pen)
        painter.drawArc(-radius, -radius, radius*2, radius*2,
                       self.start_angle*16, self.range_angle*16)
        
        # 绘制刻度
        self.drawScale(painter, radius)
        
        # 绘制数值显示
        self.drawValue(painter, radius)
        
        # 绘制指针
        self.drawPointer(painter, radius)
        
        painter.restore()
        
    def drawScale(self, painter, radius):
        """绘制刻度"""
        # 主刻度间隔为20，绘制7个主刻度（0,20,40,60,80,100,120）
        for i in range(7):
            speed = i * 20
            angle = self.start_angle + (speed / 120) * self.range_angle
            
            # 计算颜色
            progress = speed / 120
            if progress < 0.5:
                color = QColor("#2563eb")  # 蓝色
            elif progress < 0.75:
                color = QColor("#eab308")  # 黄色
            else:
                color = QColor("#dc2626")  # 红色
                
            # 计算刻度位置
            rad_angle = angle * np.pi / 180
            x1 = int((radius - 25) * np.cos(rad_angle))
            y1 = int((radius - 25) * np.sin(rad_angle))
            x2 = int((radius - 10) * np.cos(rad_angle))
            y2 = int((radius - 10) * np.sin(rad_angle))
            
            # 绘制主刻度线
            painter.setPen(QPen(color, 3))
            painter.drawLine(x2, y2, x1, y1)
            
            # 绘制刻度值
            self.drawScaleNumber(painter, radius, angle, speed, color)
            
            # 绘制中间刻度（每10km/h一个）
            if i < 6:  # 不绘制最后一段的小刻度
                self.drawSubScale(painter, radius, speed, color)
                
    def drawScaleNumber(self, painter, radius, angle, speed, color):
        """绘制刻度数字"""
        rad_angle = angle * np.pi / 180
        text_x = int((radius - 45) * np.cos(rad_angle))
        text_y = int((radius - 45) * np.sin(rad_angle))
        
        painter.save()
        painter.translate(text_x, text_y)
        
        # 调整文本角度，使其更易读
        text_angle = angle
        if -180 <= angle <= 0:
            text_angle += 90
        else:
            text_angle -= 90
        painter.rotate(text_angle)
        
        font = QFont()
        font.setPointSize(10)
        painter.setFont(font)
        painter.setPen(color)
        painter.drawText(QRectF(-20, -10, 40, 20), Qt.AlignCenter, str(speed))
        painter.restore()
        
    def drawSubScale(self, painter, radius, start_speed, color):
        """绘制小刻度（中间刻度）"""
        # 在每个主刻度之间画一个中间刻度
        mid_speed = start_speed + 10
        mid_angle = self.start_angle + (mid_speed / 120) * self.range_angle
        mid_rad = mid_angle * np.pi / 180
        
        x1 = int((radius - 15) * np.cos(mid_rad))
        y1 = int((radius - 15) * np.sin(mid_rad))
        x2 = int((radius - 10) * np.cos(mid_rad))
        y2 = int((radius - 10) * np.sin(mid_rad))
        
        painter.setPen(QPen(color, 1))
        painter.drawLine(x2, y2, x1, y1)
            
    def drawValue(self, painter, radius):
        """绘制当前值显示"""
        # 绘制数值
        font = QFont()
        font.setPointSize(32)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(QColor("#2563eb"))
        value_text = f"{self.value:.0f}"
        painter.drawText(QRectF(-50, radius/2, 100, 40), Qt.AlignCenter, value_text)
        
        # 绘制单位
        font.setPointSize(12)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor("#6b7280"))
        painter.drawText(QRectF(-50, radius/2 + 30, 100, 30), Qt.AlignCenter, "km/h")
        
    def drawPointer(self, painter, radius):
        """绘制指针"""
        painter.save()
        
        # 计算指针角度
        angle = self.start_angle + (self.value / 120) * self.range_angle
        rad_angle = angle * np.pi / 180
        
        # 计算指针端点
        pointer_length = radius - 40
        x = pointer_length * np.cos(rad_angle)
        y = pointer_length * np.sin(rad_angle)
        
        # 创建指针形状
        pointer_width = 6
        perpendicular_angle = rad_angle + np.pi/2
        px = pointer_width * np.cos(perpendicular_angle)
        py = pointer_width * np.sin(perpendicular_angle)
        
        pointer = QPainterPath()
        pointer.moveTo(-px, -py)
        pointer.lineTo(x, y)
        pointer.lineTo(px, py)
        pointer.closeSubpath()
        
        # 创建指针渐变
        gradient = QLinearGradient(0, 0, x, y)
        gradient.setColorAt(0, QColor("#dc2626"))
        gradient.setColorAt(1, QColor("#ef4444"))
        
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawPath(pointer)
        
        # 绘制中心圆
        painter.setBrush(QColor("#dc2626"))
        painter.drawEllipse(QPoint(0, 0), 10, 10)
        
        # 绘制中心圆的高光效果
        painter.setBrush(QColor("#ffffff"))
        painter.setOpacity(0.3)
        painter.drawEllipse(QPoint(-2, -2), 4, 4)
        
        painter.restore()

class AccelerationGaugeWidget(QWidget):
    """现代风格加速度仪表盘控件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.value = 0
        self.setMinimumSize(200, 200)
        # 定义角度范围
        self.start_angle = -210  # 起始角度（左侧，对应-1.1）
        self.end_angle = 30      # 结束角度（右侧，对应+1.1）
        self.range_angle = self.end_angle - self.start_angle  # 总范围240度
        self.min_value = -1.1
        self.max_value = 1.1
        
    def setValue(self, value):
        """设置加速度值（m/s²）"""
        self.value = max(self.min_value, min(value, self.max_value))
        self.update()
        
    def paintEvent(self, event):
        """绘制仪表盘"""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.Antialiasing)
        
        # 计算绘制区域
        width = self.width()
        height = self.height()
        center_x = width // 2
        center_y = height // 2  # 居中放置
        radius = min(width, height) // 2 - 20
        
        # 绘制外圈
        painter.save()
        painter.translate(center_x, center_y)
        
        # 绘制背景弧
        pen = QPen(QColor("#e5e7eb"), 10)
        painter.setPen(pen)
        painter.drawArc(-radius, -radius, radius*2, radius*2,
                       self.start_angle*16, self.range_angle*16)
        
        # 绘制刻度
        self.drawScale(painter, radius)
        
        # 绘制数值显示
        self.drawValue(painter, radius)
        
        # 绘制指针
        self.drawPointer(painter, radius)
        
        painter.restore()
        
    def drawScale(self, painter, radius):
        """绘制刻度"""
        # 主刻度值为 -1.0, -0.5, 0, 0.5, 1.0
        scale_values = [-1.0, -0.5, 0.0, 0.5, 1.0]
        
        for value in scale_values:
            # 计算角度 - 将值映射到角度范围
            angle = self.start_angle + ((value - self.min_value) / 
                   (self.max_value - self.min_value)) * self.range_angle
            
            # 选择颜色
            if value < 0:
                color = QColor("#dc2626")  # 红色（减速）
            elif value > 0:
                color = QColor("#2563eb")  # 蓝色（加速）
            else:
                color = QColor("#6b7280")  # 灰色（零点）
                
            # 计算刻度位置
            rad_angle = angle * np.pi / 180
            x1 = int((radius - 25) * np.cos(rad_angle))
            y1 = int((radius - 25) * np.sin(rad_angle))
            x2 = int((radius - 10) * np.cos(rad_angle))
            y2 = int((radius - 10) * np.sin(rad_angle))
            
            # 绘制主刻度线
            painter.setPen(QPen(color, 3))
            painter.drawLine(x2, y2, x1, y1)
            
            # 绘制刻度值
            text_x = int((radius - 45) * np.cos(rad_angle))
            text_y = int((radius - 45) * np.sin(rad_angle))
            
            painter.save()
            painter.translate(text_x, text_y)
            
            # 调整文本角度，使其更易读
            text_angle = angle
            if -180 <= angle <= 0:
                text_angle += 90
            else:
                text_angle -= 90
            painter.rotate(text_angle)
            
            font = QFont()
            font.setPointSize(10)
            painter.setFont(font)
            painter.setPen(color)
            painter.drawText(QRectF(-25, -10, 50, 20), 
                           Qt.AlignCenter, f"{value:.1f}")
            painter.restore()
            
    def drawValue(self, painter, radius):
        """绘制当前值显示"""
        # 选择颜色
        if self.value < 0:
            color = QColor("#dc2626")  # 红色（减速）
        elif self.value > 0:
            color = QColor("#2563eb")  # 蓝色（加速）
        else:
            color = QColor("#6b7280")  # 灰色（零点）
        
        # 绘制数值
        font = QFont()
        font.setPointSize(32)
        font.setBold(True)
        painter.setFont(font)
        painter.setPen(color)
        value_text = f"{self.value:.2f}"
        painter.drawText(QRectF(-50, radius/2, 100, 40), Qt.AlignCenter, value_text)
        
        # 绘制单位
        font.setPointSize(12)
        font.setBold(False)
        painter.setFont(font)
        painter.setPen(QColor("#6b7280"))
        painter.drawText(QRectF(-50, radius/2 + 30, 100, 30), Qt.AlignCenter, "m/s²")
        
    def drawPointer(self, painter, radius):
        """绘制指针"""
        painter.save()
        
        # 计算指针角度
        angle = self.start_angle + ((self.value - self.min_value) / 
               (self.max_value - self.min_value)) * self.range_angle
        rad_angle = angle * np.pi / 180
        
        # 计算指针端点
        pointer_length = radius - 40
        x = pointer_length * np.cos(rad_angle)
        y = pointer_length * np.sin(rad_angle)
        
        # 创建指针形状
        pointer_width = 6
        perpendicular_angle = rad_angle + np.pi/2
        px = pointer_width * np.cos(perpendicular_angle)
        py = pointer_width * np.sin(perpendicular_angle)
        
        pointer = QPainterPath()
        pointer.moveTo(-px, -py)
        pointer.lineTo(x, y)
        pointer.lineTo(px, py)
        pointer.closeSubpath()
        
        # 创建指针渐变
        gradient = QLinearGradient(0, 0, x, y)
        if self.value < 0:
            gradient.setColorAt(0, QColor("#dc2626"))
            gradient.setColorAt(1, QColor("#ef4444"))
        else:
            gradient.setColorAt(0, QColor("#2563eb"))
            gradient.setColorAt(1, QColor("#60a5fa"))
        
        painter.setBrush(gradient)
        painter.setPen(Qt.NoPen)
        painter.drawPath(pointer)
        
        # 绘制中心圆
        painter.setBrush(QColor("#dc2626") if self.value < 0 else QColor("#2563eb"))
        painter.drawEllipse(QPoint(0, 0), 10, 10)
        
        # 绘制中心圆的高光效果
        painter.setBrush(QColor("#ffffff"))
        painter.setOpacity(0.3)
        painter.drawEllipse(QPoint(-2, -2), 4, 4)
        
        painter.restore()

class MatplotlibWidget(QWidget):
    """Matplotlib图表控件"""
    def __init__(self, parent=None):
        super().__init__(parent)
        # 创建图表
  
        self.figure = plt.figure(figsize=(8, 6), facecolor='#ffffff')
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111)
        
        # 设置布局
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.canvas)
        
        # 配置图表样式
        self.ax.grid(True, linestyle='--', alpha=0.6)
        self.ax.set_xlabel('位置 (m)', fontsize=10)
        self.ax.set_ylabel('速度 (km/h)', fontsize=10)
        self.ax.tick_params(labelsize=9)
        self.figure.tight_layout()
        
    def plot_data(self, x1, y1, x2, y2, x3=None, y3=None):
        """绘制速度曲线"""
        self.ax.clear()
        
        # 设置样式
        self.ax.set_facecolor('#f8fafc')
        self.ax.grid(True, linestyle='--', alpha=0.6, color='#cbd5e1')
        
        # 绘制曲线
        self.ax.plot(x1, y1, color='#2563eb', label='目标速度', 
                    linewidth=2, linestyle='-')
        self.ax.plot(x2, y2, color='#dc2626', label='顶棚速度', 
                    linewidth=2, linestyle='--')
        
        if x3 is not None and y3 is not None and len(x3) > 0:
            self.ax.plot(x3, y3, color='#eab308', label='实际速度', 
                        linewidth=2.5)
            
        # 设置图表属性
        self.ax.set_xlabel('位置 (m)', fontsize=10, color='#475569')
        self.ax.set_ylabel('速度 (km/h)', fontsize=10, color='#475569')
        self.ax.tick_params(colors='#475569')
        
        # 设置图例
        self.ax.legend(loc='upper right', fancybox=True, shadow=True)
        
        # 调整显示范围
        if x3 is not None and len(x3) > 0:
            self.ax.set_xlim(min(x1[0], x3[0]), max(x1[-1], x3[-1]))
            self.ax.set_ylim(0, max(max(y1), max(y2)) * 1.1)
            
        self.figure.tight_layout()
        self.canvas.draw()
        
    def save_plot(self, filename):
        """保存图表为图片"""
        self.figure.savefig(filename, dpi=100, bbox_inches='tight', 
                          facecolor='white', edgecolor='none')