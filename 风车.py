import turtle as t
def fengche(r):
    for i in range(4):
        t.seth(i*90+r)
        t.color("cyan")
        t.begin_fill()
        t.fd(100)
        t.lt(150)
        t.fd(70)
        t.end_fill()
        t.color("blue")
        t.begin_fill()
        t.lt(30)
        t.fd(40)
        t.lt(90)
        t.fd(35)
        t.end_fill()

t.speed(0)
fengche(0)
for i in range(1000000):
    t.tracer(0)
    t.clear()
    fengche(i)
    t.hideturtle()
    t.update()
t.done()
