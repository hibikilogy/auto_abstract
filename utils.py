# 参数&配置文件&utils
import argparse, time, types, json
from moonshot_config import moonshot_key
from functools import wraps
from collections import namedtuple, OrderedDict

Format = namedtuple('Format', ['separator', 'definer', 'commenter', 'wrapper'])

symbols = OrderedDict({
    "jekyll": {
        "separator": "---",
        "definer": ":",
        "commenter": "#",
        "wrapper": "",
    },
    "zola": {
        "separator": "+++",
        "definer": "=",
        "commenter": "#",
        "wrapper": "\"",
    }
})



class AbstractConfig():
    def __init__(self, config_file):
        with open(config_file, 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        parser = argparse.ArgumentParser()
        parser.add_argument("--format","-m", type=str, default=next(iter(symbols)), choices=list(symbols.keys()), 
                            help=f"Whitch format to use, support {list(symbols.keys())}, default {next(iter(symbols))}") #添加/覆盖
        parser.add_argument("--add","-a", action="store_true", default=False, help="Addition mode, articals w/o 'abstract' field will be added, default in OverWrite mode") #添加/覆盖
        parser.add_argument("--force","-f", action="store_true", default=False, help="Forced Write ALL abstract using AI, default manual-added ones will Not be overwritten")
        parser.add_argument("--post_dir", type=str, default="../hibikilogy.github.io/_posts", help="Path for posts DIR/FILE to abstract")
        parser.add_argument("--interval", type=int, default=20, help="Min interval for API request")
        parser.add_argument("--ext", nargs='+', type=str, default=[".md"], help="List of file extensions")
        parser.add_argument("--maxlength", "-l", type=int, default=300, help="Length limit for abstract")
        parser.add_argument("--debug", action="store_true", default=False, help="Debug in first 5 post")
        
        args = parser.parse_args()
        def get_arg(key,default = None):
            return getattr(args, key) if hasattr(args, key) and getattr(args, key) != parser.get_default(key) else config.get(key, default)
        
        self.force = get_arg('force',False)
        if self.force:
            response = input("警告：执行此操作可能会覆盖所有摘要，导致不可逆的改变。是否确定执行？(y/n): ").lower()
            if response != 'y':
                raise ValueError("操作已取消，程序退出")
        
        self.format = get_arg('format',"jekyll")
        self.post_dir = get_arg('post_dir')
        self.ext = get_arg('ext')
        self.add = get_arg('add')
        self.maxlength = get_arg('maxlength')
        self.debug = get_arg('debug',False)
        
        # # kimi api
        self.moonshot_key = moonshot_key
        self.models = get_arg('models')   #模型: token长度
        self.encoding = get_arg('encoding')
        self.api_url = get_arg('api_url')
        self.temperature = get_arg('temperature',0.3)
        self.interval = get_arg('interval',20)  #api最短请求间隔s
        
        self.models = dict(sorted(self.models.items(), key=lambda item: item[1]))
        
        self.formatter = Format(
            separator=symbols[self.format]["separator"], 
            definer=symbols[self.format]["definer"],
            commenter=symbols[self.format]["commenter"],
            wrapper=symbols[self.format]["wrapper"],
            )
        
        self.prompt = f'''你需要将我给你的markdown文档内容做简要的学术摘要，若原文有"前言"、"总结"可着重参考相应内容。
                        请忽略文档中的html代码，只返回摘要内容，摘要只有一个自然段，长度限制在{self.maxlength}字以内。
                        注意！不要以以下形式开头:《文章标题》, "这篇文章..."; 摘要中禁止出现以下文字: "恶搞" 
                        '''
        

class MinInterval:
    '''
    控制方法调用间隔的包装类
    '''
    def __init__(self, interval):
        if isinstance(interval, (int, float)):
            self.interval_func = lambda: interval
        elif isinstance(interval, types.FunctionType):
            self.interval_func = interval
        else:
            raise ValueError("Invalid interval type. Must be int, float, or function.")
        self.last_executed = 0

    def __call__(self, func):
        @wraps(func)
        def wrapper(that, *args, **kwargs):
            interval = self.interval_func(that)
            current_time = time.time()
            time_since_last = current_time - self.last_executed
            if time_since_last < interval:
                remaining_time = interval - time_since_last
                print(f"Function '{func.__name__}' is called too soon, waiting {remaining_time:.2f}s...")
                time.sleep(remaining_time)
            # self.last_executed = time.time()
            res = func(that, *args, **kwargs)
            self.last_executed = time.time()
            return res

        return wrapper