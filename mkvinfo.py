import json
import platform
import shutil
import subprocess
from pathlib import Path
from typing import Union, List, Optional
from dataclasses import dataclass

from box import Box

if platform.system() == "Windows":
    MKVMERGE_PATH = shutil.which('mkvmerge.exe')
else:
    MKVMERGE_PATH = shutil.which('mkvmerge')


@dataclass
class MkvInfoTrack:
    """Matroska track information.

    Attributes:
        track_id (int): The track ID
        track_type (str): The track type (e.g. `video` or `subtitles`)
        track_lang (str, optional): The track language. Set to None if no language associated.
    """
    track_id: int
    track_type: str
    track_lang: Union[str, None]
    track_codec: str


class MkvInfo:
    """Get track information from the `mkvmerge` command.

    Attributes:
        source (Path): The source file to get the information for.
        mkvmerge_path (Path): The path to the `mkvmerge` binary.
        info (Box): The JSON data from `mkvmerge`.
        tracks (List[MkvInfoTrack]): All of the track information from the source file.
    """
    source: Path
    mkvmerge_path: Path
    info: Box
    tracks: List[MkvInfoTrack]

    def __init__(self, source: Union[Path, str]):
        """Create the MkvInfo object given a source file.

        Args:
            source (Union[Path, str]): The filesystem path to the source file.
        """
        self.source = Path(source)
        self.mkvmerge_path = MKVMERGE_PATH
        self.info = self.get_info()
        self.tracks = self.process_info()

    def get_info(self) -> Box:
        """Get the 'identify' information for the track.

        Returns:
            Box: The information loaded from the `mkvmerge` JSON.
        """
        command = [MKVMERGE_PATH, '-i', str(self.source), '-F', 'json']
        output = subprocess.run(command, capture_output=True)
        return Box(json.loads(output.stdout))

    def process_info(self) -> List[MkvInfoTrack]:
        """Process the information from the `mkvmerge` command and return a list of MkvInfoTracks.

        Returns:
            List[MkvInfoTrack]: All of the tracks associated with the source.
        """
        tracks = list()
        for i in self.info.tracks:
            lang = getattr(i.properties, "language", None)
            track = MkvInfoTrack(
                track_id=i.id,
                track_type=i.type,
                track_lang=lang,
                track_codec=i.properties.codec_id
            )
            tracks.append(track)
        return tracks

    def get_tracks(self, track_type: Optional[str] = None, language: Optional[str] = None) -> List[MkvInfoTrack]:
        """Get tracks from the track list.

        Args:
            track_type (Optional[str], optional): Filter by track type. Defaults to None.
            language (Optional[str], optional): Filter by track language. Defaults to None.

        Returns:
            List[MkvInfoTrack]: The filtered tracks.
        """
        if not track_type and not language:
            return self.tracks

        tracks = self.tracks
        if track_type:
            tracks = [i for i in self.tracks if i.track_type == track_type]
        if language:
            tracks = [i for i in tracks if i.track_lang == language]
        return tracks
