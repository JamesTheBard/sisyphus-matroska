import json
import logging
import mimetypes
import os
import platform
import shlex
import shutil
import subprocess
import sys
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import List, Optional, Union, Iterable

import box
import jsonschema
from box import Box, BoxList

if platform.system() == "Windows":
    MKVMERGE_PATH = shutil.which('mkvmerge.exe')
else:
    MKVMERGE_PATH = shutil.which('mkvmerge')
logging.debug(
    f"Found 'mkvmerge' binary ({platform.system()}): {MKVMERGE_PATH}")


class MkvSourceTrack:
    """An object to associate tracks with MkvSources.

    Attributes:
        options (dict): All of the key, value pairs for setting options.
        track (int): The track/stream associated with the options set.
    """

    options: dict
    track: int

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
    """The MkvSource object that holds source and track information.

    Attributes:
        source_file (Path): The source file to mux from.
        info (Box): `mkvmerge -i` information associated with the source and associated tracks.
        verify_files (bool): Whether to verify that the source files exist.
    """
    source_file: Path
    info: Box
    __tracks: List[MkvSourceTrack]
    options: Box

    def __init__(self, filename: Union[str, Path], options: Optional[Box] = None, verify_files: bool = False) -> None:
        """Create a Matroska source object.

        Args:
            source_file (Union[str, Path]): The source filename to mux from.
            verify_files (bool): Verify that the source file exists. Defaults to False.
        """
        self.source_file = Path(filename)
        self.options = options if options else Box()
        if not self.source_file.exists() and verify_files:
            logging.fatal(f"Source does not exist: '{self.source_file}'!")
            sys.exit(10)
        else:
            logging.debug(f"Found source: '{self.source_file}'.")
        self.__tracks = list()
        self.get_info()

    def add_track(self, track: MkvSourceTrack) -> None:
        """Add an MkvSourceTrack to the source

        Args:
            track (MkvSourceTrack): The MkvSourceTrack to add
        """
        self.__tracks.append(track)

    def remove_track(self, track: MkvSourceTrack) -> None:
        """Delete an MkvSourceTrack from the source

        Args:
            track (MkvSourceTrack): The MkvSourceTrack to delete
        """
        try:
            self.__tracks.remove(track)
        except ValueError:
            pass

    def get_info(self) -> None:
        """Get the 'identify' information for the track.
        """
        command = [MKVMERGE_PATH, '-i', str(self.source_file), '-F', 'json']
        output = subprocess.run(command, capture_output=True)
        self.info = Box(json.loads(output.stdout))

    @property
    def tracks(self) -> List[MkvSourceTrack]:
        """Returns a list of all the associated MkvSourceTracks

        Returns:
            List[MkvSourceTrack]: The MkvSourceTracks associated with the source.
        """
        return self.__tracks

    def generate_options(self) -> list:
        """
        Generate all options associated with this source and tracks

        Returns:
            list: List of all options for the source/tracks.
        """
        track_count = {
            "video": list(),
            "audio": list(),
            "subtitles": list(),
            "buttons": list(),
        }
        command = list()
        for track in self.__tracks:
            try:
                track_type = self.info.tracks[track.track].type
            except box.BoxKeyError as e:
                logging.fatal(
                    f"Source '{self.source_file}' does not contain track number {track.track}!")
                sys.exit(60)

            track_count[track_type].append(track.track)
            for k, v in track.options.items():
                if v is not None:
                    command.extend([f"--{k}", f"{track.track}:{v}"])
                else:
                    command.extend([f"--{k}"])
        command.extend(("(", f"{self.source_file.absolute()}", ")"))

        pc = list()
        for k, v in track_count.items():
            if f"_copy-{k}-tracks" in self.options.keys():
                continue
            if not v:
                pc.append(f'--no-{k}')
            else:
                if k in ["subtitles", "buttons"]:
                    k = k[:-1]
                pc.append(f'--{k}-tracks')
                pc.append(','.join([str(i) for i in v]))

        for k, v in self.options.items():
            if k[0] == "_":
                continue
            if v == None or type(v) is bool:
                pc.append(f'--{k}')
            else:
                pc.extend((f'--{k}', v))

        return pc + command


class MkvAttachment:
    """A Matroska attachment object.  Very useful for adding things like fonts for subtitle sources/tracks.

    Attributes:
        filename (Path): The file to attach.
        mimetype (str): The MIME-type associated with the file.
        mimetypes (BoxList): A list of all MIME-type to file extension associations.
        name (str): The name of the attachment.
    """

    filename: Path
    mimetype: str
    name: str

    def __init__(self, filename: Union[str, Path], name: Optional[str] = None, mimetype: Optional[str] = None, verify_files: bool = False) -> None:
        """Create an attachment for the Matroska file.

        Args:
            name (str, optional): The name of the attachment. Defaults to None.
            mimetype (str, optional): The MIME-type associated with the file. Defaults to None.
            filename (Union[Path, str]): The file to attach.
            verify_files (bool): Verify that the attachment file exists. Defaults to False.
        """
        self.filename = Path(filename)
        self.name = name if name else self.filename.name
        if not self.filename.exists() and verify_files:
            logging.fatal(f"Could not find attachment file: {self.filename}!")
            sys.exit(70)
        self.mimetype = mimetype

    def generate_options(self) -> list:
        """
        Generate all options associated with the attachment.

        Returns:
            list: List of attachment CLI options passed to mkvmerge.
        """
        options = [
            "--attachment-name",
            self.name,
            "--attach-file",
            str(self.filename.absolute()),
        ]

        if self.mimetype:
            options.extend(
                ["--attachment-mime-type", self.mimetype]
            )

        return options


class MkvMerge:
    """A class that contains all the sources, attachments, and options required to create an
    actual useful set of configuration options.  It will also mux everything together.

    Attributes:
        attachments (List[MkvAttachments]): The list of associated attachments to mux in.
        mkvmerge_path (Path): The path to the `mkvmerge` binary.
        global_options (dict): Global options to set for `mkvmerge`.
        output (Path): The output file to mux to.
        schema_file (Path): The path to the Matroska `mkvmerge` schema file for JSON validation.
        sources (List[MkvSource]): The source files and options to use for tracks.
        track_order_override (list): A list of maps that set the final order of tracks in the output file.
    """

    attachments: List[MkvAttachment]
    mkvmerge_path: Path
    global_options: dict
    output: Path
    schema_file: Path
    sources: List[MkvSource]
    track_order_override: list

    def __init__(self) -> None:
        """
        Create a Matroska muxing object
        """
        self.sources = list()
        self.attachments = list()
        self.track_order_override = list()
        self.output = None
        self.mkvmerge_path = MKVMERGE_PATH
        self.global_options = dict()
        schema_path = Path(
            os.path.dirname(os.path.abspath(__file__)))
        self.schema_file = schema_path / Path("schema/mkvmerge.schema.json")

    def load_from_file(self, json_file: Union[Path, str]):
        """Load all of the relevant Matroska information from a JSON file.

        Args:
            json_file (Union[Path, str]): The JSON file to load.
        """
        json_file = Path(json_file)
        if not json_file.exists():
            logging.fatal(f"Cannot open JSON file: '{json_file}'!")
            sys.exit(10)
        with json_file.open('r') as f:
            data = json.load(f)

        self.load_from_object(data)

    def reload_source_information(self) -> None:
        """Regenerate source information for all attached sources.
        """
        for source in self.sources:
            source.get_info()

    def load_from_object(self, json_data: Union[Box, dict]):
        """Load all of the relevant Matroska information from a dict.

        Args:
            json_data (Union[Box, dict]): The data to load.
        """
        with self.schema_file.open('r') as f:
            schema = json.load(f)

        jsonschema.validate(json_data, schema)

        json_data = Box(json_data)
        self.sources = [MkvSource(**source) for source in json_data.sources]
        for track in json_data.tracks:
            source_track = MkvSourceTrack(track.track, track.options)
            self.sources[track.source].add_track(source_track)
        self.output = Path(json_data.output_file)
        self.global_options = getattr(json_data, "options", dict())
        self.attachments = [MkvAttachment(
            **i) for i in getattr(json_data, "attachments", list())]
        for attach_dir in json_data.get("attachment_directories", list()):
            self.attachments.extend(self.add_attachment_directory(attach_dir))
        self.track_order_override = [
            f'{i.source}:{i.track}' for i in json_data.tracks]

    def add_attachment_directory(self, dir: Union[Path, str]) -> Iterable[MkvAttachment]:
        """Load all files from a directory as attachments.

        Args:
            dir (Union[Path, str]): The directory to load attachments from.

        Yields:
            Iterator[Iterable[MkvAttachment]]: An iterator of MkvAttachments.
        """
        files = (f for f in Path(dir).glob('*') if f.is_file())
        for f in files:
            yield MkvAttachment(filename=f)

    def add_source(self, source: MkvSource) -> None:
        """Add an MkvSource to mux into the Matroska file

        Args: 
            source (MkvSource): An MkvSource object
        """
        self.sources.append(source)

    def add_attachment(self, attachment: MkvAttachment) -> None:
        """Add an MkvAttachment to mux into the Matroska file

        Args:
            attachment : An MkvAttachment object
        """
        self.attachments.append(attachment)

    @property
    def track_order(self) -> list:
        """The track order that will be used when muxing.  Automatically generated unless the
        track_order_override parameter is used.

        Returns:
            list: The track order CLI options.
        """
        if self.track_order_override:
            return self.track_order_override
        temp = list()
        for i in range(0, len(self.sources)):
            for j in self.sources[i].tracks:
                temp.append(f"{i}:{j.track}")
        return temp

    def generate_command(self, as_string: bool = False) -> Union[list, str]:
        """Generate a list of options to feed the 'mkvmerge' binary.

        Args:
            as_string (bool): Return the CLI options as a string. Defaults to False.

        Returns:
            Union[list, str]: A list/string of 'mkvmerge' CLI options.
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
        delete_temp: bool = False,
        filename: Union[str, Path] = None,
        verbose: bool = False,
    ) -> int:
        """Mux all of the included sources, attachemts, and options.

        Args:
            delete_temp (bool, optional): Delete the temp file created for options (if created). Defaults to False.
            filename (Union[str, Path], optional): The temporary file to put the `mkvmerge` options in. Defaults to None.
            verbose (bool, optional): Output `mkvmerge` muxing messages to STDOUT. Defaults to False.

        Returns:
            int: The status code of the `mkvmerge` mux.
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


if __name__ == "__main__":
    a = MkvMerge()
    a.load_from_file("test copy.json")
    print(a.generate_command(True))
