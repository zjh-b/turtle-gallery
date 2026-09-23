import turtle
turtle.shape("turtle")
turtle.bgcolor("black")
colors = ["red", "yellow", "blue", "green","orange","purple","pink","gray"]
turtle.speed(0)
for i in range(230):
    turtle.pencolor(colors[i%8])
    turtle.penup()
    turtle.forward(i)
    turtle.right(44)
    turtle.pendown()
    for j in range(4):
        turtle.forward(5+i/8)
        turtle.right(90)
turtle.hideturtle()
turtle.done()
