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
    track_id: int
    track_type: str
    track_lang: str


class MkvInfo:
    def __init__(self, source: Union[Path, str]) -> list:
        self.source = Path(source)
        self.mkvmerge_path = MKVMERGE_PATH
        self.info = self.get_info()
        self.tracks = self.process_info()

    def get_info(self) -> Box:
        """Get the 'identify' information for the track.
        """
        command = [MKVMERGE_PATH, '-i', str(self.source), '-F', 'json']
        output = subprocess.run(command, capture_output=True)
        return Box(json.loads(output.stdout))

    def process_info(self) -> List[MkvInfoTrack]:
        tracks = list()
        for i in self.info.tracks:
            lang = getattr(i.properties, "language", None)
            track = MkvInfoTrack(
                track_id=i.id,
                track_type=i.type,
                track_lang=lang
            )
            tracks.append(track)
        return tracks

    def get_tracks(self, track_type: Optional[str] = None, language: Optional[str] = None) -> List[MkvInfoTrack]:
        if not track_type and not language:
            return self.tracks

        tracks = self.tracks
        if track_type:
            tracks = [i for i in self.tracks if i.track_type == track_type]
        if language:
            tracks = [i for i in tracks if i.track_lang == language]
        return tracks
