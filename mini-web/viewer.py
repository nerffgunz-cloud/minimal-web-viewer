import curses
import os
import subprocess
import sys
import urllib.parse
import textwrap
import shutil
from html.parser import HTMLParser


def run_extension(event_type, action_name=None, stdscr=None):
    """
    Universal extension runner. 
    - If action_name is given (like for keys: 'r', 'w'), it runs that specific file.
    - If action_name is None (like for folders: 'render', 'read'), it runs ALL files inside that folder.
    """
    folder_path = os.path.join("local/extensions", event_type)
    
    if not os.path.exists(folder_path):
        return False
        
    executed_any = False
    
    # Determine which files to run
    if action_name:
        # Run a specific file (e.g., local/extensions/key/w.py)
        files_to_run = [f"{action_name}.py"]
    else:
        # Run ALL files in the folder (e.g., local/extensions/render/ or read/)
        files_to_run = sorted([f for f in os.listdir(folder_path) if f.endswith(".py")])
        
    for filename in files_to_run:
        script_path = os.path.join(folder_path, filename)
        
        if not os.path.exists(script_path):
            continue
            
        try:
            with open(script_path, "r", encoding="utf-8") as f:
                script_code = f.read()
                
            local_scope = {
                'stdscr': stdscr,
                'file_path': file_path if 'file_path' in locals() else None,
                'cachef_lines': cachef_lines if 'cachef_lines' in globals() else [],
                'interactive_elements': interactive_elements if 'interactive_elements' in globals() else [],
                'raw_html': raw_html if 'raw_html' in globals() else "",
                'read': read,
                'prompt_user_input': prompt_user_input if 'prompt_user_input' in globals() else None,
                'subprocess': subprocess,
                'sys': sys,
                'os': os,
                'globals_dict': globals(),
                
                # --- ADD THESE EXTENSION CALLS & UTILITIES ---
                'InteractiveHTMLParser': InteractiveHTMLParser, # Allows custom parsing or re-parsing
                'details_states': details_states if 'details_states' in globals() else {}, # Preserves dropdown states
            }
            
            exec(script_code, globals(), local_scope)
            executed_any = True
            
        except Exception as e:
            if stdscr:
                curses.endwin()
            print(f"Error running extension {script_path}: {e}")
            input("Press Enter to continue...")
            if stdscr:
                stdscr.refresh()
                
    return executed_any


class InteractiveHTMLParser(HTMLParser):
    def __init__(self, details_states):
        super().__init__()
        self.details_states = details_states
        self.output_lines = []
        self.interactive_elements = []
        
        self._current_line = []
        self._current_tag = None
        self.in_title = False
        self.in_center = False
        
        self.in_script = False
        self.in_style = False
        self.has_script = False
        self.has_css = False
        
        self.details_count = 0
        self.in_summary = False
        self.skip_content = False
        self.details_stack = []

        # List stack and counter tracking for ordered (<ol>) vs unordered (<ul>) lists
        self.list_stack = []
        self.ol_counters = []

    def handle_comment(self, data):
        pass

    def handle_starttag(self, tag, attrs):
        attr_dict = dict(attrs)
        self._current_tag = tag

        if tag in ['meta', 'link']:
            return

        if tag == 'script':
            self.in_script = True
            self.has_script = True
            return

        if tag == 'style':
            self.in_style = True
            self.has_css = True
            return

        if tag == 'title':
            self.in_title = True
            return

        if tag == 'center':
            self.in_center = True
            if self._current_line:
                self.flush_line()
            return

        if tag == 'details':
            d_id = self.details_count
            self.details_count += 1
            self.details_stack.append(d_id)
            if d_id not in self.details_states:
                self.details_states[d_id] = False
            
            if not self.details_states[d_id]:
                self.skip_content = True
            return

        if tag == 'summary' and self.details_stack:
            self.in_summary = True
            d_id = self.details_stack[-1]
            self.interactive_elements.append({
                'type': 'details',
                'details_id': d_id,
                'text': '',
                'line_idx': len(self.output_lines),
                'centered': self.in_center
            })
            self._current_line.append("[+] ")
            return

        
        if self.skip_content:
            return

        # Upgraded horizontal rule <hr>
        if tag == 'hr':
            if self._current_line:
                self.flush_line()
            term_width = shutil.get_terminal_size().columns
            self.output_lines.append(("-" * term_width, self.in_center))
            return

        if tag == 'ul':
            self.list_stack.append('ul')
            self.ol_counters.append(0)
            return

        if tag == 'ol':
            self.list_stack.append('ol')
            self.ol_counters.append(1)
            return

        if tag == 'li':
            if self._current_line:
                self.flush_line()
            if self.list_stack and self.list_stack[-1] == 'ol':
                num = self.ol_counters[-1]
                self._current_line.append(f" {num}. ")
                self.ol_counters[-1] += 1
            else:
                self._current_line.append(" * ")
            return

        if tag == 'input':
            input_type = attr_dict.get('type', 'text')
            if input_type in ['text', 'search']:
                placeholder = attr_dict.get('placeholder', 'Search...')
                default_value = attr_dict.get('value', '')
                self.interactive_elements.append({
                    'type': 'input',
                    'name': attr_dict.get('name', 'q'),
                    'value': default_value,
                    'text': f"[ Input: {placeholder} ]",
                    'line_idx': len(self.output_lines),
                    'centered': self.in_center
                })
                self._current_line.append(f"[ Input: {placeholder} ]")
            return

        if tag == 'details':
            d_id = self.details_count
            self.details_count += 1
            self.details_stack.append(d_id)
            if d_id not in self.details_states:
                self.details_states[d_id] = False
            
            if not self.details_states[d_id]:
                self.skip_content = True
            return

        if tag == 'summary' and self.details_stack:
            self.in_summary = True
            d_id = self.details_stack[-1]
            self.interactive_elements.append({
                'type': 'details',
                'details_id': d_id,
                'text': '',
                'line_idx': len(self.output_lines),
                'centered': self.in_center
            })
            self._current_line.append("[+] ")
            return

        if self.skip_content:
            return

        # Distinct header hierarchy formatting (h1, h2, h3)
        if tag == 'h1':
            if self._current_line:
                self.flush_line()
            self._current_line.append("=== ")
        elif tag == 'h2':
            if self._current_line:
                self.flush_line()
            self._current_line.append("-- ")
        elif tag == 'h3':
            if self._current_line:
                self.flush_line()
            self._current_line.append("- ")

        elif tag == 'a':
            if self._current_line:
                self.flush_line()
            
            href = attr_dict.get('href', '#')
            self.interactive_elements.append({
                'type': 'link',
                'href': href,
                'text': '',
                'line_idx': len(self.output_lines),
                'centered': self.in_center
            })
            self._current_line.append("[Link: ")

        elif tag in ['p', 'div', 'br', 'form']:
            if self._current_line:
                self.flush_line()
            if tag == 'br':
                self.output_lines.append(("", self.in_center))

    def handle_endtag(self, tag):
        if tag in ['meta', 'link', 'hr', 'input']:
            return

        if tag == 'script':
            self.in_script = False
            return

        if tag == 'style':
            self.in_style = False
            return

        if tag == 'title':
            self.in_title = False
            return

        if tag == 'center':
            if self._current_line:
                self.flush_line()
            self.in_center = False
            return

        if tag in ['ul', 'ol']:
            if self.list_stack:
                self.list_stack.pop()
                self.ol_counters.pop()
            return

        if tag == 'details':
            if self.details_stack:
                self.details_stack.pop()
                self.skip_content = any(not self.details_states.get(d, False) for d in self.details_stack)
            return

        if tag == 'summary':
            self.in_summary = False
            self.flush_line()
            return

        if self.skip_content:
            return

        # Closing tags for structured headings
        if tag == 'h1':
            self._current_line.append(" ===")
            self.flush_line()
            self.output_lines.append(("", self.in_center))
        elif tag == 'h2':
            self._current_line.append(" --")
            self.flush_line()
            self.output_lines.append(("", self.in_center))
        elif tag == 'h3':
            self._current_line.append(" -")
            self.flush_line()
            self.output_lines.append(("", self.in_center))
        elif tag == 'a':
            self._current_line.append("]")
            if self.interactive_elements:
                self.interactive_elements[-1]['text'] = "".join(self._current_line)
            self.flush_line()
        elif tag in ['p', 'div', 'li', 'form']:
            self.flush_line()
            if tag != 'li':
                self.output_lines.append(("", self.in_center))

        self._current_tag = None

    def handle_data(self, data):
        if self.in_script or self.in_style or self.in_title:
            return

        if self.in_summary:
            cleaned = data.strip()
            if cleaned:
                self._current_line.append(cleaned)
            return

        if self.skip_content:
            return
        
        cleaned = data.strip()
        if cleaned:
            self._current_line.append(cleaned + " ")
            if self.interactive_elements:
                self.interactive_elements[-1]['text'] = "".join(self._current_line)

    def flush_line(self):
        line_str = "".join(self._current_line).strip()
        if line_str:
            wrapped_chunks = textwrap.wrap(line_str, width=shutil.get_terminal_size().columns)
            for chunk in wrapped_chunks:
                self.output_lines.append((chunk, self.in_center))
        self._current_line = []

    def get_result(self):
        if self._current_line:
            self.flush_line()
        return self.output_lines, self.interactive_elements, self.has_script, self.has_css


# Global state
cachef_lines = []
interactive_elements = []
details_states = {}
page_title = "Simple HTML Viewer"
selected_index = 0
scroll_y = 0
has_js_warning = False
has_css_warning = False



def read(filename="cache.html", stdscr=None):
    global cachef_lines, interactive_elements, page_title, details_states, has_js_warning, has_css_warning, scroll_y
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as file:
                raw_html = file.read()
        except UnicodeDecodeError:
            # ... fallback ...
            return

        # === ADD THIS: Allow HTML extensions to modify raw_html before parsing ===
        # We can expose raw_html to the extension scope
        global_scope = globals()
        global_scope['raw_html'] = raw_html
        
        # Run any scripts in local/extensions/html/
        run_extension("html", stdscr=stdscr)
        
        # Pull back any modifications the extension might have made to raw_html
        if 'raw_html' in globals():
            raw_html = globals()['raw_html']

        if "<title>" in raw_html and "</title>" in raw_html:
            start = raw_html.find("<title>") + 7
            end = raw_html.find("</title>", start)
            page_title = raw_html[start:end].strip()

        parser = InteractiveHTMLParser(details_states)
        parser.feed(raw_html)
        
        cachef_lines, interactive_elements, has_js_warning, has_css_warning = parser.get_result()
        scroll_y = 0

        # === HOOK 1: Run extensions that want to modify content at the TOP ===
        run_extension("read_top", stdscr=stdscr)

        # === HOOK 2: Run extensions that want to append at the BOTTOM ===
        run_extension("read", stdscr=stdscr)

    else:
        cachef_lines = [(f"Error: '{filename}' not found.", False)]
        interactive_elements = []
        has_js_warning = False
        has_css_warning = False

def prompt_user_input(stdscr, prompt_text, initial_text=""):
    max_y, max_x = stdscr.getmaxyx()
    input_str = initial_text  # Initialize with the prefix (e.g., "@")
    
    stdscr.timeout(-1)
    
    try:
        while True:
            stdscr.move(max_y - 1, 0)
            stdscr.clrtoeol()
            display_str = f"{prompt_text}: {input_str}"
            try:
                stdscr.addstr(max_y - 1, 0, display_str[:max_x - 1], curses.A_REVERSE)
            except curses.error:
                pass
            stdscr.refresh()
            
            ch = stdscr.getch()
            
            if ch in [10, 13, curses.KEY_ENTER]:
                return input_str.strip()
            elif ch == 27:
                return None
            elif ch in [curses.KEY_BACKSPACE, 127, 8]:
                # Prevent deleting the mandatory prefix if you want to lock it in, 
                # or allow deleting it if you want flexibility. 
                # Keeping len(input_str) > len(initial_text) protects the prefix from being deleted:
                if len(input_str) > len(initial_text):
                    input_str = input_str[:-1]
            elif 32 <= ch <= 126:
                input_str += chr(ch)
    finally:
        stdscr.timeout(50)


def main(stdscr):
    # Declare all global variables right at the top of the function here:
    global selected_index, details_states, scroll_y, cachef_lines, interactive_elements
    run_extension("global", stdscr=stdscr)

    read("cache.html")

    stdscr.timeout(50)
    curses.curs_set(0)

    left_intro = "Simple html Viewer v0.9 ([q] Quit, [h] Home, [r] Reload, [s] Search, [i] install)"

    try:
        while True:
            key = stdscr.getch()
            max_y, max_x = stdscr.getmaxyx()
            visible_height = max_y - 2

            if key == curses.KEY_RIGHT:
                if interactive_elements:
                    selected_index = (selected_index + 1) % len(interactive_elements)
                    elem_line = interactive_elements[selected_index]['line_idx']
                    if elem_line < scroll_y:
                        scroll_y = elem_line
                    elif elem_line >= scroll_y + visible_height:
                        scroll_y = elem_line - visible_height + 1
            elif key == curses.KEY_LEFT:
                if interactive_elements:
                    selected_index = (selected_index - 1) % len(interactive_elements)
                    elem_line = interactive_elements[selected_index]['line_idx']
                    if elem_line < scroll_y:
                        scroll_y = elem_line
                    elif elem_line >= scroll_y + visible_height:
                        scroll_y = elem_line - visible_height + 1

            elif key == curses.KEY_UP:
                if scroll_y > 0:
                    scroll_y -= 1
            elif key == curses.KEY_DOWN:
                if scroll_y < max(0, len(cachef_lines) - visible_height):
                    scroll_y += 1
            elif key == curses.KEY_PPAGE:
                scroll_y = max(0, scroll_y - visible_height)
            elif key == curses.KEY_NPAGE:
                scroll_y = min(max(0, len(cachef_lines) - visible_height), scroll_y + visible_height)
            
            elif key in [10, 13, curses.KEY_ENTER]:
                if interactive_elements and 0 <= selected_index < len(interactive_elements):
                    item = interactive_elements[selected_index]
                    if item['type'] == 'details':
                        d_id = item['details_id']
                        details_states[d_id] = not details_states[d_id]
                        read("cache.html")
                        if selected_index >= len(interactive_elements):
                            selected_index = max(0, len(interactive_elements) - 1)


                    elif item['type'] == 'link':
                        url = item['href']
                        
                        # === INTERCEPT NIBBLE CONSOLE INPUT ===
                        if url == "nibble-action://input":
                            val = prompt_user_input(stdscr, "Nibble Console Input")
                            if val:
                                with open("nibble_input.txt", "w") as f:
                                    f.write(val)
                                read("cache.html", stdscr)
                                selected_index = 0
                                scroll_y = 0
                            continue
                        # ======================================

                        # Check if it's a local file path rather than a web URL
                        if not url.startswith("http://") and not url.startswith("https://"):
                            # ... (rest of standard local file handling)
                            if os.path.exists(url):
                                with open(url, "r", encoding="utf-8") as f:
                                    local_content = f.read()
                                with open("cache.html", "w", encoding="utf-8") as f:
                                    f.write(local_content)
                                read("cache.html")
                                selected_index = 0
                                scroll_y = 0
                            else:
                                cachef_lines = [(f"Error: Local file '{url}' not found.", False)]
                                interactive_elements = []
                        else:
                            subprocess.run([sys.executable, "mwd.py"], input=url + "\n", text=True)
                            read("cache.html")
                            selected_index = 0
                            scroll_y = 0


                    elif item['type'] == 'input':
                        # Grab the default value from the HTML input tag (e.g. "@wikipedia-clone/")
                        initial_val = item.get('value', '')
                        query = prompt_user_input(stdscr, f"Search ({item['name']})", initial_text=initial_val)
                        if query:
                            # If the resulting string starts with @, use it directly as the target query path
                            if query.startswith("@"):
                                target_url = query
                            else:
                                target_url = f"@{query}"
                                
                            subprocess.run([sys.executable, "mwd.py"], input=target_url + "\n", text=True)
                            read("cache.html")
                            selected_index = 0
                            scroll_y = 0


            elif key == ord('s') or key == ord('S'):
                query = prompt_user_input(stdscr, "Enter URL or Search Query")
                if query:
                    if query.startswith("http://") or query.startswith("https://"):
                        target_url = query
                    elif "." in query and " " not in query:
                        target_url = "https://" + query
                    else:
                        encoded_query = urllib.parse.quote_plus(query)
                        target_url = f"https://lite.duckduckgo.com/lite/?q={encoded_query}"

                    subprocess.run([sys.executable, "mwd.py"], input=target_url + "\n", text=True)
                    read("cache.html")
                    selected_index = 0
                    scroll_y = 0

            elif key == ord('i') or key == ord('I'):
                # Temporarily leave curses mode so the installer can print/input normally in the terminal
                curses.endwin()
                
                print("\nLaunching MWB Package Installer...")
                subprocess.run([sys.executable, "installer.py"])
                
                input("\nInstallation finished. Press Enter to return to the browser...")
                
                # Resume curses mode and redraw the screen
                stdscr.refresh()
                read("cache.html")
                selected_index = 0
                scroll_y = 0


            elif key == ord('h') or key == ord('H'):
                if os.path.exists("home.html"):
                    with open("home.html", "r", encoding="utf-8") as h_file:
                        home_data = h_file.read()
                    with open("cache.html", "w", encoding="utf-8") as c_file:
                        c_file.write(home_data)
                read("cache.html")
                selected_index = 0
                scroll_y = 0

            # When a key is pressed, check if an extension script exists for it
            elif (ord('a') <= key <= ord('z')) or (ord('A') <= key <= ord('Z')):
                key_char = chr(key).lower()
                
                # Executes extensions/key/w.py or extensions/key/x.py natively
                executed = run_extension("key", key_char, stdscr)
                
                if executed:
                    # The extension can freely modify global variables, 
                    # and we just ensure the view resets/redraws safely
                    selected_index = 0
                    scroll_y = 0
            
            # rendering scripts

            run_extension("render", stdscr=stdscr)

            stdscr.clear()

            warnings = []
            if has_js_warning:
                warnings.append("JS Ignored")
            if has_css_warning:
                warnings.append("CSS Ignored")
            warn_str = " | ".join(warnings)
            if warn_str:
                warn_str = f" [{warn_str}]"

            right_title = f"{warn_str} Page: {page_title} "
            
            spacing = max_x - len(left_intro) - len(right_title)
            if spacing < 0:
                spacing = 0
            header_bar = left_intro + (" " * spacing) + right_title
            
            try:
                stdscr.addstr(0, 0, header_bar[:max_x - 1], curses.A_REVERSE)
            except curses.error:
                pass

            for i in range(visible_height):
                line_idx = scroll_y + i
                if line_idx < len(cachef_lines):
                    line_text, is_centered = cachef_lines[line_idx]
                    
                    x_pos = 0
                    if is_centered and line_text:
                        x_pos = max(0, (max_x - len(line_text)) // 2)

                    is_selected_line = False
                    for idx, elem in enumerate(interactive_elements):
                        if idx == selected_index and elem.get('line_idx') == line_idx:
                            is_selected_line = True
                            break

                    try:
                        max_draw_x = max_x - x_pos - 1 if (2 + i == max_y - 1) else max_x - x_pos
                        if max_draw_x > 0:
                            if is_selected_line:
                                stdscr.addstr(2 + i, x_pos, line_text[:max_draw_x], curses.A_REVERSE)
                            else:
                                stdscr.addstr(2 + i, x_pos, line_text[:max_draw_x])
                    except curses.error:
                        pass

            stdscr.refresh()

            if key == ord('q') or key == ord('Q'):
                break
            elif key == ord('r') or key == ord('R'):
                read("cache.html")
                selected_index = 0
                scroll_y = 0

    finally:
        pass

if __name__ == "__main__":
    curses.wrapper(main)
