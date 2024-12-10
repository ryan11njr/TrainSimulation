# network_client.py
from PyQt5.QtNetwork import QTcpSocket
from PyQt5.QtCore import QTimer
import json
import logging

logger = logging.getLogger(__name__)

class SimulationDataSender:
    """仿真数据发送器，负责通过TCP发送仿真数据到评价系统"""
    def __init__(self, host='localhost', port=5000):
        self.host = host
        self.port = port
        self.socket = QTcpSocket()
        self.connected = False
        
        # 连接信号槽
        self.socket.connected.connect(self.handle_connected)
        self.socket.disconnected.connect(self.handle_disconnected)
        self.socket.error.connect(self.handle_error)
        
        # 创建重连定时器
        self.reconnect_timer = QTimer()
        self.reconnect_timer.timeout.connect(self.try_connect)
        self.reconnect_timer.setInterval(5000)  # 5秒重连间隔（单位：毫秒）
        
        logger.info("数据发送器初始化完成")
        
    def try_connect(self):
        """尝试连接到服务器"""
        if not self.connected:
            logger.info(f"正在连接到评价系统 {self.host}:{self.port}")
            self.socket.connectToHost(self.host, self.port)
            
    def start(self):
        """启动数据发送器"""
        self.try_connect()
        self.reconnect_timer.start()
        logger.info("数据发送器已启动")
        
    def stop(self):
        """停止数据发送器"""
        self.reconnect_timer.stop()
        if self.connected:
            self.socket.disconnectFromHost()
        logger.info("数据发送器已停止")
        
    def handle_connected(self):
        """处理连接成功事件"""
        self.connected = True
        self.reconnect_timer.stop()
        logger.info("已连接到评价系统")
        
    def handle_disconnected(self):
        """处理断开连接事件"""
        self.connected = False
        self.reconnect_timer.start()
        logger.info("与评价系统的连接已断开，将尝试重新连接")
        
    def handle_error(self, socket_error):
        """处理连接错误"""
        logger.error(f"网络连接错误: {self.socket.errorString()}")
        
    def send_data(self, simulation_data):
        """发送仿真数据"""
        try:
            if not self.connected:
                return
                
            # 构造要发送的数据
            data = {
                'time': simulation_data['time'],
                'position': simulation_data['position'],
                'speed': simulation_data['speed'],
                'acceleration': simulation_data['acceleration'],
                'target_speed': simulation_data.get('target_speed', 0),
                'ceiling_speed': simulation_data.get('ceiling_speed', 0),
                'status': simulation_data['status']
            }
            
            # 转换为JSON字符串
            json_data = json.dumps(data)
            
            
            # 发送数据
            self.socket.write(json_data.encode())
            
        except Exception as e:
            logger.error(f"发送数据失败: {str(e)}")