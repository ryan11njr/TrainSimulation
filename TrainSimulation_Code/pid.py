# pid.py
import numpy as np
import logging
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

class PIDController:
    """PID控制器基类"""
    def __init__(
        self,
        kp: float = 1.0,
        ki: float = 0.0,
        kd: float = 0.0,
        output_limits: Optional[Tuple[float, float]] = None,
        sample_time: float = 0.1,
        anti_windup: bool = True
    ):
        # 控制参数
        self.kp = kp  # 比例增益
        self.ki = ki  # 积分增益
        self.kd = kd  # 微分增益
        
        # 控制器配置
        self.output_limits = output_limits  # 输出限制
        self.sample_time = sample_time      # 采样时间
        self.anti_windup = anti_windup      # 是否启用防积分饱和
        
        # 初始化状态
        self.reset()
        
        logger.info(
            f"PID控制器初始化: kp={kp}, ki={ki}, kd={kd}, "
            f"output_limits={output_limits}, sample_time={sample_time}"
        )
        
    def reset(self):
        """重置控制器状态"""
        self.setpoint = 0.0        # 设定值
        self.last_error = 0.0      # 上次误差
        self.integral = 0.0        # 积分项
        self.last_time = None      # 上次更新时间
        
    def clamp(self, value: float) -> float:
        """限制输出值在指定范围内"""
        if self.output_limits is None:
            return value
            
        lower, upper = self.output_limits
        return max(lower, min(value, upper))
        
    def compute(self, setpoint: float, measurement: float, dt: Optional[float] = None) -> float:
        """
        计算PID控制输出
        
        参数:
            setpoint: 目标值
            measurement: 当前测量值
            dt: 时间间隔(秒)
            
        返回:
            output: 控制输出值
        """
        try:
            if dt is None:
                dt = self.sample_time
                
            # 计算误差
            error = setpoint - measurement
            
            # 计算比例项
            P = self.kp * error
            
            # 计算积分项（使用梯形积分）
            if self.ki > 0:
                potential_integral = self.integral + 0.5 * self.ki * (error + self.last_error) * dt
                
                # 防积分饱和
                if self.anti_windup and self.output_limits is not None:
                    lower, upper = self.output_limits
                    self.integral = max(lower, min(potential_integral, upper))
                else:
                    self.integral = potential_integral
            
            I = self.integral
            
            # 计算微分项（使用后向差分）
            if self.kd > 0 and dt > 0:
                D = self.kd * (error - self.last_error) / dt
            else:
                D = 0
            
            # 计算总输出
            output = P + I + D
            
            # 限制输出范围
            output = self.clamp(output)
            
            # 更新状态
            self.last_error = error
            
            logger.debug(
                f"PID计算 - 设定值: {setpoint:.2f}, 测量值: {measurement:.2f}, "
                f"输出: {output:.2f}, P: {P:.2f}, I: {I:.2f}, D: {D:.2f}"
            )
            
            return output
            
        except Exception as e:
            logger.error(f"PID计算错误: {str(e)}")
            return self.clamp(0.0)  # 发生错误时返回安全值

class TrainSpeedController:
    """列车速度控制器"""
    def __init__(self):
        # 创建速度PID控制器
        self.speed_pid = PIDController(
            kp=0.8,    # 比例增益
            ki=0.2,    # 积分增益
            kd=0.3,    # 微分增益
            output_limits=(-1.1, 1.1),  # 加速度限制
            sample_time=0.1,            # 采样时间
            anti_windup=True            # 启用防积分饱和
        )
        
        # 状态变量
        self.last_acc = 0.0      # 上次加速度
        self.max_jerk = 0.75     # 最大加加速度 (m/s³)
        
        logger.info("列车速度控制器已初始化")
        
    def reset(self):
        """重置控制器状态"""
        self.speed_pid.reset()
        self.last_acc = 0.0
        logger.debug("列车速度控制器已重置")
        
    def compute_control(self, target_speed: float, current_speed: float, dt: float) -> float:
        """
        计算列车控制输出
        
        参数:
            target_speed: 目标速度 (km/h)
            current_speed: 当前速度 (km/h)
            dt: 时间间隔 (s)
            
        返回:
            control_acc: 控制加速度 (m/s²)
        """
        try:
            # 将速度单位从km/h转换为m/s
            target_speed_ms = target_speed / 3.6
            current_speed_ms = current_speed / 3.6
            
            # 计算基础控制输出
            raw_acc = self.speed_pid.compute(target_speed_ms, current_speed_ms, dt)
            
            # 限制加加速度（平滑加速度变化）
            acc_change = raw_acc - self.last_acc
            max_change = self.max_jerk * dt
            
            if abs(acc_change) > max_change:
                acc_change = max_change * np.sign(acc_change)
                
            # 更新加速度
            self.last_acc = self.last_acc + acc_change
            
            # 记录控制信息
            logger.debug(
                f"速度控制 - 目标: {target_speed:.1f} km/h, "
                f"当前: {current_speed:.1f} km/h, "
                f"输出加速度: {self.last_acc:.3f} m/s²"
            )
            
            return self.last_acc
            
        except Exception as e:
            logger.error(f"速度控制计算错误: {str(e)}")
            return 0.0  # 发生错误时返回安全值
        
    def get_control_params(self) -> dict:
        """获取控制参数"""
        return {
            'kp': self.speed_pid.kp,
            'ki': self.speed_pid.ki,
            'kd': self.speed_pid.kd,
            'max_jerk': self.max_jerk
        }
        
    def set_control_params(
        self,
        kp: Optional[float] = None,
        ki: Optional[float] = None,
        kd: Optional[float] = None,
        max_jerk: Optional[float] = None
    ):
        """设置控制参数"""
        if kp is not None:
            self.speed_pid.kp = kp
        if ki is not None:
            self.speed_pid.ki = ki
        if kd is not None:
            self.speed_pid.kd = kd
        if max_jerk is not None:
            self.max_jerk = max_jerk
            
        logger.info(
            f"更新控制参数 - kp: {self.speed_pid.kp}, "
            f"ki: {self.speed_pid.ki}, kd: {self.speed_pid.kd}, "
            f"max_jerk: {self.max_jerk}"
        )