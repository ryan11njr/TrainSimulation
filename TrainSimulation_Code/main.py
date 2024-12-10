# main.py
import sys
import os
import logging
from datetime import datetime
from PyQt5.QtWidgets import QApplication, QMessageBox
from PyQt5.QtCore import Qt
import csv
import matplotlib.pyplot as plt

from gui import MainWindow

def setup_logging():
    """设置日志系统"""
    try:
        # 创建logs目录
        if not os.path.exists('logs'):
            os.makedirs('logs')
        
        # 生成日志文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        log_filename = f'logs/train_simulation_{timestamp}.log'

        # 配置日志系统
        logging.basicConfig(
            level=logging.INFO,
            format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
            handlers=[
                logging.FileHandler(log_filename, encoding='utf-8'),
                logging.StreamHandler(sys.stdout)
            ]
        )
        
        logger = logging.getLogger(__name__)
        logger.info("日志系统初始化完成")
        return logger
        
    except Exception as e:
        print(f"日志系统初始化失败: {e}")
        sys.exit(1)

def setup_matplotlib():
    """配置matplotlib设置"""
    try:
        # 设置中文字体支持
        plt.rcParams["font.sans-serif"] = ["SimHei", "Microsoft YaHei"]  
        plt.rcParams["axes.unicode_minus"] = False
        
        # 设置图表默认大小和DPI
        plt.rcParams['figure.figsize'] = [10.0, 6.0]
        plt.rcParams['figure.dpi'] = 100
        plt.rcParams['savefig.dpi'] = 100
        
        # 设置默认网格样式
        plt.rcParams['grid.linestyle'] = '--'
        plt.rcParams['grid.alpha'] = 0.6
        
    except Exception as e:
        logging.error(f"Matplotlib配置失败: {e}")
        raise

def check_data_files():
    """检查必要的数据文件是否存在"""
    required_files = [
        '列车目标速度曲线.xlsx',
        'ATP顶棚速度数据.xls',
        '制动特性曲线.xls', 
        '牵引特性曲线.xls'  
    ]
    missing_files = []
    for file in required_files:
        if not os.path.exists(file):
            missing_files.append(file)
    return missing_files

def create_directories():
    """创建必要的目录"""
    try:
        directories = ['logs']
        for directory in directories:
            if not os.path.exists(directory):
                os.makedirs(directory)
                logging.info(f"创建目录: {directory}")
    except Exception as e:
        logging.error(f"创建目录失败: {e}")
        raise

def main():
    """主函数"""
    try:
        # 设置日志系统
        logger = setup_logging()
        logger.info("列车驾驶仿真软件启动")
        
        # 创建必要的目录
        create_directories()
        
        # 检查数据文件
        missing_files = check_data_files()
        if missing_files:
            message = f"缺少以下数据文件:\n{chr(10).join(missing_files)}"
            logger.error(message)
            QMessageBox.critical(None, "错误", message)
            sys.exit(1)
            
        # 配置matplotlib
        setup_matplotlib()
        
        # 设置高DPI支持
        QApplication.setAttribute(Qt.AA_EnableHighDpiScaling)
        QApplication.setAttribute(Qt.AA_UseHighDpiPixmaps)
        
        # 创建应用程序
        app = QApplication(sys.argv)
        app.setStyle('Fusion')  # 使用Fusion风格主题
        app.setApplicationName("列车驾驶仿真软件")
        
        # 创建并显示主窗口
        window = MainWindow()
        window.show()
        
        logger.info("应用程序初始化完成")
        sys.exit(app.exec_())
        
    except Exception as e:
        logger.error(f"应用程序启动失败: {e}", exc_info=True)
        QMessageBox.critical(None, "错误", f"应用程序启动失败: {str(e)}")
        sys.exit(1)

def cleanup():
    """清理资源"""
    try:
        plt.close('all')  # 关闭所有matplotlib图表
        
        # 获取主窗口实例并清理资源
        app = QApplication.instance()
        if app:
            for window in app.topLevelWidgets():
                if isinstance(window, MainWindow):
                    if hasattr(window, 'simulation'):
                        window.simulation.cleanup()
        
        logging.shutdown()  # 关闭日志系统
    except Exception as e:
        print(f"清理资源失败: {e}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"程序异常退出: {e}")
    finally:
        cleanup()