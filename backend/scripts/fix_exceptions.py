import os

for root, dirs, files in os.walk('app'):
    for f in files:
        if f.endswith('.py'):
            path = os.path.join(root, f)
            with open(path, 'r', encoding='utf-8') as file:
                lines = file.readlines()
            changed = False
            for i, line in enumerate(lines):
                # Using lstrip to avoid replacing something like `except: pass` exactly, just `except:` on its own line
                if line.lstrip().startswith('except:\n') or line.lstrip().startswith('except:\r\n'):
                    indent = len(line) - len(line.lstrip())
                    lines[i] = line.replace('except:', 'except Exception as e:')
                    lines.insert(i+1, ' '*(indent+4) + 'logger.error(f"Exception caught: {e}", exc_info=True)\n')
                    changed = True
            
            if changed:
                has_logger = any('import get_logger' in l or 'import logging' in l for l in lines)
                if not has_logger:
                    lines.insert(0, 'import logging\nlogger = logging.getLogger(__name__)\n')
                
                with open(path, 'w', encoding='utf-8') as file:
                    file.writelines(lines)
            
print("Bare exceptions fixed!")
