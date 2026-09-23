import turtle
t=turtle.Turtle()
def b():
    t.penup()
    t.goto(-200,0)
    t.setheading(90)
    t.pendown()
    t.circle(-210,180)
    t.circle(-70,-180)
    t.circle(70,180)
    t.circle(-70,-180)
    t.penup()
    t.goto(0,70)
    t.pendown()
    t.setheading(-90)
    t.fd(300)
    t.circle(-50,180)




b()
turtle.done()
