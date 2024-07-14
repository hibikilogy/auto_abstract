#TODO: 

import os, re, json
from utils import AbstractConfig, MinInterval
from openai import OpenAI
import tiktoken

class AbstractGenerator():
    def __init__(self, cfg):
        self.cfg = cfg
        self.client = OpenAI(
            api_key = cfg.moonshot_key,
            base_url = cfg.api_url,
        )
        self.encoder = tiktoken.get_encoding(cfg.encoding)
    
    def write_startcode(self, code):
        with open(self.cfg.config_file, 'rw', encoding='utf-8') as f:
            data = json.load(f)
            data['start'] = code
            json.dump(data, f, ensure_ascii=False, indent=4)
        
    @MinInterval(lambda self: self.cfg.interval)
    def query_ai(self, artical):
        token_size = len(self.encoder.encode(artical))
        print(f"AI 摘要请求中 ({token_size})...")
        abstract = None
        for model,size in self.cfg.models.items():
            if token_size < size:  #超长使用更大的模型
                completion = self.client.chat.completions.create(
                    model = model,
                    messages = [
                        {"role": "system", "content": self.cfg.prompt},
                        {"role": "user", "content": artical}
                    ],
                    temperature = self.cfg.temperature,
                )
                abstract = completion.choices[0].message.content
                # print(abstract)
                break
            else:
                print(f"{token_size}>{size}, using larger model")
        if not abstract:
            raise ValueError("abstract query failed")
        return abstract
    
    def gen_abstract_content(self, artical, origin_tag = None):
        abstract_content = None
        wrap = self.cfg.frontter.wrapper
        # origin_tag = re.compile(rf'\n{sep}.*{self.cfg.frontter.commenter} origin\s*?\n.*{sep}\n', re.DOTALL)
        origin_pattern = re.compile(r'[\s\W](摘要|前言|引言)[\s\W]\s*?(.*?)\n\s*?[#|==]', re.DOTALL)
        origin_abstract = origin_pattern.search(artical)
        if origin_abstract and not self.cfg.force:
            # 提取匹配到的内容
            abstract_content = origin_abstract.group(2).strip()
            abstract_content = re.sub(r'^!.*?$', '', abstract_content, flags=re.MULTILINE)
            abstract_content = re.sub(r'\s', ' ', abstract_content)
            abstract_content = re.sub(r'[<|/].*?>', '', abstract_content)
            abstract_content = re.sub(r'&emsp;', '', abstract_content)
            # if len(abstract_content)>self.cfg.maxlength:
            #     print(f"找到原文摘要过长({len(abstract_content)}>{self.cfg.maxlength}), 截取片段")
            #     abstract_content = abstract_content[:self.cfg.maxlength]
            # else:
            print("找到原文摘要")
            tag = "origin"
        elif origin_tag not in[None, 'AI','origin'] and not self.cfg.force:
            tag = "manual"
            return tag, None
        else:
            tag = "AI"
            abstract_content = self.query_ai(artical)
        if not abstract_content:
            raise ValueError("abstract not generated")
            
        replace_content = \
            f" {tag} \nabstract {self.cfg.frontter.definer} {wrap}{abstract_content}{wrap}"
        return tag, replace_content

    
    def handle_file(self, filepath):
        r"""        
        原文已生成（有字段）
            强制覆盖模式, 覆盖ALL, 标记AI
            -a, 跳过
            覆盖模式(default), 覆盖AI,更新origin,跳过manual
        原文未生成
            强制覆盖模式, 直接生成, 标记AI
            已有摘要, 复制, 标记origin
            需要生成, -a/default, 标记AI
        """
        print(f"\nhandling {filepath}")
        artical = open(filepath,'r',encoding='utf-8').read()
        if len(artical)==0:
            raise ValueError("read file failed")
        new_artical = None
        sep = self.cfg.frontter.separator.replace('+','\+')
        defi = self.cfg.frontter.definer
        comm = self.cfg.frontter.commenter
        
        # 
        field_parttern = re.compile(
            rf'({sep}.*?\n#)(.*?)\nabstract.*?{defi}.*?(\n.*?{sep})', 
            re.DOTALL)
        abstract_field = field_parttern.search(artical)
        # 查找abstract字段并进行替换
        if abstract_field:
            if self.cfg.force or not self.cfg.add:
                _tag = abstract_field.group(2).strip()
                tag, replace_content = self.gen_abstract_content(artical, _tag)
                if tag =="manual":
                     print("已有手动添加的abstract, 跳过")
                else:
                    new_artical = field_parttern.sub(rf'\1{replace_content}\3', artical)
                    print(f"已有'abstract'并{'强制覆盖' if self.cfg.force else '处理'}为'{tag}'.")
            elif self.cfg.add:
                print("已有 'abstract' 并跳过.")
            else:
                raise ValueError("config error")
        else:
            tag, replace_content = self.gen_abstract_content(artical)
            new_artical = re.sub(rf'{sep}\n(.*?)\n{sep}', 
                            rf'{sep}\n\1\n{comm}{replace_content}\n{sep}', artical, flags=re.DOTALL)
            print(f"已添加 '{tag} abstract' ")
        if new_artical:
            new_artical = new_artical.replace('\+','+')
            with open(filepath,'w',encoding='utf-8') as file:
                file.write(new_artical)

    
    def generate(self,path = None):
        if path:
            if os.path.isfile(path):
                return self.handle_file(path)
            elif os.path.isfile(os.path.join(self.cfg.post_path, path)):
                return self.handle_file(os.path.join(self.cfg.post_path, path))
            elif os.path.isdir(path):
                post_path = path
        # 不输入path则处理配置中默认path
        elif os.path.isfile(self.cfg.post_path):
            return self.handle_file(self.cfg.post_path)
        elif os.path.isdir(self.cfg.post_path):
            post_path = self.cfg.post_path
        else:
            raise ValueError("path not exist")
        for i, (root, dirs, filenames) in enumerate(os.walk(post_path)):
            if self.cfg.debug:
                filenames = filenames[:10]
            for j, filename in enumerate(filenames):
                unicode = (i << 32) | j
                if unicode < self.cfg.start: continue
                elif unicode == self.cfg.start:
                    print(f"Starting at {unicode}")
                # 指定的扩展名结尾
                if filename.endswith(tuple(self.cfg.ext)):
                    filepath = os.path.join(root, filename)
                    try:
                        self.handle_file(filepath) 
                    except:
                        self.write_startcode(unicode)
            
        print("All file handled")
        self.write_startcode(0)

            
if __name__=="__main__":
    cfg = AbstractConfig('config.json')
    generator = AbstractGenerator(cfg)
    generator.generate()