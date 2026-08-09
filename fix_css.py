import os
filepath = os.path.join('jainzee-website', 'static', 'css', 'style.css')
with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()
new_lines = [line for line in lines if '>>>>>>>' not in line]
with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)
with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()
print('Contains >>>>>>>:', '>>>>>>>' in content)
print('Total lines:', len(new_lines))
