print("欢迎来到月饼计算程序")
while True:
    print("输入q退出程序,按下回车继续")
    i=input()
    if i=='q':
        break
    elif i=='':
        a=int(input("输入月饼:",))
        b=int(input("输入每盒装的月饼数:",))
        if b==0:
            print("分母不能为0")
            continue
        else:
            c=a//b
            d=a%b
        print(f"月饼可以装满{c}个包装盒,还有{d}个")
    else:
        print("请按格式输入")
