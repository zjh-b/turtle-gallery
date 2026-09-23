import turtle as t
import time
def tai(r,angle):
    t.home()
    t.seth(angle)
    t.up()
    t.fd(r)
    t.down()
    t.right(90)
    #画阳鱼
    t.color("black")
    t.begin_fill()
    t.circle(-r/2,180)
    t.circle(r/2,180)
    t.circle(r,180)
    t.end_fill()
    t.circle(r,180)
    #画阴鱼眼
    t.up()
    t.seth(angle)
    t.fd(r/2)
    t.down()
    t.dot(r/4,"white")
    #画阳鱼眼
    t.up()
    t.fd(r)
    t.down()
    t.dot(r/4,"black")
    t.up()
t.speed(3)
tai(200,90)
for i in range(1000):
    t.tracer(0)
    t.clear()
    tai(200,i)
    time.sleep(0.01)
    t.update()
t.done()
