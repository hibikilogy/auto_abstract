# auto abstract
本项目为文章自动摘要脚本，核心逻辑如下：
```
查找abstract字段：
已有abstract字段
    判断执行模式：
    强制覆盖模式-f, 覆盖所有, 标记AI
    添加模式-a, 跳过
    覆盖模式(default), 覆盖AI,更新origin,跳过manual
未找到abstract字段
    判断执行模式：
    强制覆盖模式, 直接生成, 标记AI
    原文有摘要/前言/引言, 过长截断, 复制到abstract, 标记origin
    需要生成, -a/default, 标记AI
```

## 使用方式
安装 Python 并下载本仓库，pip install -r requirements.txt安装依赖

需要自行在项目目录创建`moonshot_config.py`并在其中添加
```python 
moonshot_key = your moonshot api key
```
api key获得方式：https://platform.moonshot.cn/console/api-keys


两种使用方式：
1. 可通过命令行+参数传入
    ```bash
    python auto_abstract.py -h
    ```
2. 或修改`utils.py`中的配置并直接运行`auto_abstract.py`

详情参考参数说明，使用时确认好format为jekyll或zola，建议先以debug运行测试可行性

## 注意事项

参数查找顺序为命令行参数传入>utils配置>命令行参数默认值

如需正常使用脚本功能，请确保目录满足以下条件：
```
.
├─hibikilogy.github.io
│  └─_post
└─auto_abstract（当前目录）
```
脚本会将`#`标记但非`# AI/# origin`标记的abstract认为是手动添加的，并在非强制覆盖时跳过处理，也即手动添加abstract应当为以下格式：
```markdown
# manual/干脆空着，但是需要有#且不能为AI 或 origin
abstract: 123
```
moonshot api key免费额度有请求频率限制，可通过`interval`参数控制请求间隔