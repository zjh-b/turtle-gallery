from turtle import *
import time

#绘制背景
def drawBackground():
    penup()
    goto(0,0)
    seth(0)
    pendown()
    color("red")
    dot(100)
    penup()
    goto(-300,0)
    color("purple")
    pensize(2)
    pendown()
    goto(-180,0)
    color("black")
    n=str(len(needles))
    penup()
    goto(-240,10)
    write(n,align="center",font=("行楷",18))
    if gameOver:
        penup()
        goto(-240,-40)
        color("black")
        write("游戏结束",align="center",font=("行楷",18))
class Needle:
    angle=180
    def draw(self):
        color("purple")
        pensize(2)
        penup()
        goto(0,0)
        seth(self.angle)
        forward(50)
        pendown()
        fd(100)
    def update(self):
        self.angle=(self.angle+1)%360
def addNeedle(x,y):
    global gameOver
    if gameOver:
        return
    newNeedle=Needle()
    for needle in needles:
        if abs(needle.angle-newNeedle.angle)<4:
            gameOver=True
            newNeedle.draw()
    needles.append(newNeedle)

hideturtle()
setup(width=600,height=400)
needles=[]
onscreenclick(addNeedle)
gameOver=False
while not gameOver:
    tracer(False)
    clear()
    for needle in needles:
        needle.update()
        needle.draw()
    drawBackground()
    tracer(True)
    time.sleep(0.01)

done()
