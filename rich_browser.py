import os
import sys

from rich.console import RenderableType

import logging
from rich.syntax import Syntax, DEFAULT_THEME,SyntaxTheme, Lexer
from rich.traceback import Traceback
from typing import Any, Optional, Union, Tuple, Set
from textual.widgets import DirectoryTree, TreeNode
from textual.widgets._directory_tree import DirEntry
from pydantic import BaseModel
from textual.app import App
import json
from textual.widgets import Header, Footer, FileClick, ScrollView

with open("s3_config.json", 'r') as f:
    params = json.load(f)
from s3fs import S3FileSystem

class CustomS3Config(BaseModel):
    aws_access_key_id : str = "minio_access_key"
    aws_secret_access_key : str = "minio_secret_key"
    endpoint_url: str = "http://localhost:9000"
    #bucket: str = "default"
    use_ssl: bool = False

class CustomS3(S3FileSystem):
    def __init__(self, config: CustomS3Config, *args, **kwargs) -> None:
        super().__init__(*args, **kwargs, client_kwargs=config.dict())




class CnpDirectoryTree(DirectoryTree):
    def __init__(self, path: str, name: str = None, s3: CustomS3 = None) -> None:
        self.s3 = s3
        
        super().__init__(path, name=name)
        
    async def load_directory(self, node: TreeNode[DirEntry]):
        path = node.data.path

        directory = sorted(

            [ self.s3.decompose_path(x) for x in self.s3.ls(path)], key=lambda entry: (not entry.is_dir, entry.full_path)
        )
        for entry in directory:
            await node.add(entry.name, DirEntry(entry.full_path, entry.is_dir))
        node.loaded = True
        await node.expand()
        await node.control.focus()
        self.refresh(layout=True)

class CnpSyntax(Syntax):
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
        code = s3.read_object(path).decode("utf-8")
        logging.error(code)

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
        """Sent before going in to application mode."""

        # Bind our basic keys
        await self.bind("b", "view.toggle('sidebar')", "Toggle sidebar")
        await self.bind("up", "", "up")
        await self.bind("down", "", "down")
        await self.bind("enter", "", "open node")
        await self.bind("q", "quit", "Quit")
        config = CustomS3Config(**params)
        self.s3_instance = CustomS3(config=config)
        # Get path to show
        
        self.path = ""

    async def on_mount(self) -> None:
        """Call after terminal goes in to application mode"""

        # Create our widgets
        # In this a scroll view for the code and a directory tree
        self.body = ScrollView()
        self.directory = CnpDirectoryTree(self.path, "Code", self.s3_instance)

        # Dock our widgets
        await self.view.dock(Header(), edge="top")
        await self.view.dock(Footer(), edge="bottom")

        # Note the directory is also in a scroll view
        await self.view.dock(
            ScrollView(self.directory), edge="left", size=48, name="sidebar"
        )
        await self.view.dock(self.body, edge="top")

    async def handle_file_click(self, message: FileClick) -> None:
        """A message sent by the directory tree when a file is clicked."""

        syntax: RenderableType
        self.log(message)
        try:
            # Construct a Syntax object for the path in the message
            syntax = CnpSyntax.from_s3_path(
                message.path,
                line_numbers=False,
                word_wrap=True,
                indent_guides=True,
                theme="monokai",
                s3=self.s3_instance,
                #code_width=80
            )
        except Exception:
            # Possibly a binary file
            # For demonstration purposes we will show the traceback
            syntax = Traceback(theme="monokai", width=None, show_locals=True)
        self.app.sub_title = os.path.basename(message.path)
        await self.body.update(syntax)


# Run our app class
MyApp.run(title="Cnp S3 Browser Viewer", log="cnp_s3_browser.log")
