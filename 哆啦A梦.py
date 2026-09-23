from turtle import *
pensize(4)
speed(9)
#脸
penup()
goto(0,-200)
pendown()
fillcolor("blue")
begin_fill()
circle(200)
end_fill()
fillcolor("white")
begin_fill()
circle(160)
end_fill()
penup()
goto(0,125)
pendown()
begin_fill()
seth(90)
circle(40)
circle(-40)
end_fill()
#眼球
penup()
goto(-40,105)
pendown()
dot(40)
dot(10,"white")
#右眼
penup()
goto(40,105)
pendown()
dot(40)
dot(10,"white")
#鼻子
penup()
goto(0,80)
pendown()
dot(30,"red")
fd(-100)

penup()
seth(-90)
goto(-85,-45)
pendown()
circle(85,180)


t=10
a=30
for i in range(3):
    penup()
    goto(40,t)
    pendown()
    seth(a)
    fd(200)
    t-=5
    a-=30

a=150
t=10
for i in range(3):
    penup()
    goto(-40,t)
    pendown()
    seth(a)
    fd(200)
    t-=5
    a+=30



done()
