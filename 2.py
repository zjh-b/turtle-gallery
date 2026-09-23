import turtle
t=turtle.Turtle()
colors=["red","orange","yellow","green","blue","indigo","violet"]
def a(x,y,r):
    t.penup()
    t.seth(0)
    t.goto(x,y-r)
    t.pendown()
    t.circle(r)

def b(x,y,m):
    t.pencolor("red")
    a(x,y,m)
    if m>=10:
        b(x+1.5*m,y,m/2)
        b(x-1.5*m,y,m/2)
        b(x,y+1.5*m,m/2)
        b(x,y-1.5*m,m/2)
t.speed(0)
b(0,0,100)
t.ht()
turtle.done()
