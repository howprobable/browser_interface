from __future__ import annotations

from typing import Any, Union
from dataclasses import dataclass
from py_helpers import Point, Rectangle
from pychrome import Tab, RuntimeException

import requests
import traceback
import os
import time
import pyautogui
import subprocess
import psutil
import shutil
import json
import pychrome
import uuid


import logging
logging.getLogger('pychrome').setLevel(logging.CRITICAL)

class LangNotFound(Exception): pass

def start_chrome_if_not_running(verbose: bool = False, path: str = None, lang: str = "de"):
    langs = ["de", "en_US"]
    if lang not in langs: raise LangNotFound(lang)

    chrome_running = any("chrome.exe" in p.name() for p in psutil.process_iter())
    chrome_path = path or "C:\\Program Files\\Google\\Chrome\\Application\\chrome.exe"
    uid = str(uuid.uuid4())

    if not chrome_running: 
        for folder in os.listdir("C:\\auto_chrome"):
            if folder not in ["tmp_"+l for l in langs]: 
                shutil.rmtree(os.path.join("C:\\auto_chrome", folder))

    shutil.copytree("C:\\auto_chrome\\tmp_"+lang, "C:\\auto_chrome\\tmp_"+uid)
    params = ["--remote-debugging-port=9222", "--user-data-dir=C:\\auto_chrome\\tmp_"+uid, "--remote-allow-origins=*", "--lang="+lang, "--accept-lang="+lang, "--disable-notifications", "--disable-infobars", "--no-default-browser-check"]
    
    if not chrome_running: 
        if verbose: print("Starting Chrome....")
        subprocess.Popen([chrome_path]+params, close_fds=True)
        if verbose: print("Started Chrome.... waiting...")
        time.sleep(4)
        if verbose: print("Starting Chrome.... done")

@dataclass
class uiElement:
    def __str__(self): 
        t = self.text.replace("\n", "\\n")
        if self.typeable: 
            return f"<textfeld<(id:{self.id},x:{int(self.pos.get_middle().x)},y:{int(self.pos.get_middle().y)}): {t}>>"
        elif self.clickable: 
            return f"[[(id:{self.id},x:{int(self.pos.get_middle().x)},y:{int(self.pos.get_middle().y)}): {t}]]"
        else: 
            return f"(x:{int(self.pos.get_middle().x)},y:{int(self.pos.get_middle().y)}): {t}"

    def __repr__(self):
        return self.__str__()

    def isDisplayed(self): return not (self.pos.anchor.x == 0 and self.pos.anchor.y == 0 and self.pos.height == 0 and self.pos.width == 0)

    def __eq__(self, other : uiElement): 
        if self.text in other.text or other.text in self.text: 
            if not self.isDisplayed() or not other.isDisplayed(): return True
            if self.pos.hasCrossSection(other=other.pos): return True

        return False
    
    def __lt__(self, other: uiElement): 
        if self.pos.get_middle().y < other.pos.get_middle().y: return True
        elif self.pos.get_middle().y == other.pos.get_middle().y: 
            if self.pos.get_middle().x < other.pos.get_middle().x: return True  
        else: return False

    def copy(self,) -> uiElement: 
        return uiElement(clickable=self.clickable, typeable=self.typeable, id=self.id, id_nr=self.id_nr, text=self.text, type=self.type, pos=self.pos)


class TabNotFound(Exception):
    pass


class WindowNotFound(Exception):
    pass

class ClickableBufferEmtpy(Exception):
    pass

class TypeableBufferEmpty(Exception):
    pass

class ClickableNotFound(Exception):
    def __init__(self, id: str): 
        self.message = f"Could not find clickable with id: {id}"
        super().__init__(self.message)

class TypeableNotFound(Exception):
    def __init__(self, id: str): 
        self.message = f"Could not find Typeable with id: {id}"
        super().__init__(self.message)


class FailedJSQuery(Exception):
    def __init__(self, message=""):
        super().__init__(message)

class TooManyGoogleChromes(Exception): pass

class TooLessGoogleChromes(Exception): pass

class browserIF:
    
    ### Configs
    tab_waiter = 1

    ### Handler
    def __init__(
        self,
        debugging_url: str = "http://localhost:9222",
        start_and_close: bool = True,
        verbose: bool = False,
    ):
        self.clean: bool = False
        self.verbose: bool = verbose

        if start_and_close: 
            if verbose: print("[Browser] Starting Chrome....")
            start_chrome_if_not_running()

        self.start_and_close : bool = start_and_close
        self.browser = pychrome.Browser(url=debugging_url)
        self.tab: Tab = None
        
        if start_and_close: 
            self.hijack_tab()

        self.clickable_buffer : list[uiElement] = None
        self.typeable_buffer : list[uiElement] = None

        self.typeable_query_file: str = os.path.join(os.path.dirname(__file__), 'js', 'typeable_elements.js')
        self.clickable_query_file: str = os.path.join(os.path.dirname(__file__), 'js', 'clickable_elements.js')
        self.text_query_file: str = os.path.join(os.path.dirname(__file__), 'js', 'text_elements.js')
        

    def __del__(self):
        if self.verbose: print(f"[Browser] Destructor called....(clean: {self.clean})")
        if not self.clean: 
            self.clean_up()

    ### Public
    def clean_up(self): 
        if self.verbose: print(f"[Browser] Cleaning up...")
        if not self.clean:
            if self.start_and_close: self.close_browser()
            self.clean = True
        else: 
            if self.verbose: print("[Browser] Already cleaned up....")

    def hijack_tab(self, url: str = None, nr: int = 0) -> None:
        tabs = self.browser.list_tab()
        if len(tabs) == 0: raise TabNotFound() 

        if not url:
            self.tab = tabs[nr]
            if self.verbose: print(f"[Browser] Hijacked tab by NR: {self.tab}")
            return

        for tab in tabs:
            if url.lower() in self._get_url_of_tab(tab=tab):
                self.tab = tab
                if self.verbose: print(f"[Browser] Hijacked tab by URL: {self.tab}")
                return

        raise TabNotFound()

    def get_tabs(self) -> list[str]:
        tabs = self.browser.list_tab()
        return [self._get_url_of_tab(tab=t) for t in tabs]

    def open_tab(self, url: str) -> None:
        if self.verbose: print(f"[Browser] Opening tab: {url}")
        if not (url.startswith("https://") or url.startswith("http://")): url = f"https://{url}" 
        self.tab = self.browser.new_tab()
        self.tab.start() 
        self.tab.wait(timeout=browserIF.tab_waiter)
        self.tab.Page.navigate(url=url)
        self.tab.wait(timeout=browserIF.tab_waiter)

    def close_browser(self) -> None:
        if self.verbose: print("[Browser] Closing Chrome....")
        chrome_windows = pyautogui.getWindowsWithTitle("- Google Chrome")
        if len(chrome_windows) == 0: 
            if self.verbose: print("[Browser] Chrome already closed")
            return 
        
        if len(chrome_windows) > 1: raise TooManyGoogleChromes() 

        self.close_tab()
        time.sleep(.5) 

        browser_window = pyautogui.getWindowsWithTitle("- Google Chrome")[0] 
        browser_window.close()

        self.clean = True

    def close_tab(self) -> None:
        if self.verbose: print(f"[Browser] Closing tab.... {self.tab}")

        if not self.tab:
            if self.verbose: print("[Browser] Tab already closed")
            return
        
        if self.tab.status == Tab.status_started: self.tab.stop() 

        try: 
            self.tab.wait(timeout=browserIF.tab_waiter)
        except RuntimeException as _: 
            if self.verbose: print(f"[Browser] RuntimeException: Tab already stopped....")

        if self.verbose: print(f"[Browser] Tab stopped.... {self.tab}, closing tab....")
        self.browser.close_tab(self.tab)
        if self.verbose: print(f"[Browser] Browser closed tab.... {self.tab}, hijacking other tab....")
        
        try: 
            self.hijack_tab()
        except requests.exceptions.ConnectionError as _:
            if self.verbose: print(f"[Browser] ConnectionError: No more tabs to hijack....")

    def get_viewport_content(self, withMetaInfo: bool = True) -> str: 
        elem_list : list[uiElement] = self._combine_all_elements(clickables=self._get_clickables(), texts=self._get_text_elements(), typeables=self._get_typeables())
    
        #filter nach viewport
        viewport: Rectangle = self.get_viewport_on_screen() 
        filtered_list = [elem for elem in elem_list if elem.pos.bottom_left.y > 0 and elem.pos.top_right.y < viewport.height]

        str_elem_list = self.stringify_element_list(elementList=filtered_list)
        #add url und scrollLevel
        ret = f"CONTENT:\n\n {str_elem_list}"
        
        if withMetaInfo: ret = f"URL: {self.get_url()}, SCROLLED: {self.get_scroll_px()}px\n\n" + ret 

        return ret

    def set_window(self, window: Rectangle) -> None:
        chrome_windows = pyautogui.getWindowsWithTitle("- Google Chrome")
        if len(chrome_windows) == 0: raise TooLessGoogleChromes() 
        if len(chrome_windows) > 1: raise TooManyGoogleChromes() 
        
        pyautogui.getWindowsWithTitle("- Google Chrome")[0].resizeTo(window.width, window.height)
        pyautogui.getWindowsWithTitle("- Google Chrome")[0].moveTo(window.top_left.x, window.top_left.y)

    def get_window(self) -> Rectangle:
        chrome_windows = pyautogui.getWindowsWithTitle("- Google Chrome")
        if len(chrome_windows) == 0: raise TooLessGoogleChromes() 
        if len(chrome_windows) > 1: raise TooManyGoogleChromes() 

        window = pyautogui.getWindowsWithTitle("- Google Chrome")[0]

        if not window:
            raise WindowNotFound()

        return Rectangle.from_anchor(
            anchor=Point(window.top, window.left),
            height=window.height,
            width=window.width,
        )

    def get_viewport_on_screen(self) -> Rectangle:
        window = self.get_window()
        viewport = self.get_inner_window()

        ##assume left and bottom of viewport are browser edges
        browser_bar_height = window.height - viewport.height
        return Rectangle.from_anchor(
            anchor=Point(window.top_left.x, window.top_left.y + browser_bar_height),
            height=viewport.height,
            width=viewport.width,
        )

    def get_inner_window(self) -> Rectangle:
        ret = self._exec(cmd="[window.innerHeight, window.innerWidth, window.pageXOffset, window.pageYOffset]")
        return Rectangle.from_anchor(anchor=Point(x=ret[2], y=ret[3]), height=ret[0], width=ret[1])

    def scroll_to(self, pos: Point = None, element: uiElement = None, by: Point = None):
        if pos: 
            _ = self._exec(noReturn=True, cmd=f"window.scrollTo({pos.x}, {pos.y})")
        if element: 
            _ = self._exec(noReturn=True, cmd=f"document.getElementById('{element.id}').scrollIntoView({{ behavior: 'smooth' }})")
        if by: 
            _ = self._exec(noReturn=True, cmd=f"window.scrollBy(0, {by})")

    def click(self, element: uiElement) -> None:
        _ = self._exec(noReturn=True, cmd=f"""(() => {{
                                                document.querySelectorAll('#' + CSS.escape('{element.id}'))[{element.id_nr}].click();
                                            }})()
                                            """)
        self.clickable_buffer = None
        self.typeable_buffer = None
        self.tab.wait(timeout=browserIF.tab_waiter)

    def type(self, element: uiElement, text: str) -> None: 
        _ = self._exec(noReturn=True, cmd=f"""(() => {{ 
                       const element = document.querySelectorAll('#' + CSS.escape('{element.id}'))[{element.id_nr}]; 
                       let text = '{text}'; 
                       for (let i = 0; i < text.length; i++) 
                        {{ 
                            setTimeout(() => {{ element.value += text[i]; }}, i * 100); 
                        }}
                        }})()""")
        time.sleep(len(text) * 0.1)

    def typeById(self, id: str, text: str) -> None: 
        if not self.typeable_buffer: raise TypeableBufferEmpty() 

        elem = next((elem for elem in self.typeable_buffer if elem.id == id), None)
        if not elem: raise TypeableNotFound(id) 

        return self.type(element=elem, text=text)

    def clickById(self, id: str) -> None: 
        if not self.clickable_buffer: raise ClickableBufferEmtpy() 

        elem = next((elem for elem in self.clickable_buffer if elem.id == id), None)
        if not elem: raise ClickableNotFound(id) 

        return self.click(element=elem)

    def hover(self, element: uiElement) -> None: 
        _ = self._exec(noReturn=False, cmd=f"document.getElementById('{element.id}').dispatchEvent(new MouseEvent('mouseover', {{bubbles: true}}))")

    def hoverById(self, id: str) -> None: 
        if not self.clickable_buffer: raise ClickableBufferEmtpy() 

        elem = next((elem for elem in self.clickable_buffer if elem.id == id), None)
        if not elem: raise ClickableNotFound(id) 

        return self.hover(element=elem)

    def back(self ) -> None: 
        _ = self._exec(noReturn=True, cmd=f"window.history.back()") 
        self.tab.wait(timeout=browserIF.tab_waiter)

    def get_url(self) -> str:
        return self._get_url_of_tab(tab=self.tab)
    
    def get_scroll_px(self, x_axis: bool = False) -> str: 
        return self._exec(cmd=f"window.{'scrollY' if not x_axis else 'scrollX'}", tab=self.tab)

    def get_scroll(self) -> Point: 
        return Point(self.get_scroll_px(x_axis=True), self.get_scroll_px())

    def manual_mode(self) -> None: 
        print("Tabs: ", self.get_tabs())
        inp = input("Which tab shall I controll (None for [0]): ")
        print("hijacking tab....")
        if inp == "": self.hijack_tab() 
        else: self.hijack_tab(url=inp) 
        print("-------------------------------------")

        while True: 
            try: 
                if inp != "help": 
                    print(self.get_viewport_content())

                print("-------------------------------------")
                inp = input(">>")
                print("-------------------------------------")
                if inp == "help": 
                    #help
                    print("Usage: ")
                    print("[c]: click <id>")
                    print("[t]: type <id> <string_to_type>")
                    print("[h]: hover <id>")
                    print("[o]: open <url>")
                    print("[s]: scrollBy <px>")
                    print("[b]: back")
                    continue
                if inp.startswith("c"): 
                    id = inp.split()[1]
                    self.clickById(id=id)
                    continue
                if inp.startswith("t"): 
                    id = inp.split()[1]
                    string = inp.split()[2]
                    self.typeById(text=string,id=id)
                    continue
                if inp.startswith("h"): 
                    id = inp.split()[1]
                    self.hoverById(id=id) #TODO
                    continue
                if inp.startswith("o"): 
                    url = inp.split()[1]
                    self.open_tab(url=url)
                    continue
                if inp == "b": 
                    self.back()
                    continue 
                if inp.startswith("s"): 
                    px = int(inp.split()[1])
                    self.scroll_to(by=px)
                    continue

                print("Dont know what you mean...")

            except Exception as e: 
                print("Error: ")
                traceback.print_exc()
            except KeyboardInterrupt: 
                print("Shutting down... see you...")
                return


    ### private

    def _get_url_of_tab(self, tab: Tab) -> str:
        return self._exec(cmd="document.location.href", tab=tab)

    def _exec(self, cmd: str, tab: Tab = None, noReturn: bool = False) -> Any:
        print(f"[Browser] self.tab: {self.tab}, tab: {tab}")

        if not tab:
            if not self.tab:
                raise TabNotFound() 
            tab = self.tab

        if tab.status != tab.status_started: 
            tab.start()
            tab.wait(timeout=browserIF.tab_waiter)

        ret = ""
        try:
            # print("Exec: ", f"JSON.stringify({cmd})")
            ret = tab.Runtime.evaluate(expression=f"JSON.stringify({cmd})")
            if not noReturn:
                ret = ret["result"]["value"]
                return json.loads(ret)
            else: 
                if ret["result"]["type"] == "undefined": return
                else: raise FailedJSQuery(message="Return is defined: "+str(ret["result"]["description"]))
        
        except FailedJSQuery as e: raise e
        except:
            traceback.print_exc()
            raise FailedJSQuery(message=ret)
        
    def _get_typeables(self) -> list[uiElement]: 
        element_jsons = self._exec(cmd=self.get_file_contents_as_string(file_path=self.typeable_query_file))
        
        ret : list[uiElement] = []
        for elem in element_jsons: 
            r = elem["rect"]
            rect = None
            if len(r) == 4: 
                rect = Rectangle.from_anchor(anchor=Point(x=r[0], y=r[1]), height=r[2], width=r[3]) 
            text = (elem["placeholder"] or elem["title"] or elem["ariaLabel"] or "") + ":" + elem["text"]            
            ret.append(uiElement(typeable=True, id=elem["id"], id_nr=elem["id_nr"], text=text, type=elem["tag"], pos=rect))

        # ret = self._filter_duplicates(elements=self._filter_invisible(elements=ret))  
        
        self.typeable_buffer = [r.copy() for r in ret]
        return ret


    def _get_clickables(self ) -> list[uiElement]: 
        element_jsons = self._exec(cmd=self.get_file_contents_as_string(file_path=self.clickable_query_file))
        
        ret : list[uiElement] = []
        for elem in element_jsons: 
            r = elem["rect"]
            rect = None
            if len(r) == 4: 
                rect = Rectangle.from_anchor(anchor=Point(x=r[0], y=r[1]), height=r[2], width=r[3]) 
            text = self.get_text_of_elem(elem)            
            ret.append(uiElement(clickable=True, id=elem["id"], id_nr=elem["id_nr"], text=text, type=elem["tag"], pos=rect))

        ret = self._filter_duplicates(elements=self._filter_invisible(elements=ret))  
        
        self.clickable_buffer = [r.copy() for r in ret]
        return ret 
    
    def get_text_of_elem(self, json_data):
        text = json_data.get("text", "").strip()
        title = json_data.get("title", "").strip()
        ariaLabel = json_data.get("ariaLabel", "").strip()

        elements = [title, ariaLabel]
        non_empty_elements = [e for e in elements if e]

        if text:
            if non_empty_elements:
                return f"{text}({', '.join(non_empty_elements)})"
            return text
        elif non_empty_elements:
            if len(non_empty_elements) == 2:
                return f"{non_empty_elements[0]}({non_empty_elements[1]})"
            return non_empty_elements[0]
        return ""  # or "" if you prefer to return an empty string

    def _filter_duplicates(self, elements: list[uiElement]) -> list[uiElement]: 
        ret : list[uiElement] = []

        for element in elements:
            found = False
            for i in range(len(ret)):
                if element == ret[i]:
                    if len(element.text) < len(ret[i].text):
                        ret[i] = element  # Replace with the smaller one
                    found = True
                    break
            if not found:
                ret.append(element)
        return ret
    
    def _filter_invisible(self, elements: list[uiElement]) -> list[uiElement]: 
        ret : list[uiElement] = []
        for element in elements: 
            if element.isDisplayed(): ret.append(element)
        return ret
    
    def _get_text_content(self) -> str: 
        return self._exec(cmd="document.body.innerText")
        
    def _get_text_elements(self ) -> list[uiElement]: 
        element_jsons = self._exec(cmd=self.get_file_contents_as_string(file_path=self.text_query_file))
        
        ret : list[uiElement] = []
        for elem in element_jsons: 
            r = elem["rect"]
            rect = None
            if len(r) == 4: 
                rect = Rectangle.from_anchor(anchor=Point(x=r[0], y=r[1]), height=r[2], width=r[3]) 
            text = elem["text"]          
            ret.append(uiElement(id=None, id_nr=None,  text=text, type="TEXT", pos=rect))
            
        return ret    
    
    def stringify_element_list(self, elementList: list[uiElement]) -> str: 
        ret = ""
        for elem in elementList: 
            ret += str(elem) + "\n"
        return ret
    
    def _combine_all_elements(self, clickables: list[uiElement], texts: list[uiElement], typeables: list[uiElement]) -> list[uiElement]:
        ret: list[uiElement] = []

        for text in texts: 
            isBtn = False
            for i in reversed(range(len(clickables))):
                click = clickables[i]
                if text == click: 
                    ret.append(click)
                    del clickables[i]  # Remove in place by index
                    isBtn = True
                    break
            if not isBtn: 
                ret.append(text)

        ret2: list[uiElement] = []
        
        for elem in ret: 
            isInput = False
            for i in reversed(range(len(typeables))):
                typeable = typeables[i]
                if elem == typeable: 
                    ret.append(typeable)
                    del typeables[i]  # Remove in place by index
                    isBtn = True
                    break
            if not isInput: 
                ret2.append(elem)

        # Append remaining clickables that were not processed
        ret2.extend(clickables)
        ret2.extend(typeables)
        ret2.sort() 
        return ret2 
    
    def get_file_contents_as_string(self, file_path: str) -> str:
        with open(file_path, 'r') as file:
            return file.read()
    
        


if __name__ == "__main__":
    start_chrome_if_not_running(lang="en_US")

    # b = browserIF()
    # b.manual_mode()