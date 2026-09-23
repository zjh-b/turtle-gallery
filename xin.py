import turtle
t=turtle.Turtle()
def c():
    t.fillcolor("red")
    t.begin_fill()
    t.penup()
    t.goto(0,100)
    t.pendown()
    t.setheading(45)
    t.circle(-80,180)
    t.fd(160)
    t.setheading(135)
    t.fd(160)
    t.setheading(-45)
    t.circle(80,-180)
    t.end_fill()



c()
turtle.done()
