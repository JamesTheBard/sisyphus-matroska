# Sisyphus Matroska

This Python module wraps `mkvinfo`, `mkvmerge` and `mkvextract` commands and adds some enhancements to `mkvinfo` and `mkvextract` that allows for the search of tracks via language and track type.

## Pythonic Version

```python
from pathlib import Path

from matroska import Matroska, MkvAttachment, MkvSource, MkvSourceTrack

m = Matroska()

# Set the output file for all of the muxing
m.output = Path('output.mkv')

# Add the sources. Tracks are zero-indexed based on their order in the CLI
# as well as here.
m.add_source(
    MkvSource(
        filename='test1.mkv',
        options={
            "_copy-video-tracks": None,
            "no-chapters": None
        }
    )
)
m.add_source(MkvSource(filename='test2.mkv'))

# Add tracks 0 and 2 to the first source (source 0)
m.sources[0].add_track(
    MkvSourceTrack(
        track=0,
        options={
            "language": "und",
            "default-track": "yes",
            "title": "Awesome Newly Muxed Video"
        }
    )
)
m.sources[0].add_track(
    MkvSourceTrack(
        track=2,
        options={
            "language": "eng",
            "default-track": "no"
        }
    )
)

# Add tracks 1 and 3 to the second source (source 1)
m.sources[1].add_track(
    MkvSourceTrack(
        track=1,
        options={
            "language": "jpn",
            "default-track": "yes"
        }
    )
)
m.sources[1].add_track(
    MkvSourceTrack(
        track=3,
        options={
            "language": "eng",
            "default-track": "yes",
            "track-name": "Cool Audio Track"
        }
    )
)

# Set the global options to pass to `mkvmerge`.
m.global_options = {
    "no-global-tags": None,
    "no-track-tags": None,
    "title": "Awesome Newly Muxed Video"
}

# Attach two fonts to the output Matroska file.
m.add_attachment(
    MkvAttachment(
        filename="test.otf"
    )
)
m.add_attachment(
    MkvAttachment(
        filename="test.ttf"
    )
)

# Set the final track order for the Matroska file.  The order of this
# puts the video track first (0:0), then the Japanese audio track (1:1),
# then the English audio track (0:2), then the English subtitles (1:3).
#
# When loading from JSON, this is automatically generated from the order
# of the tracks in the JSON file.
m.track_order_override = ["0:0", "1:1", "0:2", "1:3"]

# Mux the track.
m.mux()
```

## Passing a JSON file into the module

```python
from matroska import Matroska

m = Matroska()

# Load the configuration from the JSON file.  The track order in the JSON
# file is based on the order that the tracks appear in the file.
m.load_from_file('test.json')

# Mux the track.
m.mux()
```

The contents of the `test.json` file are below.

```json
{
  "sources": [
    {
      "filename": "test1.mkv",
      "options": {
        "_copy-video-tracks": null,
        "no-chapters": null
      }
    },
    {
      "filename": "test2.mkv"
    }
  ],
  "tracks": [
    {
      "source": 0,
      "track": 0,
      "options": {
        "language": "und",
        "default-track": "yes",
        "title": "Awesome Newly Muxed Video"
      }
    },
    {
      "source": 1,
      "track": 1,
      "options": {
        "language": "jpn",
        "default-track": "yes"
      }
    },
    {
      "source": 0,
      "track": 2,
      "options": {
        "language": "eng",
        "default-track": "no"
      }
    },
    {
      "source": 1,
      "track": 3,
      "options": {
        "language": "eng",
        "default-track": "yes",
        "track-name": "THISISATEST"
      }
    }
  ],
  "output_file": "awesome_newly_muxed_video.mkv",
  "options": {
    "no-global-tags": null,
    "no-track-tags": null,
    "title": "Awesome Newly Muxed Video"
  },
  "attachments": [
    {
      "filename": "test.otf"
    },
    {
      "filename": "test.ttf"
    }
  ]
}
```