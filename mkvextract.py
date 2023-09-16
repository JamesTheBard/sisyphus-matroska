import json
import os
import platform
import shlex
import shutil
import subprocess
from pathlib import Path
from typing import Union

import jsonschema
from box import Box, BoxList

from mkvinfo import MkvInfo

if platform.system() == "Windows":
    MKVEXTRACT_PATH = shutil.which('mkvextract.exe')
else:
    MKVEXTRACT_PATH = shutil.which('mkvextract')


class Mkvextract:
    """Extract tracks, attachments, cues, timestamps, chapters, attachments from a
    given source file.

    Attributes:
        data (Box, optional): The data associated with what to extract.
        mkvextract_path (Path): The path to the `mkvextract` binary.
        schema_file (Path): The path to the JSON schema file to validate the data.
        mkvinfo (MkvInfo, optional): The MkvInfo object representing the source file's track information.
    """
    data: Optional[Box]
    mkvextract_path: Path
    schema_file: Path
    mkvinfo: MkvInfo

    def __init__(self):
        self.data = None
        self.mkvextract_path = MKVEXTRACT_PATH
        schema_path = Path(
            os.path.dirname(os.path.abspath(__file__)))
        self.schema_file = schema_path / Path("schema/mkvextract.schema.json")
        self.mkvinfo = None

    def load_from_file(self, json_file: Union[Path, str]):
        """Load `mkvextract` options/data from a JSON file.

        Args:
            json_file (Union[Path, str]): The path to the JSON file.
        """
        json_file = Path(json_file)
        with json_file.open('r') as f:
            data = json.load(f)

        self.load_from_object(data)

    def load_from_object(self, data: Union[dict, Box]):
        """Load `mkvextract` options/data from a Python object.

        Args:
            data (Union[dict, Box]): The object to load the `mkvextract` options from.
        """
        with self.schema_file.open('r') as f:
            schema = json.load(f)

        jsonschema.validate(data, schema)
        self.data = Box(data)
        self.mkvinfo = MkvInfo(source=self.data.source)

    def generate_command(self, as_string: bool = False) -> Union[str, list]:
        """Generate the command line options to run.

        Args:
            as_string (bool, optional): Return the command as a string. Defaults to False.

        Returns:
            Union[str, list]: The command to run.
        """
        if not self.data:
            return None
        command = list()
        command.append(self.mkvextract_path)
        command.append(self.data.source)
        for mode, v in self.data.items():
            if mode == "source":
                continue
            if mode == "tracks":
                command.extend(self.process_track_mode(v))
            if mode in ["attachments", "timestamps", "cues"]:
                mode = mode if mode != "timestamps" else "timestamps_v2"
                command.append(mode)
                for i in v:
                    command.append(f'{i.id}:{i.filename}')
            if mode in ["chapters", "tags"]:
                command.append(mode)
                command.append(v)

        if as_string:
            return shlex.join(command)
        else:
            return command

    def process_track_mode(self, data: list) -> list:
        """Process the track mode information.

        Args:
            data (list): The track mode information from the loaded data.

        Returns:
            list: The command options for all of the associated tracks to extract.
        """
        data = BoxList(data)
        command = ["tracks"]
        for d in data:
            search_tags = {"track_type", "language"}
            tags = set(d.keys())
            if s_tags := tags.intersection(search_tags):
                track = self.mkvinfo.get_tracks(
                    **{i: d[i] for i in s_tags})[d.id]
            else:
                track = self.mkvinfo.tracks[d.id]

            command.append(f"{track.track_id}:{d.filename}")
        return command

    def extract(self, verbose: bool = False) -> int:
        """Run the `mkvextract` command to extract all of the information specified.

        Args:
            verbose (bool, optional): Show command output when run. Defaults to False.

        Returns:
            int: The return code from `mkvextract`.
        """
        if verbose:
            results = subprocess.run(self.generate_command())
        else:
            results = subprocess.run(
                self.generate_command(),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        return results.returncode
