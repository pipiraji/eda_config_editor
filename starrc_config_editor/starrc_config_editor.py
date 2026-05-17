#!/usr/bin/env python3
import re
import sys
import argparse
import os

class StarrcEditor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.lines = [] # List of dicts: {'raw': str, 'commented': bool, 'cmd': str, 'val': str, 'sep': str, 'indent': str}
        self.load()

    def load(self):
        if not os.path.exists(self.file_path):
            return

        with open(self.file_path, 'r', encoding='utf-8') as f:
            raw_lines = f.readlines()

        for line in raw_lines:
            stripped = line.strip()
            if not stripped:
                self.lines.append({'raw': line, 'commented': False, 'cmd': None, 'val': None, 'sep': None, 'indent': ""})
                continue

            # StarRC Comment: starts with *
            commented = stripped.startswith('*')
            content = stripped.lstrip('*').strip()
            
            # Match COMMAND: VALUE or COMMAND VALUE
            # We look for the first colon or space as separator
            match = re.search(r'^([^:\s]+)([:\s]+)(.*)$', content)
            
            if match:
                cmd = match.group(1)
                sep = match.group(2)
                val = match.group(3).strip()
                self.lines.append({
                    'raw': line,
                    'commented': commented,
                    'cmd': cmd,
                    'val': val,
                    'sep': sep,
                    'indent': line[:len(line) - len(line.lstrip())]
                })
            else:
                # Unknown format or just a single word
                self.lines.append({
                    'raw': line,
                    'commented': commented,
                    'cmd': content,
                    'val': "",
                    'sep': " ",
                    'indent': line[:len(line) - len(line.lstrip())]
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

    def uncomment(self, cmd_pattern, val_pattern=None):
        changed = False
        for entry in self.lines:
            if not entry['commented']:
                continue
            
            if self._match(cmd_pattern, entry['cmd']):
                if val_pattern and not self._match(val_pattern, entry['val']):
                    continue
                
                entry['commented'] = False
                changed = True
        return changed

    def update(self, cmd_pattern, new_value):
        # 1. Uncomment matching lines first
        self.uncomment(cmd_pattern)
        
        changed = False
        for entry in self.lines:
            if entry['commented']:
                continue
            
            if self._match(cmd_pattern, entry['cmd']):
                entry['val'] = str(new_value)
                changed = True
        return changed

    def set_command(self, cmd, val):
        # 1. Try update first (use literal matching for set)
        if self.update(f"^{re.escape(cmd)}$", val):
            return True
        
        # 2. If not found, append to the end
        # Find dominant separator (default to ": ")
        seps = [l['sep'] for l in self.lines if l['sep']]
        dominant_sep = max(set(seps), key=seps.count) if seps else ": "
        
        self.lines.append({
            'raw': "", # New line
            'commented': False,
            'cmd': cmd,
            'val': val,
            'sep': dominant_sep,
            'indent': ""
        })
        return True

    def delete(self, cmd_pattern, val_pattern=None):
        changed = False
        for entry in self.lines:
            if entry['commented'] or not entry['cmd']:
                continue
            
            if self._match(cmd_pattern, entry['cmd']):
                if val_pattern and not self._match(val_pattern, entry['val']):
                    continue
                
                entry['commented'] = True
                changed = True
        return changed

    def save(self, output_path=None, dry_run=False):
        final_lines = []
        for entry in self.lines:
            if entry['cmd'] is None:
                # Blank line
                final_lines.append(entry['raw'])
                continue
                
            line_str = f"{entry['indent']}{entry['cmd']}{entry['sep']}{entry['val']}"
            if entry['commented']:
                line_str = f"*{line_str.lstrip()}"
            
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
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(description="StarRC Configuration Editor")
    parser.add_argument("file", help="Path to the StarRC .cmd file")
    parser.add_argument("action", choices=['uncomment', 'update', 'set', 'delete'], help="Action to perform")
    parser.add_argument("--command", help="Command name (regex supported)")
    parser.add_argument("--value", help="Value (literal for update/set, regex for uncomment/delete)")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without saving")
    parser.add_argument("--output", help="Output file path (default: overwrite input)")

    args = parser.parse_args()

    if not (args.command or args.value):
        parser.error("At least one of --command or --value must be provided.")

    editor = StarrcEditor(args.file)

    if args.action == 'uncomment':
        editor.uncomment(args.command, args.value)
    elif args.action == 'update':
        if args.value is None:
            print("Error: --value is required for update")
            sys.exit(1)
        editor.update(args.command, args.value)
    elif args.action == 'set':
        if not args.command:
            print("Error: --command is required for set")
            sys.exit(1)
        if args.value is None:
            print("Error: --value is required for set")
            sys.exit(1)
        editor.set_command(args.command, args.value)
    elif args.action == 'delete':
        editor.delete(args.command, args.value)

    editor.save(output_path=args.output, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
