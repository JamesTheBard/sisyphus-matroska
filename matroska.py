import json
import platform
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List, Optional, Union

import jsonschema
from box import Box

if platform.system() == "Windows":
    MKVMERGE_PATH = shutil.which('mkvmerge.exe')
else:
    MKVMERGE_PATH = shutil.which('mkvmerge')


class MkvSourceTrack:
    """An object to associate tracks with MkvSources.

    Attributes:
        options (dict): All of the key, value pairs for setting options.
        track (int): The track/stream associated with the options set.
    """

    options: dict
    track: int
    track_type: str
    info: dict

    def __init__(self, track: int, options: Optional[dict]) -> None:
        """Create an instance of the MkvSourceTrack.

        Args:
            track (int): The track/stream to use.
            options (dict, optional): The options to use for the track. Defaults to None.
        """
        self.track = track
        self.options = options if options else dict()

    def set_option(self, option: str, value: str = None) -> None:
        """Set an option for a given track.

        Args:
            option (str): The option to set.
            value (str, optional): The value of that option. Defaults to None.
        """
        self.options[option] = value

    def get_option(self, option: str) -> Optional[str]:
        """Get the value of an option associated with the stream/track.

        Args:
            option (str): The option to set.

        Returns:
            Optional[str]: The value of that option, or None if the option is not set.

        Raises:
            KeyError: Raised if the `option` specified is not defined in the track/stream.
        """
        return self.options[option]


class MkvSource:
    """
    A Matroska source object.
    """

    source_file: Path
    info: Box
    __tracks: List[MkvSourceTrack]

    def __init__(self, source_file: Union[str, Path]) -> None:
        """
        Create a Matroska source object.
        :param source_file: The file to use as a source
        """
        self.source_file = Path(source_file)
        self.__tracks = list()
        self.get_info()

    def add_track(self, track: MkvSourceTrack) -> None:
        """
        Add an MkvSourceTrack to the source
        :param track: The MkvSourceTrack to add
        """
        self.__tracks.append(track)

    def remove_track(self, track: MkvSourceTrack) -> None:
        """
        Delete an MkvSourceTrack from the source
        :param track: The MkvSourceTrack to delete
        """
        try:
            self.__tracks.remove(track)
        except ValueError:
            pass

    def get_info(self) -> None:
        """Get the 'identify' information for the track.

        Returns:
            dict: The information from 'mkvmerge --identify' for the track.
        """
        command = [MKVMERGE_PATH, '-i', str(self.source_file), '-F', 'json']
        output = subprocess.run(command, capture_output=True)
        self.info = Box(json.loads(output.stdout))

    @property
    def tracks(self) -> List[MkvSourceTrack]:
        """
        Returns a list of all the associated MkvSourceTracks
        :return: List of all associated MkvSourceTracks
        """
        return self.__tracks

    def generate_options(self) -> list:
        """
        Generate all options associated with this source and tracks
        :return: List of all options for the source/tracks
        """
        track_count = {
            "video": list(),
            "audio": list(),
            "subtitles": list(),
            "buttons": list(),
        }
        command = list()
        for track in self.__tracks:
            track_type = self.info.tracks[track.track].type
            track_count[track_type].append(track.track)
            for k, v in track.options.items():
                if v is not None:
                    command.extend([f"--{k}", f"{track.track}:{v}"])
                else:
                    command.extend([f"--{k}"])
        command.extend(("(", f"{self.source_file.absolute()}", ")"))

        pc = list()
        for k, v in track_count.items():
            if not v:
                pc.append(f'--no-{k}')
            else:
                if k in ["subtitles", "buttons"]:
                    k = k[:-1]
                pc.append(f'--{k}-tracks')
                pc.append(','.join([str(i) for i in v]))

        return pc + command


class MkvAttachment:
    """
    A Matroska attachment object.  Very useful for adding things like fonts for subtitle sources/tracks.
    """

    filename: Path
    mime_type: str
    name: str

    def __init__(self, name: str, mime_type: str, filename: Union[str, Path]) -> None:
        """
        Create a subtitle attachment
        :param name: The filename to attach as
        :param mime_type: The MIME type of the fime
        :param filename: The actual file to attach from the local filesystem
        """
        self.name = name
        self.mime_type = mime_type
        self.filename = Path(filename)

    def generate_options(self) -> list:
        """
        Generate all options associated with the attachment.
        :return: List of attachment options passed to mkvmerge
        """
        return [
            "--attachment-name",
            self.name,
            "--attachment-mime-type",
            self.mime_type,
            "--attach-file",
            str(self.filename.absolute()),
        ]


class Matroska:
    """
    A class that contains all the sources, attachments, and options required to create an
    actual useful set of configuration options.  It will also mux everything together.
    """

    attachments: List[MkvAttachment]
    global_options: dict
    mkvmerge_path: Path
    output: Path
    sources: List[MkvSource]
    track_order_override: list
    schema_file: Path

    def __init__(self) -> None:
        """
        Create a Matroska muxing object
        :param output: The output file to mux everything into.
        """
        self.sources = list()
        self.attachments = list()
        self.track_order_override = list()
        self.output = None
        self.mkvmerge_path = MKVMERGE_PATH
        self.global_options = dict()
        self.schema_file = Path("schema/matroska.schema.json")

    def load_from_file(self, json_file: Union[Path, str]):
        """Load all of the relevant Matroska information from a JSON file.

        Args:
            json_file (Union[Path, str]): The JSON file to load.
        """
        json_file = Path(json_file)
        with json_file.open('r') as f:
            data = json.load(f)

        self.load_from_object(data)

    def load_from_object(self, json_data: Union[Box, dict]):
        """Load all of the relevant Matroska information from a dict.

        Args:
            json_data (Union[Box, dict]): The data to load.
        """
        with self.schema_file.open('r') as f:
            schema = json.load(f)

        try:
            jsonschema.validate(json_data, schema)
        except jsonschema.ValidationError as e:
            print(f"Data failed schema validation: {e.message}")
            sys.exit(100)

        json_data = Box(json_data)
        self.sources = [MkvSource(source) for source in json_data.sources]
        for track in json_data.tracks:
            source_track = MkvSourceTrack(track.track, track.options)
            self.sources[track.source].add_track(source_track)
        self.output = Path(json_data.output_file)
        self.global_options = getattr(json_data, "options", dict())
        self.attachments = [MkvAttachment(
            **i) for i in getattr(json_data, "attachments", list())]
        self.track_order_override = [f'{i.source}:{i.track}' for i in json_data.tracks]

    def add_source(self, source: MkvSource) -> None:
        """
        Add an MkvSource to mux into the Matroska file
        :param source: An MkvSource object
        """
        self.sources.append(source)

    def add_attachment(self, attachment: MkvAttachment) -> None:
        """
        Add an MkvAttachment to mux into the Matroska file
        :param attachment: An MkvAttachment object
        """
        self.attachments.append(attachment)

    @property
    def track_order(self) -> list:
        """
        The track order that will be used when muxing.  Automatically generated unless the
        track_order_override parameter is used
        :return: The track order
        """
        if self.track_order_override:
            return self.track_order_override
        temp = list()
        for i in range(0, len(self.sources)):
            for j in self.sources[i].tracks:
                temp.append(f"{i}:{j.track}")
        return temp

    def generate_command(self, as_string=False) -> list:
        """
        Generate a list of options to feed the 'mkvmerge' binary.
        :return: A list of 'mkvmerge' options
        """
        full_command = [str(self.mkvmerge_path)]
        full_command.extend(["--output", f"{self.output.absolute()}"])
        for k, v in self.global_options.items():
            if not v:
                full_command.append(f"--{k}")
            else:
                full_command.extend([f"--{k}", f"{v}"])
        for source in self.sources:
            full_command.extend(source.generate_options())
        for attachment in self.attachments:
            full_command.extend(attachment.generate_options())
        full_command.extend(["--track-order", ",".join(self.track_order)])

        if as_string:
            return shlex.join(full_command)
        return full_command

    def mux(
        self,
        filename: Union[str, Path] = None,
        delete_temp: bool = False,
        verbose: bool = False,
    ) -> int:
        """
        Mux all of the included sources, attachemts, and options.
        :param filename: The filename to store the 'mkvmerge' options as JSON
        :param delete_temp: Delete the JSON file after muxing is finished
        """
        # command = self.generate_command()
        # results = subprocess.run(command)
        # return results.returncode
        if not filename:
            output_file = NamedTemporaryFile(mode="w", delete=False)
        else:
            output_file = Path("output.json").open("w")
        command = f'"{self.mkvmerge_path}" "@{output_file.name}"'
        if verbose:
            print(command)
            print(f"Creating temp file: {output_file.name}")
        with output_file as f:
            json.dump(self.generate_command()[1:], f)
        if verbose:
            results = subprocess.run(shlex.split(command))
        else:
            results = subprocess.run(
                shlex.split(command),
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
        if delete_temp:
            Path(output_file.name).unlink()
        return results.returncode
