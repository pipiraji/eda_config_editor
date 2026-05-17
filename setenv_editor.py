import re
import sys
import argparse
import os

class SetenvEditor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.lines = [] # List of dicts: {'raw': str, 'commented': bool, 'var': str, 'val': str, 'indent': str}
        self.load()

    def load(self):
        if not os.path.exists(self.file_path):
            return

        with open(self.file_path, 'r', encoding='utf-8') as f:
            raw_lines = f.readlines()

        for line in raw_lines:
            stripped = line.strip()
            if not stripped:
                self.lines.append({'raw': line, 'commented': False, 'var': None, 'val': None, 'indent': ""})
                continue

            # tcsh setenv format: [indent] [#] [whitespace] setenv VAR [VAL]
            # Match optional leading whitespace, optional comments, optional whitespace, setenv, variable, and optional value
            match = re.search(r'^(\s*)(#+)?(\s*)setenv\s+([^\s]+)(?:\s+(.*))?$', line.rstrip())
            
            if match:
                commented = match.group(2) is not None
                indent = match.group(1)
                var = match.group(4)
                val = match.group(5)
                self.lines.append({
                    'raw': line,
                    'commented': commented,
                    'var': var,
                    'val': val,
                    'indent': indent
                })
            else:
                # Other lines (comments without setenv, empty lines already handled, etc.)
                self.lines.append({
                    'raw': line,
                    'commented': stripped.startswith('#'),
                    'var': None,
                    'val': None,
                    'indent': ""
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
            'indent': ""
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
                
            # Apply dominant indentation
            indent = dominant_indent
            if entry['val'] is None:
                line_str = f"{indent}setenv {entry['var']}"
            else:
                line_str = f"{indent}setenv {entry['var']} {entry['val']}"
                
            if entry['commented']:
                # For setenv_editor, we follow the # setenv style for delete, 
                # but uncomment removes all #.
                line_str = f"# {line_str.lstrip()}"
            
            final_lines.append(line_str + "\n")

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
