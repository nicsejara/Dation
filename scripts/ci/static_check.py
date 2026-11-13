#!/usr/bin/env python3
"""Small static checks for changed files; excludes business execution and network."""
import argparse
import json
from pathlib import Path
import subprocess
ROOT=Path(__file__).resolve().parents[2]
def check_css(path):
    s=path.read_text()
    depth=0;state='normal';i=0
    while i<len(s):
        c=s[i];n=s[i+1] if i+1<len(s) else ''
        if state=='comment':
            if c=='*' and n=='/':state='normal';i+=1
        elif state in ('single','double'):
            if c=='\\':i+=1
            elif (c=="'" and state=='single') or (c=='"' and state=='double'):state='normal'
        elif c=='/' and n=='*':state='comment';i+=1
        elif c=="'":state='single'
        elif c=='"':state='double'
        elif c=='{':depth+=1
        elif c=='}':
            depth-=1
            if depth<0:raise ValueError('Unmatched CSS closing brace')
        i+=1
    if depth or state!='normal':raise ValueError('Unclosed CSS rule, comment or string')
def check(paths):
    for relative in paths:
        path=ROOT/relative
        if not path.is_file():
            continue
        if relative.endswith(('.mjs','.js')):
            subprocess.run(['node','--input-type=module','--check'],input=path.read_bytes(),check=True,cwd=ROOT)
        elif relative.endswith('.py'):
            compile(path.read_bytes(),str(path),'exec')
        elif relative.endswith('.json'):
            json.loads(path.read_text())
        elif relative.endswith('.css'):
            check_css(path)
        print('STATIC_OK',relative)
if __name__=='__main__':
    parser=argparse.ArgumentParser()
    parser.add_argument('--base',required=True);parser.add_argument('--head',required=True)
    args=parser.parse_args()
    from impact import diff_paths
    check(diff_paths(args.base,args.head))
