import curses
import os
import subprocess
import sys
import urllib.parse
from html.parser import HTMLParser

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

    def handle_comment(self, data):
        # Ignore and hide HTML comments <!-- ... -->
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

        if tag == 'hr':
            if self._current_line:
                self.flush_line()
            self.output_lines.append(("-" * 30, self.in_center))
            return

        if tag == 'li':
            if self._current_line:
                self.flush_line()
            self._current_line.append(" * ")
            return

        # Handle form input boxes for local database searching
        if tag == 'input':
            input_type = attr_dict.get('type', 'text')
            if input_type in ['text', 'search']:
                placeholder = attr_dict.get('placeholder', 'Search...')
                self.interactive_elements.append({
                    'type': 'input',
                    'name': attr_dict.get('name', 'q'),
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

        if tag in ['h1', 'h2', 'h3']:
            if self._current_line:
                self.flush_line()
            self._current_line.append("=== ")

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

        elif tag in ['p', 'div', 'br', 'ul', 'ol', 'form']:
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

        if tag in ['h1', 'h2', 'h3']:
            self._current_line.append(" ===")
            self.flush_line()
            self.output_lines.append(("", self.in_center))
        elif tag == 'a':
            self._current_line.append("]")
            if self.interactive_elements:
                self.interactive_elements[-1]['text'] = "".join(self._current_line)
            self.flush_line()
        elif tag in ['p', 'div', 'li', 'ul', 'ol', 'form']:
            self.flush_line()
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
            self.output_lines.append((line_str, self.in_center))
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

def read(filename="cache.html"):
    global cachef_lines, interactive_elements, page_title, details_states, has_js_warning, has_css_warning, scroll_y
    if os.path.exists(filename):
        try:
            with open(filename, "r", encoding="utf-8") as file:
                raw_html = file.read()
        except UnicodeDecodeError:
            cachef_lines = [
                ("File downloaded successfully into the /downloads folder.", True),
                ("Press [h] to return to Home.", True)
            ]
            interactive_elements = []
            page_title = "Download Complete"
            has_js_warning = False
            has_css_warning = False
            scroll_y = 0
            return

        if "<title>" in raw_html and "</title>" in raw_html:
            start = raw_html.find("<title>") + 7
            end = raw_html.find("</title>", start)
            page_title = raw_html[start:end].strip()

        parser = InteractiveHTMLParser(details_states)
        parser.feed(raw_html)
        cachef_lines, interactive_elements, has_js_warning, has_css_warning = parser.get_result()
        scroll_y = 0
    else:
        cachef_lines = [(f"Error: '{filename}' not found.", False)]
        interactive_elements = []
        has_js_warning = False
        has_css_warning = False

def prompt_user_input(stdscr, prompt_text):
    max_y, max_x = stdscr.getmaxyx()
    input_str = ""
    
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
                if len(input_str) > 0:
                    input_str = input_str[:-1]
            elif 32 <= ch <= 126:
                input_str += chr(ch)
    finally:
        stdscr.timeout(50)

def main(stdscr):
    global selected_index, details_states, scroll_y
    read("cache.html")

    stdscr.timeout(50)
    curses.curs_set(0)

    left_intro = "Simple html Viewer v0.6 ([q] Quit, [h] Home, [r] Reload, [s] Search)"

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
                        subprocess.run([sys.executable, "mwd.py"], input=url + "\n", text=True)
                        read("cache.html")
                        selected_index = 0
                        scroll_y = 0
                    elif item['type'] == 'input':
                        # Intercept Enter key on page input textboxes to trigger search/queries
                        query = prompt_user_input(stdscr, f"Search ({item['name']})")
                        if query:
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

            elif key == ord('h') or key == ord('H'):
                if os.path.exists("home.html"):
                    with open("home.html", "r", encoding="utf-8") as h_file:
                        home_data = h_file.read()
                    with open("cache.html", "w", encoding="utf-8") as c_file:
                        c_file.write(home_data)
                read("cache.html")
                selected_index = 0
                scroll_y = 0

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
