from pathlib import Path

from matroska import Matroska, MkvAttachment, MkvSource, MkvSourceTrack

m = Matroska()

# Set the output file for all of the muxing
m.output = Path('output.mkv')

# Add the sources. Tracks are zero-indexed based on their order in the CLI
# as well as here.
m.add_source(MkvSource(source_file='test1.mkv'))
m.add_source(MkvSource(source_file='test2.mkv'))

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

# Set the final track order for the Matroska file.  The order of this is

m.track_order_override = ["0:0", "1:1", "0:2", "1:3"]

