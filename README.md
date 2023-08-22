```json
{
  "sources": [
    "/mnt/server/cool_video_file_with_eng_audio.mkv",
    "/mnt/server/cool_audio_file_jpn.ac3",
    "/mnt/server/subtitles_full_eng.ass"
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
      "track": 0,
      "options": {
        "language": "jpn",
        "default-track": "yes"
      }
    },
    {
      "source": 0,
      "track": 1,
      "options": {
        "language": "eng",
        "default-track": "no"
      }
    },
    {
      "source": 2,
      "track": 0,
      "options": {
        "language": "eng",
        "default-track": "yes",
        "track-title": "Full Subtitles"
      }
    }
  ],
  "output_file": "/mnt/server/awesome_newly_muxed_video.mkv",
  "options": {
    "no-global-tags": null,
    "no-track-tags": null,
    "title": "Awesome Newly Muxed Video"
  }
}
```