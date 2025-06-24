import os
 
print("当前文件路径 (__file__):", __file__)
print("绝对路径:", os.path.abspath(__file__))
print("所在目录:", os.path.dirname(os.path.abspath(__file__)))
print("当前工作目录:", os.getcwd()) 