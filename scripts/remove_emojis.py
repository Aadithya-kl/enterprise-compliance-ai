import os
import emoji

def check_file(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
            # check if any emoji exists in the content
            if any(char in emoji.EMOJI_DATA for char in content):
                return True
    except Exception as e:
        pass
    return False

def replace_emojis(filepath):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # replace emojis with empty string
        new_content = ''.join('' if char in emoji.EMOJI_DATA else char for char in content)
        
        if new_content != content:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f'Removed emojis from {filepath}')
    except Exception as e:
        print(f'Error processing {filepath}: {e}')

found = []
for root, dirs, files in os.walk('frontend/src'):
    for file in files:
        if file.endswith(('.tsx', '.ts', '.js', '.jsx', '.css', '.html')):
            path = os.path.join(root, file)
            if check_file(path):
                found.append(path)

for f in found:
    print('EMOJI FOUND:', f)
    replace_emojis(f)
