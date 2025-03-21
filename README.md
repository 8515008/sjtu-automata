# sjtu-automata
![Version](https://img.shields.io/badge/Version-0.4.0-blue.svg) ![Language](https://img.shields.io/badge/Language-Python3-red.svg) ![License](https://img.shields.io/badge/License-GPL--3.0-yellow.svg)
## 寻求维护者：由于本人即将离开毕业，本仓库相关维护工作将无法进行，现寻求新一届维护者，如有兴趣欢迎联系！

**注意！此版本为BETA版，未经过严格测试，可能存在BUG，如有问题请提交[issue](https://github.com/MXWXZ/AutoElect/issues)**

**v0.4.0更新：教务系统限制大约在30-60分钟左右可能需要重新登陆。**

上海交通大学抢课脚本\
V2协议分析：<https://github.com/MXWXZ/sjtu-automata/blob/master/Protocol%20analysis%20v2.md>

## 使用脚本你可以做到
:heavy_check_mark: 无人值守自动抢课\
:heavy_check_mark: 并发抢课提升成功率\
:heavy_check_mark: 卡时间准时抢课

## 使用脚本你不能做到
~~:x: 违反选课规则选课(0day fucked)~~\
:x: 提高您的网速\
:x: 保证一定可以抢到课

## 系统环境测试程度
最佳支持：Manjaro with python 3.7.3 / Ubuntu 18.04 LTS with Python 3.6.7 / macOS with Python 3.8.2

Linux > macOS > Windows

## 安装
    
    pip3 install sjtu-automata

## 升级

    pip3 install sjtu-automata --upgrade

### [可选]验证码自动识别
Windows可以不装，Linux如无图形界面且无法通过其他方式打开`captcha.jpeg`文件需要安装。

Arch系安装下面两个包：`tesseract`、`tesseract-data-eng`

Ubuntu 18.04：

    sudo apt install tesseract-ocr libtesseract-dev
    
macOS

    brew install tesseract

其他版本/发行版/Windows等自行看文档：https://github.com/tesseract-ocr/tesseract/wiki
    
## 简单使用说明
- 由于选课系统再次更新，需要传递的参数改变，因此建议使用油猴脚本获取ID：https://www.tampermonkey.net/
- 插件安装完成后点击这里进入脚本安装页面：https://github.com/MXWXZ/sjtu-automata/raw/master/sjtu-automata.user.js
- 下面的教程以安装插件之后为准，如果不安装油猴脚本也可以自行查看网页源码提取相关ID

1. 查看课程号和教学班：想选的课“教学班”第二行点击复制ID即可复制课号+教学班号
2. 查看课程类型：标签页第二行的字符串即为课程类型
3. 使用命令选课，格式为`autoelect [课程类型ID] [课程号ID] [256位教学班ID]`：

        autoelect 01 AAAA... aaaa... 10 BBBB bbbb...

    上述命令将会选`01`课程类型下的`AAAA`课的`aaaa`（省略256位）教学班和`10`课程类型下的`BBBB`课的`bbbb`（省略256位）课，如果需要更多可以在后面继续添加。

    注：程序运行过程中输入`s`可以查看选课状态

## 抢课说明
- **本程序所有操作均保证当前课程不会减少，即无论你是否已经选上课、无论是否人满等各种情况都不会影响已选课程。换言之，无论何时均保证课程只多不少，重复提交不会影响当前课表。**
- 程序运行后选课将会自动进行，如果失败自动重试，如果课程已满将自动等待并且定时刷新，直到抢成功或者用户退出为止
- 可以提前开上程序，如果没有开放选课将会自动等待并定时刷新，可以节省登陆的时间
- 所有指定的课程会同时进行选课，每个课程可占一个或多个线程进行选课增加成功率（多线程一般在网卡的时候才有必要）

## 参数说明
### CLI
使用：`autoelect [OPTIONS] [CLASSTYPE-CLASSID-JXBID]`

| 参数  |   长参数形式   |              说明              |
| :---: | :------------: | :----------------------------: |
|  -v   |   --version    |            显示版本            |
|       |  --no-update   |          关闭更新检查          |
|  -o   |     --ocr      |       使用OCR识别验证码        |
|       | --print-cookie |         打印登陆cookie         |
|  -d   |    --delay     |   两次尝试选课间隔（默认1s）   |
|  -c   | --check-delay  | 检查选课是否开放的延迟(默认3s) |
|  -n   |    --number    |  每个课程的线程数（默认为1）   |
|  -h   |     --help     |            显示帮助            |

- `CLASSTYPE`、`CLASSID`、`JXBID`成组出现，可以出现多组同步进行，但至少有一组
- `CLASSTYPE`：2位课程类型
- `CLASSID`：课号ID
- `JXBID`：256位教学班ID

## Launch.json参数说明
### CLI
{
    // Use IntelliSense to learn about possible attributes.
    // Hover to view descriptions of existing attributes.
    // For more information, visit: https://go.microsoft.com/fwlink/?linkid=830387
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python Debugger: Current File",
            "type": "debugpy",
            "request": "launch",
            "program": "${file}",
            "console": "integratedTerminal",
            "args":[
                "--no-update",
                "--print-cookie",
                "01","MARX1202",
                "xxxx"
            ],
            "justMyCode": false
        }
    ]
}