from turtle import *
import time
import random

screen=Screen()
screen.bgcolor("black")
setup(600,400)
H=400
W=600
balls=[]
class Ball:
    def __init__(self,x,y,dx,dy,r):
        self.x=x
        self.y=y
        self.dx=dx
        self.dy=dy
        self.r=r
    def drawCircle(self):
        color(random.choice(["blue","black","pink","red","purple","orange"]))
        pu()
        goto(self.x,self.y)
        pd()
        dot(self.r)


    def update(self):
        if self.x>=W/2-self.r or self.x<=-W/2+self.r:
            self.dx=-self.dx
        if self.y>=H/2-self.r or self.y<=-H/2+self.r:
            self.dy=-self.dy
        self.x+=self.dx
        self.y+=self.dy



for i in range(20):
    r=random.randint(10,30)
    x=random.randint(-W//2+r,W//2-r)
    y=random.randint(-H//2+r,H//2-r)
    dx=random.randint(2,6)
    dy=random.randint(1,4)
    ball=Ball(x,y,dx,dy,r)
    balls.append(ball)

speed(0)
hideturtle()
while True:
    tracer(0)
    clear()
    for ball in balls:
        ball.drawCircle()
        ball.update()
    tracer(1)
    time.sleep(0.01)



done()
