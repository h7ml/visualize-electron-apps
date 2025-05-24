"""
Vercel Serverless处理文件

这个文件导入Flask应用，并提供Vercel Serverless Functions所需的处理入口点。
"""

from index import app

# 暴露Flask应用为处理入口点
app = app 
