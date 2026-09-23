from turtle import *  # 导入turtle库
from datetime import datetime # 导入日期时间库
import time  # 导入时间库

def drawCircle(): # 绘制表盘
    # 绘制表盘空心圆
    color('black') # 黑色
    pensize(1) # 粗细1
    penup() # 抬笔
    goto(0, -170) # 移到圆心下方
    setheading(0) # 面朝由
    pendown() # 落笔
    circle(170) # 在左侧画空心圆
    # 绘制表盘上的12个刻度
    penup() # 抬笔
    goto(0, 0) # 移到圆心
    pensize(3) # 粗细3
    for i in range(12): # 循环12次
        setheading(i*30) # 对应朝向角度
        penup() # 抬笔
        forward(160) # 不绘制前进
        pendown() # 落笔
        forward(10) # 绘制前进
        penup() # 抬笔
        backward(170) # 回到圆心
        # 绘制表盘上的文字
    penup() # 抬笔
    goto(0, -100) # 移到表盘下部
    write('我的时钟',align="center", font=("宋体", 18))

# 定义函数绘制线段(颜色、粗细、角度、长度)
def drawTimeLine(col, size, angle, length):
    color(col) # 设置颜色
    pensize(size) # 设置粗细
    penup() # 抬笔
    goto(0, 0) # 移动到窗口中心
    setheading(90-angle) # 设置朝向角度
    pendown() # 落笔
    forward(length) # 前进绘制线段

def drawSecondLine(s): # 绘制秒针函数
    drawTimeLine('blue',2,6*s,150)

def drawMinuteLine(m): # 绘制分针函数
    drawTimeLine('green', 4, 6*m, 120)

def drawHourLine(h): # 绘制时针函数
    drawTimeLine('red', 6, 30*h, 100)
hideturtle()  # 隐藏海龟形状
while True:  # 循环重复执行
    tracer(False)  # 隐藏绘图中间过程
    clear()  # 清屏
    t = datetime.today() # 获得今天时间
    second = t.second # 当前秒
    minute = t.minute # 当前分
    hour = t.hour # 当前时
    drawCircle() # 绘制表盘
    drawSecondLine(second) # 绘制秒针
    drawMinuteLine(minute+second/60) # 绘制分针
    drawHourLine(hour+minute/60) # 绘制时钟
    tracer(True)  # 显示绘图中间过程
    time.sleep(0.1)  # 暂停0.1秒
done()
