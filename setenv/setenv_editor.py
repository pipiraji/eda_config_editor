import re
import sys
import argparse
import os

class SetenvEditor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.lines = [] # List of dicts: {'raw': str, 'commented': bool, 'var': str, 'val': str, 'indent': str, 'val_sep': str, 'sep': str, 'trailing_comment': str}
        self.load()

    def load(self):
        if not os.path.exists(self.file_path):
            return

        with open(self.file_path, 'r', encoding='utf-8') as f:
            raw_lines = f.readlines()

        for line in raw_lines:
            stripped = line.strip()
            if not stripped:
                self.lines.append({
                    'raw': line, 'commented': False, 'var': None, 'val': None,
                    'indent': "", 'val_sep': "", 'sep': "", 'trailing_comment': ""
                })
                continue

            # 1. Parse line comments and split into setenv part and trailing comment part
            is_commented = stripped.startswith('#')
            trailing_comment = ""
            setenv_part = line

            if is_commented:
                # Find a '#' after all consecutive leading '#'s (to handle ###setenv and trailing comments)
                leading_hashes_match = re.match(r'^\s*(#+)', line)
                if leading_hashes_match:
                    hashes_len = len(leading_hashes_match.group(1))
                    start_search_idx = line.find(leading_hashes_match.group(1)) + hashes_len
                    second_comment_idx = line.find('#', start_search_idx)
                    if second_comment_idx != -1:
                        setenv_part = line[:second_comment_idx]
                        trailing_comment = line[second_comment_idx:]
            else:
                comment_idx = line.find('#')
                if comment_idx != -1:
                    setenv_part = line[:comment_idx]
                    trailing_comment = line[comment_idx:]

            # Calculate exact space separation before the trailing comment
            stripped_setenv = setenv_part.rstrip()
            sep = setenv_part[len(stripped_setenv):]

            # 2. Parse setenv in the setenv part
            # tcsh setenv format: [indent] [#] [whitespace] setenv VAR [VAL]
            # Match optional leading whitespace, optional comments, optional whitespace, setenv, variable, optional separator, and optional value
            match = re.search(r'^(\s*)(#+)?(\s*)setenv\s+([^\s]+)(?:(\s+)(.+))?$', stripped_setenv)
            
            if match:
                commented = match.group(2) is not None
                indent = match.group(1)
                var = match.group(4)
                val_sep = match.group(5) or ""
                val = match.group(6)
                if val:
                    val = val.strip()
                self.lines.append({
                    'raw': line,
                    'commented': commented,
                    'var': var,
                    'val': val,
                    'indent': indent,
                    'val_sep': val_sep,
                    'sep': sep,
                    'trailing_comment': trailing_comment
                })
            else:
                # Other lines (comments without setenv, etc.)
                self.lines.append({
                    'raw': line,
                    'commented': stripped.startswith('#'),
                    'var': None,
                    'val': None,
                    'indent': "",
                    'val_sep': "",
                    'sep': "",
                    'trailing_comment': ""
                })

    def _match(self, pattern, target):
        if pattern is None:
            return True
        if target is None:
            return False
        try:
            return re.fullmatch(pattern, target) is not None
        except re.error:
            return pattern == target

    def _quote_value_if_needed(self, val):
        if val is None:
            return None
        val_str = str(val)
        # If the value contains any whitespace and is not already quoted with single or double quotes
        if any(char.isspace() for char in val_str):
            if not ((val_str.startswith('"') and val_str.endswith('"')) or 
                    (val_str.startswith("'") and val_str.endswith("'"))):
                return f'"{val_str}"'
        return val_str

    def uncomment(self, cmd_pattern, val_pattern=None):
        changed = False
        for entry in self.lines:
            if not entry['commented'] or entry['var'] is None:
                continue
            
            if self._match(cmd_pattern, entry['var']):
                if val_pattern and not self._match(val_pattern, entry['val']):
                    continue
                
                entry['commented'] = False
                changed = True
        return changed

    def update(self, cmd_pattern, new_value):
        # 1. Uncomment matching variables first
        self.uncomment(cmd_pattern)
        
        formatted_value = self._quote_value_if_needed(new_value)
        
        changed = False
        for entry in self.lines:
            if entry['commented'] or entry['var'] is None:
                continue
            
            if self._match(cmd_pattern, entry['var']):
                entry['val'] = formatted_value
                changed = True
        return changed

    def set_variable(self, cmd, val):
        formatted_value = self._quote_value_if_needed(val)
        # 1. Try update first (use literal matching for set)
        if self.update(f"^{re.escape(cmd)}$", formatted_value):
            return True
        
        # 2. If not found, append to the end
        self.lines.append({
            'raw': "", # New line
            'commented': False,
            'var': cmd,
            'val': formatted_value,
            'indent': "",
            'val_sep': " ",
            'sep': " ",
            'trailing_comment': ""
        })
        return True

    def delete(self, cmd_pattern, val_pattern=None):
        changed = False
        for entry in self.lines:
            if entry['commented'] or entry['var'] is None:
                continue
            
            if self._match(cmd_pattern, entry['var']):
                if val_pattern and not self._match(val_pattern, entry['val']):
                    continue
                
                entry['commented'] = True
                changed = True
        return changed

    def save(self, output_path=None, dry_run=False):
        # Determine dominant indentation for setenv lines
        setenv_indents = [entry['indent'] for entry in self.lines if entry['var'] is not None]
        dominant_indent = ""
        if setenv_indents:
            dominant_indent = max(set(setenv_indents), key=setenv_indents.count)

        final_lines = []
        for entry in self.lines:
            if entry['var'] is None:
                # Preservation line
                final_lines.append(entry['raw'])
                continue

            # Ensure previous line ends with newline if we are appending a new line
            if final_lines and not final_lines[-1].endswith('\n'):
                final_lines[-1] += '\n'
                
            # Apply dominant indentation
            indent = dominant_indent
            if entry['commented']:
                # Commented setenv: [indent]# setenv [var][val_sep][val]
                line_str = f"{indent}setenv {entry['var']}"
                if entry['val'] is not None:
                    val_sep = entry['val_sep'] or " "
                    line_str += f"{val_sep}{entry['val']}"
                line_str = f"# {line_str.lstrip()}"
            else:
                # Active setenv
                if entry['val'] is None:
                    line_str = f"{indent}setenv {entry['var']}"
                else:
                    val_sep = entry['val_sep'] or " "
                    line_str = f"{indent}setenv {entry['var']}{val_sep}{entry['val']}"
            
            # Append trailing comment separator and comment
            if entry['trailing_comment']:
                line_str += entry['sep'] + entry['trailing_comment']
            else:
                line_str += "\n"
            
            final_lines.append(line_str)

        full_content = "".join(final_lines)
        
        if dry_run:
            print("--- DRY RUN: Proposed Changes ---")
            print(full_content)
            print("--- END DRY RUN ---")
        else:
            path = output_path or self.file_path
            with open(path, 'w', encoding='utf-8') as f:
                f.write(full_content)
            print(f"Successfully saved to {path}")

def main():
    parser = argparse.ArgumentParser(description="tcsh setenv Editor")
    parser.add_argument("file", help="Path to the tcsh .csh file")
    parser.add_argument("action", choices=['uncomment', 'update', 'set', 'delete'], help="Action to perform")
    parser.add_argument("--variable", help="Variable name (regex supported)")
    parser.add_argument("--value", help="Value (literal for update/set, regex for uncomment/delete)")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without saving")
    parser.add_argument("--output", help="Output file path (default: overwrite input)")

    args = parser.parse_args()

    if not (args.variable or args.value):
        parser.error("At least one of --variable or --value must be provided.")

    if args.action in ['update', 'set'] and not args.variable:
        parser.error(f"{args.action} action requires --variable to be specified.")

    editor = SetenvEditor(args.file)

    if args.action == 'uncomment':
        editor.uncomment(args.variable, args.value)
    elif args.action == 'update':
        editor.update(args.variable, args.value)
    elif args.action == 'set':
        editor.set_variable(args.variable, args.value)
    elif args.action == 'delete':
        editor.delete(args.variable, args.value)

    editor.save(output_path=args.output, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
