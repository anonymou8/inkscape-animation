### Inkscape extension to convert SVG document to MP4-animation.

Works with Inkscale v.1.2*

\* — *(There's an [issue](https://gitlab.com/inkscape/inkscape/-/issues/2473) on some OSes
with missing `cssselect` Python module, on which Inkskape extensions subsystem depends. 
Manual installation fixes the problem. It may be named `python3-cssselect` 
or just `python-cssselect` in your distro repository.)*

<img src="https://raw.githubusercontent.com/anonymou8/inkscape-animation/main/screenshot.png" />

Each layer in a document represents a single frame. Bottom layer is the first frame.

If bottom layer is named `bg` then it will be set as background for every frame.

The extension is of Export type. To use it go to `File→Save As...` or `File→Save a Copy...`
and select `Layers as animation frames (ffmpeg) (*.mp4)` for the format.

The extension uses Ffmpeg to combine automatically created PNG images of layers to MP4 file.
User is able to select rendering resolution, framerate and encoding quality. `Loops` parameter tells Ffmpeg how many times to repeat frames sequence. The codec used is h264.

There is an option that allows to save each frame in PNG format to a specified directory. Files will
be named in four-digit format, like `0000.png`, `0001.png` e.t.c. User can change first image number.
Count of PNG images saved is always the same as number of layers in a document.

### Installation

You must have [Ffmpeg](https://ffmpeg.org/) executable instlled. Make sure a path to it is mentioned in the system global `PATH` variable. As newer version of Inkscape is bundled with Python 3 you don't have to worry about the interpreter.

Copy `layers2anim.inx` and `layers2anim.py` to Inkscape extesions directory and restart Inkscape. You can find out the name of the directory in `Edit→Preferences→System: User extensions`. For Linux it might be `~/.config/inkscape/extensions`.

### Example animation 

<img src="https://raw.githubusercontent.com/anonymou8/inkscape-animation/main/swan.gif" />

This GIF is the result of convertion PNG frames exported by the extension, using Ffmpeg commands like

```
ffmpeg -i %04d.png -vf palettegen=max_colors=256 palette.png
ffmpeg -r 18 -i %04d.png -i palette.png -lavfi paletteuse=bayer:4 swan.gif
```
