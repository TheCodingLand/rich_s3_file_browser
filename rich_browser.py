

import os
import logging

from rich.console import RenderableType
from pydantic import BaseModel

from rich.syntax import Syntax, DEFAULT_THEME, SyntaxTheme, Lexer
from rich.traceback import Traceback
from typing import Optional, Union, Tuple, Set
from textual.widgets import DirectoryTree, TreeNode
from textual.widgets._directory_tree import DirEntry

from s3fs import S3FileSystem
from textual.app import App
import json
from rich.text import Text
from textual.widgets import Header, Footer, FileClick, ScrollView
from textual.widget import Widget

class TextWidget(Widget):

    #mouse_over = Reactive(False)
    text : str

    def __init__(self, name: Union[str, None] = None, text: str= "") -> None:
        self.text=text
        super().__init__(name)
    
    def render(self) -> Text:
        return Text(self.text)


with open("s3_config.json", 'r') as f:
    params = json.load(f)


class CustomS3Config(BaseModel):
    aws_secret_access_key: str = "minio_secret_key"
    aws_access_key_id: str = "minio_access_key"
    endpoint_url: str = "http://s3:9000"

    #bucket: str = "default"
    
class CustomS3(S3FileSystem):
    def __init__(self, config: CustomS3Config, *args, **kwargs) -> None:
        self.config = config
        super().__init__(*args, **kwargs, client_kwargs=config.dict())



class S3DirectoryTree(DirectoryTree):
    def __init__(self, path: str, name: str = None, s3: CustomS3 = None) -> None:
        self.s3 = s3
        
        super().__init__(path, name=name)
        
    async def load_directory(self, node: TreeNode[DirEntry]):
        path = node.data.path

        directory = sorted(

            [ x for x in self.s3.ls(path)], key=lambda entry: (not self.s3.isdir(entry), entry)
        )
        for entry in directory:
            await node.add(entry, DirEntry(entry, self.s3.isdir(entry)))
        node.loaded = True
        await node.expand()
        await node.control.focus()
        self.refresh(layout=True)

class CustomSyntax(Syntax):
    @classmethod
    def from_s3_path(
        cls,
        path: str,
        encoding: str = "utf-8",
        lexer: Optional[Union[Lexer, str]] = None,
        theme: Union[str, SyntaxTheme] = DEFAULT_THEME,
        dedent: bool = False,
        line_numbers: bool = False,
        line_range: Optional[Tuple[int, int]] = None,
        start_line: int = 1,
        highlight_lines: Optional[Set[int]] = None,
        code_width: Optional[int] = None,
        tab_size: int = 4,
        word_wrap: bool = False,
        background_color: Optional[str] = None,
        indent_guides: bool = False,
        s3: CustomS3 = None
    ) -> "Syntax":
        """Construct a Syntax object from a file.

        Args:
            path (str): Path to file to highlight.
            encoding (str): Encoding of file.
            lexer (str | Lexer, optional): Lexer to use. If None, lexer will be auto-detected from path/file content.
            theme (str, optional): Color theme, aka Pygments style (see https://pygments.org/docs/styles/#getting-a-list-of-available-styles). Defaults to "emacs".
            dedent (bool, optional): Enable stripping of initial whitespace. Defaults to True.
            line_numbers (bool, optional): Enable rendering of line numbers. Defaults to False.
            start_line (int, optional): Starting number for line numbers. Defaults to 1.
            line_range (Tuple[int, int], optional): If given should be a tuple of the start and end line to render.
            highlight_lines (Set[int]): A set of line numbers to highlight.
            code_width: Width of code to render (not including line numbers), or ``None`` to use all available width.
            tab_size (int, optional): Size of tabs. Defaults to 4.
            word_wrap (bool, optional): Enable word wrapping of code.
            background_color (str, optional): Optional background color, or None to use theme color. Defaults to None.
            indent_guides (bool, optional): Show indent guides. Defaults to False.

        Returns:
            [Syntax]: A Syntax object that may be printed to the console
        """
        code = s3.cat_file(path).decode("utf-8")
        

        if not lexer:
            lexer = cls.guess_lexer(path, code=code)

        return cls(
            code,
            lexer,
            theme=theme,
            dedent=dedent,
            line_numbers=line_numbers,
            line_range=line_range,
            start_line=start_line,
            highlight_lines=highlight_lines,
            code_width=code_width,
            tab_size=tab_size,
            word_wrap=word_wrap,
            background_color=background_color,
            indent_guides=indent_guides,
        )

class MyApp(App):
    """An example of a very simple Textual App"""

    async def on_load(self) -> None:
        self.logger = logging.getLogger()
        """Sent before going in to application mode."""

        # Bind our basic keys
        await self.bind("b", "view.toggle('sidebar')", "Toggle sidebar")
        #await self.bind("r", "refresh", "Refresh")
        await self.bind("t", "switch_transfer_mode", "Download/Edit Mode")
        await self.bind("up", "", "up")
        await self.bind("down", "", "down")
        await self.bind("enter", "", "open node")
        await self.bind("q", "quit", "Quit")
        
        
        self.s3_instance = CustomS3(config = CustomS3Config(**params))
        
        # Get path to show
        self.transfer_mode: bool = False
        self.current_path = ""
        self.path = ""
        self.local_path= os.getcwd()
    #async def refresh(self) -> None:
    async def action_switch_transfer_mode(self):
        self.transfer_mode = not self.transfer_mode
        self.app.sub_title = f"{'Transfer Mode' if self.transfer_mode else f'{os.path.basename(self.current_path)} - Edit Mode'}"
        if self.transfer_mode:
            syntax = TextWidget("Transfer Mode")
            
            await self.body.update(syntax)
    #    self.directory =  S3DirectoryTree(self.path, "Code", self.s3_instance)

    async def on_mount(self) -> None:
        """Call after terminal goes in to application mode"""

        # Create our widgets
        # In this a scroll view for the code and a directory tree
        self.body = ScrollView()
        self.directory = S3DirectoryTree(self.path, "Remote", self.s3_instance)
        self.local_directory = DirectoryTree(self.local_path, "Local")

        # Dock our widgets
        await self.view.dock(Header(), edge="top")
        await self.view.dock(Footer(), edge="bottom")

        # Note the directory is also in a scroll view
        
        #await self.view.dock(TextWidget(name="S3Addr", text="self.s3"), edge="left", size=48, name="sidebar_header")

        await self.view.dock(
            
            ScrollView(self.local_directory),ScrollView(self.directory), edge="left", size=48, name="sidebar")
        await self.view.dock(self.body, edge="top")

    #async def handle_dir_click(self, message: DirClick) -> None:
        #self.directory.refresh()
        #pass


    async def handle_file_click(self, message: FileClick) -> None:
        """A message sent by the directory tree when a file is clicked."""

        syntax: RenderableType
        self.log(message)
        
        try:
            if self.transfer_mode:
                syntax = TextWidget("Transfer Mode")

            elif isinstance(message.sender, S3DirectoryTree ):

            # Construct a Syntax object for the path in the message
                syntax = CustomSyntax.from_s3_path(
                    message.path,
                    line_numbers=False,
                    word_wrap=True,
                    indent_guides=True,
                    theme="monokai",
                    s3=self.s3_instance,
                    #code_width=80
                )
            else:
                syntax = CustomSyntax.from_path(message.path,
                    line_numbers=False,
                    word_wrap=True,
                    indent_guides=True,
                    theme="monokai")
        except Exception:
            # Possibly a binary file
            # For demonstration purposes we will show the traceback
            syntax = Traceback(theme="monokai", width=None, show_locals=True)
            
        
        self.current_path = message.path
        self.app.sub_title = f"{'Transfer Mode' if self.transfer_mode else f'{os.path.basename(self.current_path)} - Edit Mode'}"
        
            
        await self.body.update(syntax)


# Run our app class
MyApp.run(title="Rich S3 Browser Viewer", log="custom_s3_browser.log")
