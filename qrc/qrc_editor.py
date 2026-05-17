import re
import sys
import argparse
import os

class QrcEditor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.lines = []  # List of dicts: {'raw': str, 'commented': bool, 'cmd': str, 'opt': str, 'val': str, 'is_cmd_line': bool}
        self.load()

    def load(self):
        if not os.path.exists(self.file_path):
            return

        with open(self.file_path, 'r', encoding='utf-8') as f:
            raw_lines = f.readlines()

        current_cmd = None
        for line in raw_lines:
            stripped = line.strip()
            if not stripped:
                self.lines.append({'raw': line, 'commented': False, 'cmd': None, 'opt': None, 'val': None, 'is_cmd_line': False, 'indent': ""})
                continue

            commented = stripped.startswith('#')
            content = stripped.lstrip('#').strip()
            clean_content = content.rstrip('\\').strip()
            
            if not clean_content:
                self.lines.append({'raw': line, 'commented': commented, 'cmd': current_cmd, 'opt': None, 'val': None, 'is_cmd_line': False, 'indent': line[:line.find(stripped)]})
                continue

            parts = clean_content.split()
            indent = line[:line.find(stripped)]

            if not parts[0].startswith('-'):
                # Command line
                cmd = parts[0]
                current_cmd = cmd
                # Add command entry
                self.lines.append({
                    'raw': line,
                    'commented': commented,
                    'cmd': cmd,
                    'opt': None,
                    'val': None,
                    'is_cmd_line': True,
                    'indent': indent
                })
                # If there's an option on the same line
                if len(parts) > 1:
                    virtual_opt = {
                        'raw': "", # Virtual
                        'commented': commented,
                        'cmd': cmd,
                        'opt': parts[1],
                        'val': " ".join(parts[2:]),
                        'is_cmd_line': False,
                        'indent': "\t"
                    }
                    self.lines.append(virtual_opt)
                    # print(f"DEBUG: Added virtual option: {virtual_opt}")
            else:
                # Option line
                opt_line = {
                    'raw': line,
                    'commented': commented,
                    'cmd': current_cmd,
                    'opt': parts[0],
                    'val': " ".join(parts[1:]),
                    'is_cmd_line': False,
                    'indent': indent
                }
                self.lines.append(opt_line)
                # print(f"DEBUG: Added option line: {opt_line}")
        
        # print(f"DEBUG: Total lines parsed: {len(self.lines)}")

    def _match(self, pattern, target):
        if pattern is None:
            return True
        if target is None:
            return False
        try:
            return re.fullmatch(pattern, target) is not None
        except re.error:
            return pattern == target

    def uncomment(self, cmd_pattern, opt_pattern=None, val_pattern=None):
        changed = False
        uncommented_cmds = set()
        for entry in self.lines:
            if not entry['commented']:
                continue
            
            # Check command match
            if not self._match(cmd_pattern, entry['cmd']):
                continue
            
            # Check option match if provided
            if opt_pattern and not self._match(opt_pattern, entry['opt']):
                continue
            
            # Check value match if provided
            if val_pattern and not self._match(val_pattern, entry['val']):
                continue
            
            # Uncomment
            entry['commented'] = False
            changed = True
            if entry['cmd']:
                uncommented_cmds.add(entry['cmd'])
        
        # If any option was uncommented, ensure the command line is also uncommented
        if uncommented_cmds:
            for entry in self.lines:
                if entry['cmd'] in uncommented_cmds and entry['is_cmd_line']:
                    if entry['commented']:
                        entry['commented'] = False
                        changed = True
        return changed

    def update(self, cmd_pattern, opt_pattern, new_value):
        # 1. Uncomment first
        self.uncomment(cmd_pattern, opt_pattern)
        
        changed = False
        for entry in self.lines:
            if entry['commented']:
                continue
            
            if self._match(cmd_pattern, entry['cmd']) and self._match(opt_pattern, entry['opt']):
                entry['val'] = str(new_value)
                changed = True
        return changed

    def set_option(self, cmd, opt, val):
        # 1. Try update first (use literal matching for set)
        if self.update(f"^{re.escape(cmd)}$", f"^{re.escape(opt)}$", val):
            return True
        
        # 2. If no match, add to all matching commands (literal match)
        matching_cmds = set()
        for entry in self.lines:
            if entry['cmd'] == cmd:
                matching_cmds.add(entry['cmd'])
        
        if not matching_cmds:
            print(f"Warning: No command matching '{cmd}' found to set option '{opt}'")
            return False

        for target_cmd in matching_cmds:
            # Ensure the command line itself is uncommented
            for entry in self.lines:
                if entry['cmd'] == target_cmd and entry['is_cmd_line']:
                    entry['commented'] = False
                    break

            # Find last line of this command
            last_idx = -1
            target_indent = "\t" # Default
            for i, entry in enumerate(self.lines):
                if entry['cmd'] == target_cmd:
                    last_idx = i
                    if entry['indent']:
                        target_indent = entry['indent']
            
            if last_idx != -1:
                # Insert new option after last_idx
                new_entry = {
                    'raw': "", # Virtual
                    'commented': False,
                    'cmd': target_cmd,
                    'opt': opt,
                    'val': val,
                    'is_cmd_line': False,
                    'indent': target_indent
                }
                self.lines.insert(last_idx + 1, new_entry)
        return True

    def delete(self, cmd_pattern, opt_pattern=None, val_pattern=None):
        changed = False
        for entry in self.lines:
            if entry['commented']:
                continue
            
            if self._match(cmd_pattern, entry['cmd']):
                if opt_pattern and not self._match(opt_pattern, entry['opt']):
                    continue
                if val_pattern and not self._match(val_pattern, entry['val']):
                    continue
                
                entry['commented'] = True
                changed = True
        
        # Cascade Commenting: If a command has no active options, comment the command line too
        if changed:
            self._cascade_commenting()
            
        return changed

    def _cascade_commenting(self):
        # Group by command
        cmds = {}
        for i, entry in enumerate(self.lines):
            if entry['cmd']:
                if entry['cmd'] not in cmds:
                    cmds[entry['cmd']] = []
                cmds[entry['cmd']].append(i)
        
        for cmd, indices in cmds.items():
            active_options = False
            cmd_line_idx = -1
            for idx in indices:
                entry = self.lines[idx]
                if entry['is_cmd_line']:
                    cmd_line_idx = idx
                elif not entry['commented'] and entry['opt']:
                    active_options = True
                    break
            
            if not active_options and cmd_line_idx != -1:
                self.lines[cmd_line_idx]['commented'] = True

    def save(self, output_path=None, dry_run=False):
        # Determine dominant indentation for commands and options
        cmd_indents = [entry['indent'] for entry in self.lines if entry['is_cmd_line']]
        opt_indents = [entry['indent'] for entry in self.lines if entry['opt'] is not None]
        
        dominant_cmd_indent = ""
        if cmd_indents:
            dominant_cmd_indent = max(set(cmd_indents), key=cmd_indents.count)
            
        dominant_opt_indent = "\t" # Default
        if opt_indents:
            non_empty_opt_indents = [i for i in opt_indents if i]
            if non_empty_opt_indents:
                dominant_opt_indent = max(set(non_empty_opt_indents), key=non_empty_opt_indents.count)

        final_lines = []
        
        # We'll iterate through lines and determine if a backslash is needed
        # A backslash is needed if the current line is a non-commented command/option
        # AND the next non-commented line belongs to the same command block.
        
        for i, entry in enumerate(self.lines):
            # Apply dominant indentation
            if entry['opt']:
                entry['indent'] = dominant_opt_indent
            elif entry['is_cmd_line']:
                entry['indent'] = dominant_cmd_indent

            # 1. Build the base string for the line
            if entry['opt']: # Option line
                line_str = f"{entry['indent']}{entry['opt']} {entry['val']}"
            elif entry['is_cmd_line']:
                line_str = f"{entry['indent']}{entry['cmd']}"
            else:
                # Empty line or original raw text (likely empty or just whitespace)
                # But we should be careful with original comments
                if entry['raw'].strip().startswith('#') and not entry['cmd']:
                    line_str = entry['raw'].strip().lstrip('#').strip()
                else:
                    line_str = entry['raw'].rstrip('\r\n')
            
            # 2. Handle comment status
            if entry['commented']:
                if not line_str.startswith('#'):
                    # Preserve indentation for commented lines
                    orig_indent = ""
                    stripped_line = line_str.lstrip()
                    orig_indent = line_str[:len(line_str) - len(stripped_line)]
                    line_str = f"{orig_indent}# {stripped_line}"
            elif not entry['commented'] and line_str.startswith('#'):
                # Was commented, now not. Remove # and leading space
                line_str = line_str.lstrip('#').strip()
            
            # 3. Determine if backslash is needed
            # Backslash is only for active (non-commented) command/option lines
            if not entry['commented'] and (entry['is_cmd_line'] or entry['opt']):
                # Find the next active line in the same command block
                has_next_active = False
                for j in range(i + 1, len(self.lines)):
                    next_entry = self.lines[j]
                    if not next_entry['commented']:
                        if next_entry['cmd'] == entry['cmd'] and (next_entry['is_cmd_line'] or next_entry['opt']):
                            has_next_active = True
                            break
                        elif next_entry['cmd'] and next_entry['cmd'] != entry['cmd']:
                            # New command block started
                            break
                        elif next_entry['raw'].strip():
                            # Some other non-empty content
                            break
                
                if has_next_active:
                    line_str = line_str.rstrip('\\ ') + " \\"
                else:
                    line_str = line_str.rstrip('\\ ')
            
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
    parser = argparse.ArgumentParser(description="QRC Configuration Editor")
    parser.add_argument("file", help="Path to the QRC .tcl file")
    parser.add_argument("action", choices=['uncomment', 'update', 'set', 'delete'], help="Action to perform")
    parser.add_argument("--command", help="Command (regex supported)")
    parser.add_argument("--option", help="Option (regex supported)")
    parser.add_argument("--value", help="Value (regex supported for uncomment/delete, literal for update/set)")
    parser.add_argument("--dry-run", action="store_true", help="Show changes without saving")
    parser.add_argument("--output", help="Output file path (default: overwrite input)")

    args = parser.parse_args()

    if not (args.command or args.option or args.value):
        parser.error("At least one of --command, --option, or --value must be provided.")

    if args.option:
        if args.option.startswith('-'):
            print(f"Error: --option 인자에 하이픈('-')을 포함하지 마세요. (입력값: '{args.option}')")
            sys.exit(1)
        args.option = '-' + args.option

    editor = QrcEditor(args.file)

    if args.action == 'uncomment':
        editor.uncomment(args.command, args.option, args.value)
    elif args.action == 'update':
        if not args.option or args.value is None:
            print("Error: --option and --value are required for update")
            sys.exit(1)
        editor.update(args.command, args.option, args.value)
    elif args.action == 'set':
        if not args.command or not args.option or args.value is None:
            print("Error: --command, --option and --value are required for set")
            sys.exit(1)
        editor.set_option(args.command, args.option, args.value)
    elif args.action == 'delete':
        editor.delete(args.command, args.option, args.value)

    editor.save(output_path=args.output, dry_run=args.dry_run)

if __name__ == "__main__":
    main()
