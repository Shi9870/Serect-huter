import os 
import re


def load_Key_Word(filename):

    keyword_List =[]

    if not os.path.exists(filename):
        print(f"Can not find setting content{filename}")
        return None
    try:
        with open(filename,'r',encoding='utf-8') as f:
            for line in f:
                clean_word = line.strip()

                if clean_word:
                    keyword_List.append(clean_word)
        print(f"Loaded {len(keyword_List)} rules: {keyword_List}")

        return "|".join(keyword_List)
    except Exception as e:
        print(f"Failed to read the setting:{e}")
        return None

current_dir = os.path.dirname(os.path.abspath(__file__))
config_path = os.path.join(current_dir,"keyword.txt")
regex_pattern_string = load_Key_Word(config_path)


if regex_pattern_string:
    Keywords_pattern = re.compile(regex_pattern_string,re.IGNORECASE)
else:
    Keywords_pattern = None
    print("Warrning there is no rules")

def scan_directory(path):
    if not Keywords_pattern:
        return
    
    abs_path = os.path.abspath(path)
    print("============== Scan Start ==============")
    for root,dirs,files in os.walk(path):
        if '.git' in dirs: dirs.remove('.git')

        for file_name in files:

            if file_name == 'keyword.txt':
                continue
            if file_name.endswith('.py'):
                continue
            full_path = os.path.join(root,file_name)
            check_file_leaking(full_path)


def check_file_leaking(file_path):
    try:
        with open(file_path,'r',encoding='utf-8',errors='ignore') as f:
            for line_num , line in enumerate(f,1):

                if Keywords_pattern.search(line):

                    print(f"leaking file: {file_path}")
                    print(f"Leaking Line: {line_num}")
                    print(f"Leaking content: {line.strip()}")

                    continue
    except Exception as e:
        print(f"Failed to read file {file_path}:{e}")

Checkfile_path = os.path.join(current_dir,"checkingFile")
if __name__ =="__main__":

    if os.path.exists(Checkfile_path):

        scan_directory(Checkfile_path)
        if len(os.listdir(Checkfile_path)) == 0:
            print("The folder is empty please add the files you want to scan.")

    else:
        print(f"no such folder checkingFile in {Checkfile_path}")
        print(f"Make sure you have checkingFile  folder in {current_dir}")
