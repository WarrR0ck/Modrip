import rich
import keyboard
import os
import zipfile
import json
import requests
import config
import re
import sys

from rich import pretty, print
from rich.columns import Columns
from rich.panel import Panel
from rich.align import Align
from rich.progress import track
from rich.markdown import Markdown

from PyQt5.QtWidgets import QApplication, QFileDialog
from PyQt5.QtGui import QIcon

pretty.install()

filepath = None
filename = None
newfolder = None

mods = []


class Mod:
    """
    #### Example:
        - name = 'fabric-api-0.96.11+1.20.4.jar' <string>
        - id = 'P7dR8mSH' <string>
        - hash = '5537a4592773739e7279f3685445a84af49fde56' <sha512> string
        - client = 'required' <optional | required | unsupported> string
        - server = 'required' <optional | required | unsupported> string
        - download = 'https://cdn.modrinth.com/data/P7dR8mSH/versions/htRy7kbI/fabric-api-0.96.11%2B1.20.4.jar' <string>
    """

    def __init__(
        self,
        name: str = None,
        id: str = None,
        hash: str = None,
        client: str = "unsupported",
        server: str = "unsupported",
        download: str = None,
    ) -> None:
        self.name = name
        self.id = id
        self.hash = hash
        self.client = client
        self.server = server
        self.download = download


def modFromId(id: str) -> Mod | None:
    for mod in mods:
        if mod.id == id:
            return mod


def modFromHash(hash: str) -> Mod | None:
    for mod in mods:
        if mod.hash == hash:
            return mod


def fillTerminal():
    print(Align.center(config.sig, vertical="middle"))

    print(
        Align.center(
            Columns(
                [
                    Panel(
                        f"Author: [cyan]{config.author}[/cyan]\nVersion: [green]{config.version}[/green]",
                        expand=True,
                        title=config.project,
                        padding=(0, 32),
                    )
                ]
            ),
            vertical="middle",
        )
    )

    if isinstance(filepath, str) and filepath != "":
        print(f"Modpack: [green]{filepath}")

    if mods:
        print(f"Mod Count: [green]{len(mods)}")


def clearTerminal():
    os.system("cls" if os.name == "nt" else "clear")

    fillTerminal()


def processMods():

    mod: Mod
    for mod in track(mods, description="Downloading Mods", total=len(mods)):
        response = requests.get(mod.download, stream=True).content

        if mod.server in {"required", "optional"}:
            with open(
                os.path.join(newfolder, filename, "server", mod.name), mode="wb"
            ) as file:
                file.write(response)

        if mod.client in {"required", "optional"}:
            with open(
                os.path.join(newfolder, filename, "client", mod.name), mode="wb"
            ) as file:
                file.write(response)


def processIds():
    global newfolder

    ids = [mod.id for mod in mods]
    params = {"ids": "[{}]".format(",".join(['"{}"'.format(id) for id in ids]))}

    headers = {"Content-Type": "application/json"}

    with requests.get(
        url=f"{config.baseUrl}/v2/projects", params=params, headers=headers
    ) as response:

        data = response.json()

        app = QApplication.instance()

        if app is None:
            app = QApplication([])

        print("Select the [gold3]location[/gold3] for the output folder.")

        folder = QFileDialog().getExistingDirectory(
            None,
            "Select a folder",
        )

        if isinstance(folder, str) and folder != "":
            newfolder = folder
            path = f"{folder}/{filename}"

            os.makedirs(path, exist_ok=True)

            for dir in config.folderTree:
                os.makedirs(f"{path}/{dir}", exist_ok=True)

            for modData in track(data, total=len(data), description="Getting Types"):
                mod = modFromId(modData["id"])
                mod.server = modData["server_side"]
                mod.client = modData["client_side"]

            clearTerminal()

            processMods()


def getIds():

    payload = json.dumps({"hashes": [mod.hash for mod in mods], "algorithm": "sha512"})

    headers = {"Content-Type": "application/json"}

    with requests.post(
        url=f"{config.baseUrl}/v2/version_files", data=payload, headers=headers
    ) as response:

        data = response.json()

        for hash, modData in track(
            data.items(), total=len(data.items()), description="Getting Ids"
        ):
            mod = modFromHash(hash)
            mod.id = modData["project_id"]
            mod.name = modData["files"][0]["filename"]

        clearTerminal()

        processIds()


def getHashes():
    if zipfile.is_zipfile(filepath):
        try:
            with zipfile.ZipFile(filepath, mode="r") as archive:
                with archive.open("modrinth.index.json") as file:
                    data = json.loads(file.read())

                    for mod in track(
                        data["files"],
                        total=len(data["files"]),
                        description="Getting Hashes",
                    ):
                        mods.append(
                            Mod(
                                hash=mod["hashes"]["sha512"],
                                download=mod["downloads"][0],
                            )
                        )

                    clearTerminal()

                    getIds()

        except zipfile.BadZipFile as error:
            print(error)


def startProcess():
    global filepath
    global filename

    clearTerminal()

    app = QApplication.instance()

    if app is None:
        app = QApplication(sys.argv)

    print("Select the [green]Modpack[/green] file to continue.")

    file, _ = QFileDialog().getOpenFileName(
        None, "Select a file", "", "mrpack file (*.mrpack)"
    )

    if isinstance(file, str) and file != "":
        filename = re.search(r"([^\/\\]+?)(?=\.\w+$)", file).group(1)
        filepath = file

        clearTerminal()

        getHashes()


def main():
    fillTerminal()

    print(Align.center(config.prompts[0], vertical="middle"), config.prompts[1])

    keyboard.wait("enter")

    startProcess()


if __name__ == "__main__":
    main()
