#!/usr/bin/env python3
import re
import sys
import argparse
import os

class IcvEditor:
    def __init__(self, file_path):
        self.file_path = file_path
        self.lines = [] # List of dicts: {'raw': str, 'commented': bool, 'var': str, 'val': str, 'indent': str, 'val_sep': str, 'sep': str, 'trailing_comment': str}
        self.load()

    def load(self):
        if not os.path.exists(self.file_path):
            return

        with open(self.file_path, 'r', encoding='utf-8') as f:
            raw_lines = f.readlines()

        in_block_comment = False
        ifdef_depth = 0

        for line in raw_lines:
            stripped = line.strip()

            # 1. Block comment tracking
            if in_block_comment:
                self.lines.append({
                    'raw': line, 'commented': True, 'var': None, 'val': None,
                    'indent': "", 'val_sep': "", 'sep': "", 'trailing_comment': ""
                })
                if '*/' in line:
                    in_block_comment = False
                continue

            if '/*' in line:
                self.lines.append({
                    'raw': line, 'commented': True, 'var': None, 'val': None,
                    'indent': "", 'val_sep': "", 'sep': "", 'trailing_comment': ""
                })
                if '*/' not in line:
                    in_block_comment = True
                continue

            # 2. Preprocessor directive tracking (ignore defines inside ifdef/ifndef/if blocks)
            is_directive = False
            if not stripped.startswith('//') and stripped.startswith('#'):
                if re.match(r'^#\s*(ifdef|ifndef|if)\b', stripped):
                    ifdef_depth += 1
                    is_directive = True
                elif re.match(r'^#\s*endif\b', stripped):
                    if ifdef_depth > 0:
                        ifdef_depth -= 1
                    is_directive = True
                elif re.match(r'^#\s*(else|elif)\b', stripped):
                    is_directive = True

            if is_directive or ifdef_depth > 0:
                self.lines.append({
                    'raw': line, 'commented': stripped.startswith('//'), 'var': None, 'val': None,
                    'indent': "", 'val_sep': "", 'sep': "", 'trailing_comment': ""
                })
                continue

            # 3. Parse line comments and split into define part and trailing comment part
            is_commented = stripped.startswith('//')
            trailing_comment = ""
            define_part = line

            if is_commented:
                # For commented lines like: // #define VAR 0.001 // description
                # We need to find the trailing comment AFTER the #define content
                first_comment_idx = line.find('//')
                # Skip past the leading '//' and any whitespace to find #define content
                content_start = first_comment_idx + 2
                # Find the #define part first
                define_match = re.search(r'#define\s+\S+(?:\s+\S+)?', line[content_start:])
                if define_match:
                    define_end = content_start + define_match.end()
                    # Look for trailing // comment after the #define content
                    trailing_idx = line.find('//', define_end)
                    if trailing_idx != -1:
                        define_part = line[:trailing_idx]
                        trailing_comment = line[trailing_idx:]
                else:
                    # No #define found, keep as-is
                    pass
            else:
                comment_idx = line.find('//')
                if comment_idx != -1:
                    define_part = line[:comment_idx]
                    trailing_comment = line[comment_idx:]

            # Calculate exact space separation before the trailing comment
            stripped_define = define_part.rstrip()
            sep = define_part[len(stripped_define):]

            # 4. Parse #define in the define part
            match = re.search(r'^(\s*)(//)?(\s*)#define\s+([^\s]+)(?:(\s+)(.+))?$', stripped_define)
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
                self.lines.append({
                    'raw': line,
                    'commented': stripped.startswith('//'),
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

    def uncomment(self, var_pattern, val_pattern=None):
        changed = False
        for entry in self.lines:
            if not entry['commented'] or entry['var'] is None:
                continue

            if self._match(var_pattern, entry['var']):
                if val_pattern and not self._match(val_pattern, entry['val']):
                    continue

                entry['commented'] = False
                changed = True
        return changed

    def update(self, var_pattern, new_value):
        self.uncomment(var_pattern)

        changed = False
        for entry in self.lines:
            if entry['commented'] or entry['var'] is None:
                continue

            if self._match(var_pattern, entry['var']):
                entry['val'] = str(new_value) if new_value is not None else None
                changed = True
        return changed

    def set_variable(self, var, val):
        if self.update(f"^{re.escape(var)}$", val):
            return True

        self.lines.append({
            'raw': "",
            'commented': False,
            'var': var,
            'val': str(val) if val is not None else None,
            'indent': "",
            'val_sep': "    ",
            'sep': " ",
            'trailing_comment': ""
        })
        return True

    def delete(self, var_pattern, val_pattern=None):
        changed = False
        for entry in self.lines:
            if entry['commented'] or entry['var'] is None:
                continue

            if self._match(var_pattern, entry['var']):
                if val_pattern and not self._match(val_pattern, entry['val']):
                    continue

                entry['commented'] = True
                changed = True
        return changed

    def save(self, output_path=None, dry_run=False):
        # Determine dominant indentation for #define lines
        define_indents = [entry['indent'] for entry in self.lines if entry['var'] is not None]
        dominant_indent = ""
        if define_indents:
            dominant_indent = max(set(define_indents), key=define_indents.count)

        final_lines = []
        for entry in self.lines:
            if entry['var'] is None:
                final_lines.append(entry['raw'])
                continue

            # Ensure previous line ends with newline if we are appending a new line
            if final_lines and not final_lines[-1].endswith('\n'):
                final_lines[-1] += '\n'

            indent = dominant_indent
            if entry['commented']:
                # Commented define: [indent]// #define [var][val_sep][val]
                line_str = f"{indent}// #define {entry['var']}"
                if entry['val'] is not None:
                    val_sep = entry['val_sep'] or "    "
                    line_str += f"{val_sep}{entry['val']}"
            else:
                # Active define: [indent]#define [var][val_sep][val]
                if entry['val'] is None:
                    line_str = f"{indent}#define {entry['var']}"
                else:
                    val_sep = entry['val_sep'] or "    "
                    line_str = f"{indent}#define {entry['var']}{val_sep}{entry['val']}"

            # Append the trailing comment separator and the trailing comment
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
    if hasattr(sys.stdout, 'reconfigure'):
        sys.stdout.reconfigure(encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'reconfigure'):
        sys.stderr.reconfigure(encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(description="IC Validator #define Editor")
    parser.add_argument("file", help="Path to the .pxl runset file")
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

    editor = IcvEditor(args.file)

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
