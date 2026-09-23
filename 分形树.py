from turtle import *
import random
def a(d):
    if d>=5:
        pensize(d/20)
        forward(d)
        angleR=random.randint(10,40)
        right(angleR)
        a(d-random.randint(10,20))
        angleL=random.randint(10,40)
        left(angleR+angleL)
        a(d-random.randint(10,20))
        right(angleL)
        backward(d)
    else:
        color("pink")
        dot(5)
        color("black")

tracer(False)
speed(0)
penup()
goto(0,-200)
setheading(90)
pendown()
a(125)
hideturtle()
done()
