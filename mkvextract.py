import json
import os
import platform
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Union

import jsonschema
from box import Box

if platform.system() == "Windows":
    MKVEXTRACT_PATH = shutil.which('mkvextract.exe')
else:
    MKVEXTRACT_PATH = shutil.which('mkvextract')


class Mkvextract:
    def __init__(self):
        self.data = None
        self.mkvextract_path = MKVEXTRACT_PATH
        schema_path = Path(
            os.path.dirname(os.path.abspath(__file__)))
        self.schema_file = schema_path / Path("schema/mkvmerge.schema.json")

    def load_from_file(self, json_file: Union[Path, str]):
        json_file = Path(json_file)
        with json_file.open('r') as f:
            data = json.load(f)

        self.load_from_object(data)

    def load_from_object(self, data: Union[dict, Box]):
        with self.schema_file.open('r') as f:
            schema = json.load(f)

        jsonschema.validate(data, schema)
        self.data = Box(data)

    def generate_command(self, as_string: bool = False) -> Union[str, list]:
        if not self.data:
            return None
        command = list()
        command.append(self.mkvextract_path)
        command.append(self.data.source)
        for mode, v in self.data:
            if mode == "source":
                continue
            if mode in ["tracks", "attachments", "timestamps", "cues"]:
                mode = mode if not "timestamps" else "timestamps_v2"
                command.append(mode)
                for i in v:
                    command.append(f'{v.id}:{v.filename}')
            if mode in ["chapters", "tags"]:
                command.append(mode)
                command.append(v)

        if as_string:
            return shlex.join(command)
        else:
            return command

    def extract(self, verbose: bool = False) -> int:
        if verbose:
            results = subprocess.run(self.generate_command())
        else:
            results = subprocess.run(
                self.generate_command(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return results.returncode
